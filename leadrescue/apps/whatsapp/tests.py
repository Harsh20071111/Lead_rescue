import hashlib
import hmac
import json
from unittest.mock import patch, PropertyMock

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import AgentProfile, User
from apps.agencies.models import Agency
from apps.core.choices import BHKChoices
from apps.leads.models import Activity, Lead
from apps.properties.models import Property
from apps.whatsapp.models import WhatsAppConversation, WhatsAppMessage
from apps.whatsapp.services.client import WhatsAppClientError
from apps.whatsapp.services.qualification import handle_inbound_message

DEFAULT_BRACKETS = ["Under 50L", "50L–1Cr", "1Cr–2Cr", "2Cr+"]


def signed_payload(payload, secret="test-secret"):
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return body, signature


def webhook_payload(phone_number_id, from_phone, message_id, text_body, msg_type="text"):
    msg = {
        "id": message_id,
        "from": from_phone,
        "type": msg_type,
    }
    if msg_type == "text":
        msg["text"] = {"body": text_body}
    elif msg_type == "interactive":
        msg["interactive"] = {
            "type": "list_reply",
            "list_reply": {"id": text_body, "title": text_body},
        }
    return {
        "entry": [{
            "changes": [{
                "value": {
                    "metadata": {"phone_number_id": phone_number_id},
                    "messages": [msg],
                }
            }]
        }]
    }


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    WHATSAPP_APP_SECRET="test-secret",
    WHATSAPP_WEBHOOK_VERIFY_TOKEN="verify-me",
)
class WhatsAppPhase45Tests(TestCase):
    def setUp(self):
        self.agency_a = Agency.objects.create(
            name="ABC Realty",
            owner_phone="111",
            owner_email="owner-a@example.com",
            city="Mumbai",
            whatsapp_phone_number_id="phone-a",
            whatsapp_business_account_id="waba-a",
            whatsapp_access_token="token-a",
            whatsapp_display_name="ABC Realty",
            whatsapp_status=Agency.WhatsAppStatus.CONNECTED,
            budget_brackets=DEFAULT_BRACKETS,
        )
        self.agency_b = Agency.objects.create(
            name="XYZ Homes",
            owner_phone="222",
            owner_email="owner-b@example.com",
            city="Pune",
            whatsapp_phone_number_id="phone-b",
            whatsapp_business_account_id="waba-b",
            whatsapp_access_token="token-b",
            whatsapp_display_name="XYZ Homes",
            whatsapp_status=Agency.WhatsAppStatus.CONNECTED,
            budget_brackets=DEFAULT_BRACKETS,
        )
        self.agent_a1 = self._create_agent(self.agency_a, "a1@example.com")
        self.agent_a2 = self._create_agent(self.agency_a, "a2@example.com")
        self.agent_b1 = self._create_agent(self.agency_b, "b1@example.com")

        # Create matching properties for agency A
        self.prop_a1 = Property.objects.create(
            agency=self.agency_a,
            title="2BHK in Andheri",
            city="Mumbai",
            locality="Andheri West",
            price=7500000,
            bhk=BHKChoices.TWO_BHK,
            listing_type="sale",
            status=Property.PropertyStatus.AVAILABLE,
            brochure_pdf="brochures/prop_a1",
        )
        self.prop_a2 = Property.objects.create(
            agency=self.agency_a,
            title="3BHK in Bandra",
            city="Mumbai",
            locality="Bandra",
            price=15000000,
            bhk=BHKChoices.THREE_BHK,
            listing_type="sale",
            status=Property.PropertyStatus.AVAILABLE,
            brochure_pdf="brochures/prop_a2",
        )
        # Property without brochure
        self.prop_a3 = Property.objects.create(
            agency=self.agency_a,
            title="1BHK in Powai",
            city="Mumbai",
            locality="Powai",
            price=5000000,
            bhk=BHKChoices.ONE_BHK,
            listing_type="sale",
            status=Property.PropertyStatus.AVAILABLE,
        )

    def _create_agent(self, agency, email, role=AgentProfile.Role.AGENT):
        user = User.objects.create_user(username=email, email=email, password="pass")
        return AgentProfile.objects.create(
            user=user, agency=agency, role=role, phone="999", is_active=True
        )

    def post_webhook(self, payload, secret="test-secret"):
        body, signature = signed_payload(payload, secret=secret)
        return self.client.post(
            reverse("whatsapp:webhook"),
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )

    # ---- (a) Full flow end-to-end ----

    @patch("apps.whatsapp.services.qualification.send_list_message")
    @patch("apps.whatsapp.services.qualification.send_button_message")
    @patch("apps.whatsapp.services.qualification.send_document_message")
    def test_full_interactive_flow_creates_lead_and_sends_brochures(
        self, send_doc, send_btn, send_list
    ):
        phone = "919900001111"
        # Step 1: START → send purpose list (message is ignored, bot initiates)
        handle_inbound_message(self.agency_a, phone, "m1", "Hi", is_interactive=False)
        conv = WhatsAppConversation.objects.get(customer_phone=phone)
        self.assertEqual(conv.state, WhatsAppConversation.State.AWAITING_PURPOSE)
        send_list.assert_called()

        # Step 2: Purpose → BHK list
        handle_inbound_message(self.agency_a, phone, "m2", "buy", is_interactive=True)
        conv.refresh_from_db()
        self.assertEqual(conv.purpose, "buy")
        self.assertEqual(conv.state, WhatsAppConversation.State.AWAITING_BHK)

        # Step 3: BHK → Budget
        handle_inbound_message(self.agency_a, phone, "m3", "2_bhk", is_interactive=True)
        conv.refresh_from_db()
        self.assertEqual(conv.bhk, "2_bhk")
        self.assertEqual(conv.state, WhatsAppConversation.State.AWAITING_BUDGET)

        # Step 4: Budget → Locality
        handle_inbound_message(self.agency_a, phone, "m4", "budget_1", is_interactive=True)
        conv.refresh_from_db()
        self.assertEqual(conv.budget_bracket, "budget_1")
        self.assertEqual(conv.state, WhatsAppConversation.State.AWAITING_LOCALITY)

        # Step 5: Locality → COMPLETED → brochures sent
        handle_inbound_message(self.agency_a, phone, "m5", "Andheri West", is_interactive=True)
        conv.refresh_from_db()
        self.assertEqual(conv.state, WhatsAppConversation.State.COMPLETED)
        self.assertFalse(conv.is_active)

        # Lead created
        lead = Lead.objects.get(agency=self.agency_a, phone=phone)
        self.assertEqual(lead.source, Lead.LeadSource.WHATSAPP)
        self.assertEqual(lead.preferred_bhk, BHKChoices.TWO_BHK)
        self.assertEqual(lead.preferred_location, "Andheri West")

        # Brochures sent (prop_a1 matches, prop_a2 does not due to budget/location, prop_a3 has no brochure)
        doc_calls = [call[0] for call in send_doc.call_args_list]
        # prop_a1 (2BHK 75L Andheri) is the best match; prop_a2 is too expensive
        self.assertGreaterEqual(len(doc_calls), 1)

        # Activity logged
        activities = Activity.objects.filter(lead=lead, activity_type=Activity.ActivityType.WHATSAPP)
        self.assertGreaterEqual(activities.count(), 1)

    # ---- (b) Multi-tenant isolation ----

    @patch("apps.whatsapp.services.qualification.send_document_message")
    @patch("apps.whatsapp.services.qualification.send_text_reply")
    @patch("apps.whatsapp.services.qualification.send_list_message")
    @patch("apps.whatsapp.services.qualification.send_button_message")
    @patch("apps.whatsapp.services.qualification.send_text")
    def test_two_agencies_no_crossover(self, send_text, send_btn, send_list, send_text_reply, send_doc):
        phones = {
            "phone-a": ("919900001111", "A"),
            "phone-b": ("919900002222", "B"),
        }

        def simulate(agency, agency_phone_id, customer_phone, prefix):
            handle_inbound_message(agency, customer_phone, f"{prefix}1", "start", is_interactive=False)
            handle_inbound_message(agency, customer_phone, f"{prefix}2", "buy", is_interactive=True)
            handle_inbound_message(agency, customer_phone, f"{prefix}3", "2_bhk", is_interactive=True)
            handle_inbound_message(agency, customer_phone, f"{prefix}4", "budget_0", is_interactive=True)
            handle_inbound_message(agency, customer_phone, f"{prefix}5", "Andheri", is_interactive=True)

        simulate(self.agency_a, "phone-a", "919900001111", "A")
        simulate(self.agency_b, "phone-b", "919900002222", "B")

        lead_a = Lead.objects.get(agency=self.agency_a)
        lead_b = Lead.objects.get(agency=self.agency_b)
        self.assertEqual(lead_a.phone, "919900001111")
        self.assertEqual(lead_b.phone, "919900002222")

        self.assertEqual(
            WhatsAppConversation.objects.filter(agency=self.agency_a).count(), 1
        )
        self.assertEqual(
            WhatsAppConversation.objects.filter(agency=self.agency_b).count(), 1
        )

    # ---- (c) Property without brochure is skipped ----

    @patch("apps.whatsapp.services.qualification.send_text_reply")
    @patch("apps.whatsapp.services.qualification.send_list_message")
    @patch("apps.whatsapp.services.qualification.send_button_message")
    @patch("apps.whatsapp.services.qualification.send_document_message")
    def test_property_without_brochure_skipped_gracefully(self, send_doc, send_btn, send_list, send_text_reply):
        # Only create a property without brochure
        Property.objects.all().delete()
        prop = Property.objects.create(
            agency=self.agency_a,
            title="No Brochure Prop",
            city="Mumbai",
            locality="Test Area",
            price=7500000,
            bhk=BHKChoices.TWO_BHK,
            listing_type="sale",
            status=Property.PropertyStatus.AVAILABLE,
        )
        self.assertFalse(prop.brochure_pdf)

        phone = "919900009999"
        handle_inbound_message(self.agency_a, phone, "c1", "", is_interactive=False)
        handle_inbound_message(self.agency_a, phone, "c2", "buy", is_interactive=True)
        handle_inbound_message(self.agency_a, phone, "c3", "2_bhk", is_interactive=True)
        handle_inbound_message(self.agency_a, phone, "c4", "budget_0", is_interactive=True)
        handle_inbound_message(self.agency_a, phone, "c5", "Test Area", is_interactive=True)

        # Lead created
        self.assertTrue(Lead.objects.filter(agency=self.agency_a, phone=phone).exists())
        # No brochure sent (no properties with brochures)
        send_doc.assert_not_called()

    # ---- (d) Zero matches above threshold sends fallback ----

    @patch("apps.whatsapp.services.qualification.send_list_message")
    @patch("apps.whatsapp.services.qualification.send_button_message")
    @patch("apps.whatsapp.services.qualification.send_text_reply")
    def test_zero_matches_sends_fallback(self, send_text, send_btn, send_list):
        # All properties have mismatched BHK (e.g., 4BHK vs lead's 1BHK)
        Property.objects.all().delete()
        Property.objects.create(
            agency=self.agency_a,
            title="4BHK Luxury",
            city="Mumbai",
            locality="Bandra",
            price=50000000,
            bhk=BHKChoices.FOUR_BHK,
            listing_type="sale",
            status=Property.PropertyStatus.AVAILABLE,
            brochure_pdf="brochures/test",
        )

        phone = "919900008888"
        handle_inbound_message(self.agency_a, phone, "d1", "", is_interactive=False)
        handle_inbound_message(self.agency_a, phone, "d2", "buy", is_interactive=True)
        handle_inbound_message(self.agency_a, phone, "d3", "1_bhk", is_interactive=True)
        handle_inbound_message(self.agency_a, phone, "d4", "budget_0", is_interactive=True)
        handle_inbound_message(self.agency_a, phone, "d5", "Bandra", is_interactive=True)

        # Fallback message sent
        fallback_calls = [
            c for c in send_text.call_args_list
            if "One of our agents" in str(c)
        ]
        self.assertGreaterEqual(len(fallback_calls), 1)

    # ---- (e) Free text mid-flow re-prompts ----

    @patch("apps.whatsapp.services.qualification.send_list_message")
    def test_free_text_mid_flow_re_prompts(self, send_list):
        phone = "919900007777"
        handle_inbound_message(self.agency_a, phone, "e1", "", is_interactive=False)
        # Now in AWAITING_PURPOSE; free text should re-prompt
        send_list.reset_mock()
        handle_inbound_message(self.agency_a, phone, "e2", "I want a flat", is_interactive=False)
        # Should have called send_list again (re-prompt), not advanced
        conv = WhatsAppConversation.objects.get(customer_phone=phone)
        self.assertEqual(conv.state, WhatsAppConversation.State.AWAITING_PURPOSE)
        self.assertGreaterEqual(send_list.call_count, 1)

    # ---- (f) Agency with >3 budget brackets uses List Message ----

    @patch("apps.whatsapp.services.qualification.send_button_message")
    @patch("apps.whatsapp.services.qualification.send_list_message")
    def test_many_budget_brackets_use_list_message(self, send_list, send_btn):
        self.agency_a.budget_brackets = [
            "Under 25L", "25L–50L", "50L–75L", "75L–1Cr", "1Cr+"
        ]
        self.agency_a.save(update_fields=["budget_brackets"])

        phone = "919900006666"
        handle_inbound_message(self.agency_a, phone, "f1", "", is_interactive=False)
        handle_inbound_message(self.agency_a, phone, "f2", "buy", is_interactive=True)
        handle_inbound_message(self.agency_a, phone, "f3", "3_bhk", is_interactive=True)
        # Now awaiting budget — should use list message (>3 brackets)
        send_list.assert_called()
        send_btn.assert_not_called()

    # ---- (g) Activity timeline entries ----

    @patch("apps.whatsapp.services.qualification.send_list_message")
    @patch("apps.whatsapp.services.qualification.send_button_message")
    @patch("apps.whatsapp.services.qualification.send_document_message")
    def test_activity_logged_for_brochure_send(self, send_doc, send_btn, send_list):
        phone = "919900005555"
        handle_inbound_message(self.agency_a, phone, "g1", "", is_interactive=False)
        handle_inbound_message(self.agency_a, phone, "g2", "buy", is_interactive=True)
        handle_inbound_message(self.agency_a, phone, "g3", "2_bhk", is_interactive=True)
        handle_inbound_message(self.agency_a, phone, "g4", "budget_1", is_interactive=True)
        handle_inbound_message(self.agency_a, phone, "g5", "Andheri West", is_interactive=True)

        lead = Lead.objects.get(agency=self.agency_a, phone=phone)
        brochure_activities = Activity.objects.filter(
            lead=lead,
            activity_type=Activity.ActivityType.WHATSAPP,
            content__icontains="Brochure",
        )
        self.assertGreaterEqual(brochure_activities.count(), 1)

    # ---- Duplicate message ID is not reprocessed ----

    @patch("apps.whatsapp.services.qualification.send_list_message")
    def test_duplicate_message_id_is_not_reprocessed(self, send_list):
        payload = webhook_payload("phone-a", "919900001111", "dup-1", "Hi")
        self.post_webhook(payload)
        self.post_webhook(payload)
        self.assertEqual(WhatsAppMessage.objects.filter(message_id="dup-1").count(), 1)

    # ---- Bad signature is rejected ----

    def test_unverified_signature_is_rejected(self):
        body = json.dumps(webhook_payload("phone-a", "919900001111", "m1", "Hi")).encode()
        response = self.client.post(
            reverse("whatsapp:webhook"),
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256="sha256=bad",
        )
        self.assertEqual(response.status_code, 403)

    # ---- Disconnected agency is not matched ----

    @patch("apps.whatsapp.tasks.process_whatsapp_webhook.delay")
    def test_disconnected_agency_is_not_matched(self, delay):
        self.agency_a.whatsapp_status = Agency.WhatsAppStatus.ERROR
        self.agency_a.save(update_fields=["whatsapp_status"])
        response = self.post_webhook(webhook_payload("phone-a", "919900001111", "m1", "Hi"))
        self.assertEqual(response.status_code, 200)
        delay.assert_not_called()
