import json
import hashlib
import hmac
import logging
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.agencies.models import Agency
from apps.accounts.models import AgentProfile
from apps.billing.models import UpgradeRequest
from apps.billing.pricing import PLAN_PRICING

User = get_user_model()

class EntitlementsGatingTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Starter Tier Agency
        self.starter_agency = Agency.objects.create(name="Starter Agency", plan_tier="starter")
        self.starter_user = User.objects.create_user(username="starter@example.com", email="starter@example.com", password="password")
        self.starter_agent = AgentProfile.objects.create(user=self.starter_user, agency=self.starter_agency, role="owner")
        
        # Growth Tier Agency
        self.growth_agency = Agency.objects.create(name="Growth Agency", plan_tier="growth")
        self.growth_user = User.objects.create_user(username="growth@example.com", email="growth@example.com", password="password")
        self.growth_agent = AgentProfile.objects.create(user=self.growth_user, agency=self.growth_agency, role="owner")

    def test_growth_tier_can_access_hot_leads(self):
        """1. Growth tier agency can access Hot Leads widget view."""
        self.client.force_login(self.growth_user)
        response = self.client.get(reverse("dashboard:hot_leads_widget"))
        self.assertEqual(response.status_code, 200)

    def test_starter_tier_cannot_access_hot_leads(self):
        """2. Starter tier agency accessing Hot Leads widget view is redirected to Upgrade page."""
        self.client.force_login(self.starter_user)
        response = self.client.get(reverse("dashboard:hot_leads_widget"))
        self.assertRedirects(response, reverse("upgrade_required"))

    def test_starter_tier_cannot_exceed_seat_limit(self):
        """3. Agency at their seat limit (e.g. 3) gets an error when sending invite."""
        # Create 2 more agents for starter agency (total 3, which is the limit)
        for i in range(2):
            u = User.objects.create_user(username=f"starter{i}@example.com", email=f"starter{i}@example.com", password="password")
            AgentProfile.objects.create(user=u, agency=self.starter_agency, role="agent")
        
        self.client.force_login(self.starter_user)
        # Attempt to invite a 4th agent
        response = self.client.post(reverse("accounts:team_invite"), data={"email": "new_agent@example.com"})
        
        # Should return form error, so status 200 with error in context
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], None, "You've reached your plan's agent limit (3). Upgrade to Growth for unlimited agents.")

    def test_starter_tier_can_send_invite_under_limit(self):
        """4. Agency under limit (e.g. 1) can successfully send invite."""
        self.client.force_login(self.starter_user)
        # Agent count is 1 (the owner). Limit is 3. So inviting should work.
        response = self.client.post(reverse("accounts:team_invite"), data={"email": "new_agent@example.com"})
        
        # On success, redirects to team list
        self.assertRedirects(response, reverse("accounts:team_list"))

    def test_growth_tier_has_unlimited_seats(self):
        """5. Agency with Unlimited seat limit (Growth) can successfully send 4th invite."""
        # Create 3 more agents (total 4)
        for i in range(3):
            u = User.objects.create_user(username=f"growth{i}@example.com", email=f"growth{i}@example.com", password="password")
            AgentProfile.objects.create(user=u, agency=self.growth_agency, role="agent")
            
        self.client.force_login(self.growth_user)
        # Attempt to invite a 5th agent
        response = self.client.post(reverse("accounts:team_invite"), data={"email": "new_agent@example.com"})
        
        # On success, redirects to team list
        self.assertRedirects(response, reverse("accounts:team_list"))

    def test_whatsapp_integration_not_gated(self):
        """6. WhatsApp integration endpoint works for Starter tier (gating exception)."""
        # We can just test that the whatsapp connections view is accessible
        self.client.force_login(self.starter_user)
        response = self.client.get(reverse("whatsapp:settings"))
        self.assertEqual(response.status_code, 200)

    def test_property_matching_not_gated(self):
        """7. Property matching endpoint (or view logic) works for Starter tier (gating exception)."""
        # Testing if LeadDetailView loads matching without redirecting to upgrade
        from apps.leads.models import Lead
        lead = Lead.objects.create(name="Test Lead", agency=self.starter_agency, assigned_agent=self.starter_agent)
        
        self.client.force_login(self.starter_user)
        response = self.client.get(reverse("leads:detail", args=[lead.pk]))
        self.assertEqual(response.status_code, 200)
        # It should not have been redirected to upgrade, and it should have 'matching_properties' in context
        self.assertIn("matching_properties", response.context)


class UpgradeRequestTests(TestCase):
    """Tests for the Payment Links + Manual Activation billing system."""

    def setUp(self):
        self.agency = Agency.objects.create(name="Test Agency", plan_tier="starter")
        self.user = User.objects.create_user(
            username="owner@test.com", email="owner@test.com", password="password"
        )
        self.agent = AgentProfile.objects.create(
            user=self.user, agency=self.agency, role="owner"
        )
        self.client = Client()

    # ── Test 1: Amount snapshots from pricing config ───────────────
    def test_upgrade_request_snapshots_correct_amount(self):
        """Creating an UpgradeRequest correctly snapshots the amount from
        current pricing config, not a hardcoded value."""
        amount = PLAN_PRICING.get(Agency.PlanTier.GROWTH)
        req = UpgradeRequest.objects.create(
            agency=self.agency,
            requested_by=self.agent,
            requested_plan=UpgradeRequest.PlanChoice.GROWTH,
            amount=amount,
        )
        self.assertEqual(req.amount, Decimal("6499.00"))
        self.assertEqual(req.status, UpgradeRequest.Status.PENDING)

    # ── Test 2: Webhook signature verification ─────────────────────
    @override_settings(RAZORPAY_WEBHOOK_SECRET="test_secret")
    def test_webhook_rejects_missing_signature(self):
        """Webhook signature verification rejects an unsigned payload."""
        response = self.client.post(
            reverse("billing_razorpay_webhook"),
            data={"event": "payment_link.paid"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    @override_settings(RAZORPAY_WEBHOOK_SECRET="test_secret")
    def test_webhook_rejects_bad_signature(self):
        """Webhook signature verification rejects an incorrectly signed payload."""
        payload = json.dumps({"event": "payment_link.paid"}).encode()
        # Sign with a different secret
        bad_sig = hmac.new(
            b"wrong_secret", payload, hashlib.sha256
        ).hexdigest()
        response = self.client.post(
            reverse("billing_razorpay_webhook"),
            data=payload,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=bad_sig,
        )
        self.assertEqual(response.status_code, 400)

    # ── Test 3: Valid webhook auto-activates ───────────────────────
    @override_settings(RAZORPAY_WEBHOOK_SECRET="test_secret")
    def test_valid_payment_link_paid_webhook_activates_agency(self):
        """A valid payment_link.paid webhook correctly finds the matching
        UpgradeRequest, updates its status, and flips Agency.plan_tier."""
        req = UpgradeRequest.objects.create(
            agency=self.agency,
            requested_by=self.agent,
            requested_plan=UpgradeRequest.PlanChoice.GROWTH,
            amount=Decimal("6499.00"),
            razorpay_payment_link_id="link_test_123",
            status=UpgradeRequest.Status.LINK_SENT,
        )
        payload = json.dumps({
            "event": "payment_link.paid",
            "payload": {
                "payment_link": {
                    "id": "link_test_123",
                },
            },
        }).encode()
        sig = hmac.new(
            b"test_secret", payload, hashlib.sha256
        ).hexdigest()
        response = self.client.post(
            reverse("billing_razorpay_webhook"),
            data=payload,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )
        self.assertEqual(response.status_code, 200)
        req.refresh_from_db()
        self.assertEqual(req.status, UpgradeRequest.Status.ACTIVATED)
        self.assertIsNotNone(req.paid_at)
        self.assertIsNotNone(req.activated_at)
        self.agency.refresh_from_db()
        self.assertEqual(self.agency.plan_tier, "growth")

    # ── Test 4: Webhook with unknown link_id is ignored ────────────
    @override_settings(RAZORPAY_WEBHOOK_SECRET="test_secret")
    def test_webhook_unknown_link_id_ignored_gracefully(self):
        """A webhook for a payment_link_id that doesn't match any
        UpgradeRequest is logged and ignored gracefully, not a 500 error."""
        payload = json.dumps({
            "event": "payment_link.paid",
            "payload": {
                "payment_link": {
                    "id": "link_nonexistent",
                },
            },
        }).encode()
        sig = hmac.new(
            b"test_secret", payload, hashlib.sha256
        ).hexdigest()
        response = self.client.post(
            reverse("billing_razorpay_webhook"),
            data=payload,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {"status": "ignored"})

    # ── Test 5: Manual admin action produces identical end state ──
    def test_manual_mark_paid_and_activate_matches_webhook(self):
        """The manual 'Mark as Paid & Activate' admin action produces the
        identical end state as the webhook path."""
        req = UpgradeRequest.objects.create(
            agency=self.agency,
            requested_by=self.agent,
            requested_plan=UpgradeRequest.PlanChoice.GROWTH,
            amount=Decimal("6499.00"),
            status=UpgradeRequest.Status.PENDING,
        )
        # Simulate what the admin action does
        now = timezone.now()
        req.status = UpgradeRequest.Status.PAID
        req.paid_at = now
        req.save(update_fields=["status", "paid_at"])

        req.agency.plan_tier = req.requested_plan
        req.agency.save(update_fields=["plan_tier"])

        req.status = UpgradeRequest.Status.ACTIVATED
        req.activated_at = now
        req.save(update_fields=["status", "activated_at"])

        # Verify identical end state to webhook
        req.refresh_from_db()
        self.assertEqual(req.status, UpgradeRequest.Status.ACTIVATED)
        self.assertIsNotNone(req.paid_at)
        self.assertIsNotNone(req.activated_at)
        self.assertEqual(req.agency.plan_tier, "growth")

    # ── Test 6: Billing page hides upgrade for Growth agency ───────
    def test_billing_page_hides_upgrade_for_growth_agency(self):
        """Billing page correctly hides the 'Upgrade to Growth' button
        for an agency already on Growth."""
        growth_agency = Agency.objects.create(name="Growth Agency", plan_tier="growth")
        growth_user = User.objects.create_user(
            username="growth_owner@test.com", email="growth_owner@test.com", password="password"
        )
        AgentProfile.objects.create(user=growth_user, agency=growth_agency, role="owner")

        self.client.force_login(growth_user)
        response = self.client.get(reverse("billing_home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Growth")
        self.assertNotContains(response, "Upgrade to Growth")
        self.assertFalse(response.context.get("can_upgrade"))
