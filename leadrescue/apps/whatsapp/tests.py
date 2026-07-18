import hashlib
import hmac
import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import AgentProfile, User
from apps.agencies.models import Agency
from apps.leads.models import Lead
from apps.whatsapp.models import WhatsAppConversation, WhatsAppMessage
from apps.whatsapp.services.client import WhatsAppClientError


def signed_payload(payload, secret="test-secret"):
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return body, signature


def webhook_payload(phone_number_id, from_phone, message_id, text):
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": phone_number_id},
                            "messages": [
                                {
                                    "id": message_id,
                                    "from": from_phone,
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ],
                        }
                    }
                ]
            }
        ]
    }


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    WHATSAPP_APP_SECRET="test-secret",
    WHATSAPP_WEBHOOK_VERIFY_TOKEN="verify-me",
)
class WhatsAppPhase4Tests(TestCase):
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
        )
        self.agent_a1 = self.create_agent(self.agency_a, "a1@example.com")
        self.agent_a2 = self.create_agent(self.agency_a, "a2@example.com")
        self.agent_b1 = self.create_agent(self.agency_b, "b1@example.com")

    def create_agent(self, agency, email, role=AgentProfile.Role.AGENT):
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

    @patch("apps.whatsapp.services.qualification.send_text")
    def test_full_conversation_creates_whatsapp_lead(self, send_text):
        steps = [
            ("m1", "Hi"),
            ("m2", "Ravi Kumar"),
            ("m3", "80 lakh"),
            ("m4", "2 BHK"),
            ("m5", "Andheri West"),
        ]
        for message_id, text in steps:
            response = self.post_webhook(webhook_payload("phone-a", "919900001111", message_id, text))
            self.assertEqual(response.status_code, 200)

        lead = Lead.objects.get(agency=self.agency_a, phone="919900001111")
        self.assertEqual(lead.name, "Ravi Kumar")
        self.assertEqual(lead.source, Lead.LeadSource.WHATSAPP)
        self.assertEqual(str(lead.budget_min), "8000000.00")
        self.assertEqual(str(lead.budget_max), "8000000.00")
        self.assertEqual(lead.preferred_bhk, "2_bhk")
        self.assertEqual(lead.preferred_location, "Andheri West")
        self.assertFalse(lead.whatsapp_conversations.get().is_active)
        self.assertEqual(send_text.call_count, 5)

    @patch("apps.whatsapp.services.qualification.send_text")
    def test_two_agencies_route_by_phone_number_id(self, send_text):
        for agency_phone_id, customer_phone, prefix in [
            ("phone-a", "919900001111", "A"),
            ("phone-b", "919900002222", "B"),
        ]:
            for idx, text in enumerate(["Hi", f"{prefix} Buyer", "1 crore", "3 BHK", "Bandra"], start=1):
                self.post_webhook(
                    webhook_payload(agency_phone_id, customer_phone, f"{prefix}{idx}", text)
                )

        lead_a = Lead.objects.get(agency=self.agency_a)
        lead_b = Lead.objects.get(agency=self.agency_b)
        self.assertEqual(lead_a.phone, "919900001111")
        self.assertEqual(lead_a.name, "A Buyer")
        self.assertEqual(lead_b.phone, "919900002222")
        self.assertEqual(lead_b.name, "B Buyer")
        self.assertEqual(WhatsAppConversation.objects.filter(agency=self.agency_a).count(), 1)
        self.assertEqual(WhatsAppConversation.objects.filter(agency=self.agency_b).count(), 1)

    @patch("apps.whatsapp.services.qualification.send_text")
    def test_duplicate_message_id_is_not_reprocessed(self, send_text):
        payload = webhook_payload("phone-a", "919900001111", "dup-1", "Hi")
        self.post_webhook(payload)
        self.post_webhook(payload)
        self.assertEqual(WhatsAppMessage.objects.filter(message_id="dup-1").count(), 1)
        self.assertEqual(send_text.call_count, 1)

    def test_unverified_signature_is_rejected(self):
        body = json.dumps(webhook_payload("phone-a", "919900001111", "m1", "Hi")).encode()
        response = self.client.post(
            reverse("whatsapp:webhook"),
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256="sha256=bad",
        )
        self.assertEqual(response.status_code, 403)

    @patch("apps.whatsapp.tasks.process_whatsapp_webhook.delay")
    def test_disconnected_agency_is_not_matched(self, delay):
        self.agency_a.whatsapp_status = Agency.WhatsAppStatus.ERROR
        self.agency_a.save(update_fields=["whatsapp_status"])
        response = self.post_webhook(webhook_payload("phone-a", "919900001111", "m1", "Hi"))
        self.assertEqual(response.status_code, 200)
        delay.assert_not_called()

    @patch("apps.whatsapp.services.qualification.send_text")
    def test_round_robin_uses_least_recently_assigned_agent(self, send_text):
        for idx, phone in enumerate(["919900001111", "919900002222"], start=1):
            for step, text in enumerate(["Hi", f"Buyer {idx}", "75 lakh", "2 BHK", "Powai"], start=1):
                self.post_webhook(webhook_payload("phone-a", phone, f"rr-{idx}-{step}", text))

        assigned = list(
            Lead.objects.filter(agency=self.agency_a).order_by("created_at").values_list(
                "assigned_agent_id", flat=True
            )
        )
        self.assertEqual(assigned, [self.agent_a1.id, self.agent_a2.id])

    @patch("apps.whatsapp.forms.validate_phone_number_token")
    def test_settings_bad_token_does_not_connect(self, validate_token):
        validate_token.side_effect = WhatsAppClientError("bad token")
        owner = self.create_agent(self.agency_a, "owner@example.com", AgentProfile.Role.OWNER)
        self.client.force_login(owner.user)
        response = self.client.post(
            reverse("whatsapp:settings"),
            {
                "phone_number_id": "bad-phone",
                "business_account_id": "bad-waba",
                "access_token": "bad-token",
                "display_name": "Bad Realty",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.agency_a.refresh_from_db()
        self.assertNotEqual(self.agency_a.whatsapp_phone_number_id, "bad-phone")
        self.assertEqual(self.agency_a.whatsapp_status, Agency.WhatsAppStatus.CONNECTED)
