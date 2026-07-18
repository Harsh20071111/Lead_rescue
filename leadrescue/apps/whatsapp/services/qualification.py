import logging
import re
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Max

from apps.accounts.models import AgentProfile
from apps.core.choices import BHKChoices
from apps.leads.models import Activity, Lead
from apps.whatsapp.models import WhatsAppConversation, WhatsAppMessage
from apps.whatsapp.services.client import send_text

logger = logging.getLogger(__name__)


def handle_inbound_text(agency, customer_phone, message_id, content):
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

    reply = _advance_conversation(conversation, content)
    if reply:
        send_text(agency, customer_phone, reply)
        WhatsAppMessage.objects.create(
            conversation=conversation,
            direction=WhatsAppMessage.Direction.OUTBOUND,
            message_id=f"local-{message_id}",
            content=reply,
        )
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
        state=WhatsAppConversation.State.STARTED,
    )


def _advance_conversation(conversation, content):
    data = dict(conversation.collected_data or {})
    state = conversation.state

    if state == WhatsAppConversation.State.STARTED:
        display_name = conversation.agency.whatsapp_display_name or conversation.agency.name
        conversation.state = WhatsAppConversation.State.ASKED_NAME
        conversation.collected_data = data
        conversation.save(update_fields=["state", "collected_data", "updated_at"])
        return f"Welcome to {display_name}. What is your name?"

    if state == WhatsAppConversation.State.ASKED_NAME:
        data["name"] = content
        conversation.state = WhatsAppConversation.State.ASKED_BUDGET
        conversation.collected_data = data
        conversation.save(update_fields=["state", "collected_data", "updated_at"])
        return "Thanks. What is your approximate budget?"

    if state == WhatsAppConversation.State.ASKED_BUDGET:
        data["budget_raw"] = content
        budget_min, budget_max = parse_budget(content)
        if budget_min is not None:
            data["budget_min"] = str(budget_min)
            data["budget_max"] = str(budget_max or budget_min)
        conversation.state = WhatsAppConversation.State.ASKED_BHK
        conversation.collected_data = data
        conversation.save(update_fields=["state", "collected_data", "updated_at"])
        return "Got it. What BHK configuration are you looking for?"

    if state == WhatsAppConversation.State.ASKED_BHK:
        data["bhk_raw"] = content
        data["preferred_bhk"] = parse_bhk(content)
        conversation.state = WhatsAppConversation.State.ASKED_LOCATION
        conversation.collected_data = data
        conversation.save(update_fields=["state", "collected_data", "updated_at"])
        return "Which location do you prefer?"

    if state == WhatsAppConversation.State.ASKED_LOCATION:
        data["preferred_location"] = content
        conversation.collected_data = data
        conversation.save(update_fields=["collected_data", "updated_at"])
        lead = create_lead_from_conversation(conversation)
        if lead is None:
            return "Thanks. We have your details and our team will follow up shortly."
        return "Thanks. Your requirement has been shared with our team. We will contact you soon."

    return None


def parse_budget(value):
    text = value.lower().replace(",", "")
    numbers = re.findall(r"\d+(?:\.\d+)?", text)
    if not numbers:
        return None, None
    try:
        parsed = [Decimal(number) for number in numbers[:2]]
    except InvalidOperation:
        return None, None
    multiplier = Decimal("1")
    if "crore" in text or "cr" in text:
        multiplier = Decimal("10000000")
    elif "lakh" in text or "lac" in text or re.search(r"\bl\b", text):
        multiplier = Decimal("100000")
    values = [number * multiplier for number in parsed]
    if len(values) == 1:
        return values[0], values[0]
    return min(values), max(values)


def parse_bhk(value):
    text = value.lower()
    if "studio" in text:
        return BHKChoices.STUDIO
    match = re.search(r"([1-4])\s*(?:bhk|bed|b)", text)
    if not match:
        match = re.search(r"\b([1-4])\b", text)
    if not match:
        return None
    mapping = {
        "1": BHKChoices.ONE_BHK,
        "2": BHKChoices.TWO_BHK,
        "3": BHKChoices.THREE_BHK,
        "4": BHKChoices.FOUR_BHK,
    }
    return mapping.get(match.group(1))


def choose_round_robin_agent(agency):
    agents = list(
        AgentProfile.objects.filter(agency=agency, is_active=True)
        .select_related("user")
        .annotate(last_assigned_at=Max("leads__created_at"))
        .order_by("last_assigned_at", "id")
    )
    if not agents:
        return None
    return agents[0]


def create_lead_from_conversation(conversation):
    data = conversation.collected_data or {}
    try:
        with transaction.atomic():
            assigned_agent = choose_round_robin_agent(conversation.agency)
            lead = Lead.objects.create(
                agency=conversation.agency,
                name=data.get("name") or "WhatsApp Lead",
                phone=conversation.customer_phone,
                source=Lead.LeadSource.WHATSAPP,
                budget=data.get("budget_raw", ""),
                budget_min=data.get("budget_min") or None,
                budget_max=data.get("budget_max") or None,
                preferred_bhk=data.get("preferred_bhk") or None,
                bhk_preference=data.get("bhk_raw", ""),
                preferred_location=data.get("preferred_location", ""),
                area_preference=data.get("preferred_location", ""),
                assigned_agent=assigned_agent,
            )
            if assigned_agent:
                Activity.objects.create(
                    agency=conversation.agency,
                    lead=lead,
                    agent=assigned_agent,
                    activity_type=Activity.ActivityType.WHATSAPP,
                    content=summarize_conversation(data),
                )
            conversation.lead = lead
            conversation.state = WhatsAppConversation.State.COMPLETED
            conversation.is_active = False
            conversation.save(update_fields=["lead", "state", "is_active", "updated_at"])
            return lead
    except Exception:
        logger.exception("Failed to create Lead from WhatsApp conversation %s", conversation.pk)
        return None


def summarize_conversation(data):
    return (
        "WhatsApp qualification completed. "
        f"Name: {data.get('name', '-')}; "
        f"Budget: {data.get('budget_raw', '-')}; "
        f"BHK: {data.get('bhk_raw', '-')}; "
        f"Location: {data.get('preferred_location', '-')}."
    )
