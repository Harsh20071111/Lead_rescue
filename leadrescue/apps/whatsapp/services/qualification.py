import logging
import re
from decimal import Decimal

from django.db import transaction
from django.db.models import Max

from apps.accounts.models import AgentProfile
from apps.core.choices import BHKChoices
from apps.leads.models import Activity, Lead
from apps.matching.services import match_properties_for_lead
from apps.properties.models import Property
from apps.whatsapp.models import WhatsAppConversation, WhatsAppMessage
from apps.whatsapp.services.client import send_text
from apps.whatsapp.services.interactive import (
    send_button_message,
    send_document_message,
    send_list_message,
    send_text_reply,
)

logger = logging.getLogger(__name__)


def parse_budget(raw):
    """Parse a raw budget text (e.g. '50 lakhs', '2cr', '1Cr–2Cr', '5000000')
    into (min, max) as Decimals.  Used by the imports pipeline."""
    if not raw or not raw.strip():
        return None, None
    raw = raw.strip()
    return _parse_bracket_text(raw)


def parse_bhk(raw):
    """Parse a raw BHK text (e.g. '2 BHK', '3BHK', '1 bhk')
    into a BHKChoices value.  Used by the imports pipeline."""
    if not raw or not raw.strip():
        return None
    raw = raw.strip().lower().replace("bhk", "").replace(" ", "")
    mapping = {
        "studio": BHKChoices.STUDIO,
        "1": BHKChoices.ONE_BHK,
        "2": BHKChoices.TWO_BHK,
        "3": BHKChoices.THREE_BHK,
        "4": BHKChoices.FOUR_BHK,
    }
    return mapping.get(raw)


# ---------------------------------------------------------------------------
# Inbound message router
# ---------------------------------------------------------------------------

def handle_inbound_message(agency, customer_phone, message_id, content, is_interactive=False):
    """Route an inbound message to the state machine."""
    conversation = _get_or_create_conversation(agency, customer_phone)

    if WhatsAppMessage.objects.filter(message_id=message_id).exists():
        logger.info("Skipping duplicate WhatsApp message %s", message_id)
        return conversation

    WhatsAppMessage.objects.create(
        conversation=conversation,
        direction=WhatsAppMessage.Direction.INBOUND,
        message_id=message_id,
        content=content,
    )

    if conversation.state in (
        WhatsAppConversation.State.COMPLETED,
        WhatsAppConversation.State.HANDED_OFF,
    ):
        return conversation

    if not is_interactive and conversation.state != WhatsAppConversation.State.START:
        # Free text mid-flow — re-prompt without advancing
        _re_prompt(conversation)
        return conversation

    _advance_conversation(conversation, content)
    return conversation


def _get_or_create_conversation(agency, customer_phone):
    conversation = (
        WhatsAppConversation.objects.filter(
            agency=agency, customer_phone=customer_phone, is_active=True
        )
        .order_by("-updated_at")
        .first()
    )
    if conversation:
        return conversation
    return WhatsAppConversation.objects.create(
        agency=agency,
        customer_phone=customer_phone,
        state=WhatsAppConversation.State.START,
    )


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

def _advance_conversation(conversation, content):
    state = conversation.state
    agency = conversation.agency
    phone = conversation.customer_phone

    if state == WhatsAppConversation.State.START:
        _send_purpose_list(agency, phone, conversation)
        conversation.state = WhatsAppConversation.State.AWAITING_PURPOSE
        conversation.save(update_fields=["state", "updated_at"])
        return

    if state == WhatsAppConversation.State.AWAITING_PURPOSE:
        conversation.purpose = content
        _send_bhk_list(agency, phone, conversation)
        conversation.state = WhatsAppConversation.State.AWAITING_BHK
        conversation.save(update_fields=["purpose", "state", "updated_at"])
        return

    if state == WhatsAppConversation.State.AWAITING_BHK:
        conversation.bhk = content
        _send_budget(agency, phone, conversation)
        conversation.state = WhatsAppConversation.State.AWAITING_BUDGET
        conversation.save(update_fields=["bhk", "state", "updated_at"])
        return

    if state == WhatsAppConversation.State.AWAITING_BUDGET:
        conversation.budget_bracket = content
        _send_locality_list(agency, phone, conversation)
        conversation.state = WhatsAppConversation.State.AWAITING_LOCALITY
        conversation.save(update_fields=["budget_bracket", "state", "updated_at"])
        return

    if state == WhatsAppConversation.State.AWAITING_LOCALITY:
        conversation.locality = content
        conversation.state = WhatsAppConversation.State.COMPLETED
        conversation.save(update_fields=["locality", "state", "updated_at"])
        _complete_conversation(conversation)
        return


def _re_prompt(conversation):
    """Re-send the current step's question without advancing."""
    agency = conversation.agency
    phone = conversation.customer_phone
    state = conversation.state

    if state == WhatsAppConversation.State.AWAITING_PURPOSE:
        _send_purpose_list(agency, phone, conversation)
    elif state == WhatsAppConversation.State.AWAITING_BHK:
        _send_bhk_list(agency, phone, conversation)
    elif state == WhatsAppConversation.State.AWAITING_BUDGET:
        _send_budget(agency, phone, conversation)
    elif state == WhatsAppConversation.State.AWAITING_LOCALITY:
        _send_locality_list(agency, phone, conversation)


# ---------------------------------------------------------------------------
# Interactive message builders
# ---------------------------------------------------------------------------

PURPOSE_OPTIONS = [
    {"id": "buy", "title": "Buy", "description": "Looking to buy a property"},
    {"id": "rent", "title": "Rent", "description": "Looking to rent a property"},
    {"id": "commercial", "title": "Commercial", "description": "Commercial property"},
]

BHK_OPTIONS = [
    {"id": "1_bhk", "title": "1 BHK"},
    {"id": "2_bhk", "title": "2 BHK"},
    {"id": "3_bhk", "title": "3 BHK"},
    {"id": "4_bhk", "title": "4 BHK"},
]

LOCALITY_CAP = 10


def _send_purpose_list(agency, phone, conversation):
    display_name = agency.whatsapp_display_name or agency.name
    send_list_message(
        agency, phone,
        header=display_name,
        body="What type of property are you looking for?",
        button_text="Select",
        sections=[{
            "title": "Purpose",
            "rows": PURPOSE_OPTIONS,
        }],
    )


def _send_bhk_list(agency, phone, conversation):
    send_list_message(
        agency, phone,
        header="BHK Preference",
        body="How many bedrooms do you need?",
        button_text="Select BHK",
        sections=[{
            "title": "Bedrooms",
            "rows": BHK_OPTIONS,
        }],
    )


def _send_budget(agency, phone, conversation):
    brackets = list(agency.budget_brackets) if agency.budget_brackets else [
        "Under 50L", "50L–1Cr", "1Cr–2Cr", "2Cr+"
    ]
    count = len(brackets)

    if count <= 3:
        buttons = [
            {"id": f"budget_{i}", "title": label}
            for i, label in enumerate(brackets)
        ]
        send_button_message(
            agency, phone,
            header="Budget",
            body="What is your budget range?",
            buttons=buttons,
        )
    else:
        rows = [
            {"id": f"budget_{i}", "title": label}
            for i, label in enumerate(brackets)
        ]
        # WhatsApp allows max 10 rows per section in list
        sections = []
        for i in range(0, len(rows), 10):
            chunk = rows[i:i + 10]
            sections.append({
                "title": f"Budget options" if i == 0 else "More",
                "rows": chunk,
            })
        send_list_message(
            agency, phone,
            header="Budget",
            body="What is your budget range?",
            button_text="Select budget",
            sections=sections,
        )


def _send_locality_list(agency, phone, conversation):
    localities = (
        Property.objects
        .filter(agency=agency, status=Property.PropertyStatus.AVAILABLE)
        .exclude(locality="")
        .values_list("locality", flat=True)
        .distinct()
        .order_by("locality")
    )[:LOCALITY_CAP]

    if not localities:
        # Fallback: ask via text if no properties exist
        send_text(agency, phone, "Which locality do you prefer?")
        return

    rows = [
        {"id": loc, "title": loc}
        for loc in localities
    ]
    send_list_message(
        agency, phone,
        header="Preferred Locality",
        body="Which locality do you prefer?",
        button_text="Select locality",
        sections=[{
            "title": "Localities",
            "rows": rows,
        }],
    )


# ---------------------------------------------------------------------------
# Matching + delivery
# ---------------------------------------------------------------------------

def _complete_conversation(conversation):
    agency = conversation.agency
    phone = conversation.customer_phone

    lead = _create_lead(conversation)
    if not lead:
        send_text_reply(
            agency, phone,
            "Thanks! One of our agents will reach out with options shortly.",
        )
        return

    matches = match_properties_for_lead(lead, limit=5)
    matches_above_threshold = [m for m in matches if m.score >= 0.3]
    top_with_brochure = [
        m for m in matches_above_threshold
        if m.object.brochure_pdf
    ][:3]

    if not top_with_brochure:
        send_text_reply(
            agency, phone,
            "Thanks! One of our agents will reach out with options shortly.",
        )
        return

    for match in top_with_brochure:
        prop = match.object
        try:
            document_url = prop.brochure_pdf.url
            caption = f"₹{prop.price:,.0f} · {prop.get_bhk_display()} · {prop.locality or prop.city}"
            filename = f"{prop.title.replace(' ', '_')}.pdf"
            send_document_message(agency, phone, document_url, caption, filename)

            Activity.objects.create(
                agency=agency,
                lead=lead,
                agent=lead.assigned_agent,
                activity_type=Activity.ActivityType.WHATSAPP,
                content=(
                    f"Brochure sent via WhatsApp bot: {prop.title} "
                    f"(₹{prop.price:,.0f}, {prop.get_bhk_display()}, {prop.locality or prop.city})"
                ),
            )
        except Exception as e:
            logger.exception(
                "Failed to send brochure for property %d to %s: %s",
                prop.pk, phone, e,
            )


def _parse_budget_value(bracket_id, agency):
    """Extract min/max from a budget bracket like 'budget_0' referencing agency.budget_brackets[index]."""
    try:
        idx = int(bracket_id.replace("budget_", ""))
        brackets = list(agency.budget_brackets) if agency.budget_brackets else []
        if idx < len(brackets):
            return _parse_bracket_text(brackets[idx])
    except (ValueError, IndexError):
        pass
    return None, None


def _parse_bracket_text(text):
    """Parse a budget bracket label like '50L–1Cr' or 'Under 50L' or '2Cr+' into (min, max)."""
    text = text.strip().lower().replace(",", "")
    import re

    if text.startswith("under"):
        numbers = re.findall(r"[\d.]+", text)
        if numbers:
            val = Decimal(numbers[0]) * _multiplier(text)
            return Decimal("0"), val
    elif "+" in text:
        numbers = re.findall(r"[\d.]+", text)
        if numbers:
            val = Decimal(numbers[0]) * _multiplier(text)
            return val, None
    else:
        # Range like "50L–1Cr" or "50L - 1Cr"
        parts = re.split(r"[-–—]", text)
        if len(parts) >= 2:
            nums = [re.findall(r"[\d.]+", p) for p in parts]
            if nums[0] and nums[1]:
                low = Decimal(nums[0][0]) * _multiplier(parts[0])
                high = Decimal(nums[1][0]) * _multiplier(parts[1])
                return low, high
        # Single number
        numbers = re.findall(r"[\d.]+", text)
        if numbers:
            val = Decimal(numbers[0]) * _multiplier(text)
            return val, val
    return None, None


def _multiplier(text):
    if "crore" in text or "cr" in text:
        return Decimal("10000000")
    if "lakh" in text or "lac" in text or re.search(r"(^|[\d.])\s*l\b", text):
        return Decimal("100000")
    return Decimal("1")


def _bhk_to_lead_value(bhk_id):
    """Map a BHK list-reply id to Lead.preferred_bhk."""
    mapping = {
        "studio": BHKChoices.STUDIO,
        "1_bhk": BHKChoices.ONE_BHK,
        "2_bhk": BHKChoices.TWO_BHK,
        "3_bhk": BHKChoices.THREE_BHK,
        "4_bhk": BHKChoices.FOUR_BHK,
    }
    return mapping.get(bhk_id)


def _purpose_to_listing_type(purpose):
    if purpose == "rent":
        return "rent"
    return "sale"


def _create_lead(conversation):
    try:
        with transaction.atomic():
            assigned_agent = _choose_round_robin_agent(conversation.agency)
            budget_min, budget_max = _parse_budget_value(
                conversation.budget_bracket, conversation.agency
            )

            listing_type = _purpose_to_listing_type(conversation.purpose)
            lead = Lead.objects.create(
                agency=conversation.agency,
                name=f"WhatsApp Lead ({conversation.customer_phone})",
                phone=conversation.customer_phone,
                source=Lead.LeadSource.WHATSAPP,
                status=Lead.LeadStatus.NEW,
                budget_min=budget_min,
                budget_max=budget_max,
                preferred_bhk=_bhk_to_lead_value(conversation.bhk),
                preferred_location=conversation.locality,
                budget=conversation.budget_bracket,
                bhk_preference=conversation.bhk,
                area_preference=conversation.locality,
                assigned_agent=assigned_agent,
                notes=(
                    f"Purpose: {conversation.purpose}, "
                    f"BHK: {conversation.bhk}, "
                    f"Budget bracket: {conversation.budget_bracket}, "
                    f"Locality: {conversation.locality}"
                ),
            )

            if assigned_agent:
                Activity.objects.create(
                    agency=conversation.agency,
                    lead=lead,
                    agent=assigned_agent,
                    activity_type=Activity.ActivityType.WHATSAPP,
                    content=(
                        f"Interactive WhatsApp qualification completed. "
                        f"Purpose: {conversation.purpose}; "
                        f"BHK: {conversation.bhk}; "
                        f"Budget: {conversation.budget_bracket}; "
                        f"Locality: {conversation.locality}."
                    ),
                )

            conversation.lead = lead
            conversation.is_active = False
            conversation.save(update_fields=["lead", "is_active", "updated_at"])
            return lead
    except Exception:
        logger.exception(
            "Failed to create Lead from WhatsApp conversation %s", conversation.pk
        )
        return None


def _choose_round_robin_agent(agency):
    agents = list(
        AgentProfile.objects.filter(agency=agency, is_active=True)
        .select_related("user")
        .annotate(last_assigned_at=Max("leads__created_at"))
        .order_by("last_assigned_at", "id")
    )
    if not agents:
        return None
    return agents[0]


# Legacy text-based handler (kept for backward compat, delegates to interactive)
def handle_inbound_text(agency, customer_phone, message_id, content):
    logger.warning("handle_inbound_text called — use handle_inbound_message instead")
    return handle_inbound_message(agency, customer_phone, message_id, content, is_interactive=False)
