from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import AgentProfile, User
from apps.agencies.models import Agency
from apps.core.choices import BHKChoices
from apps.leads.models import Activity, Lead
from apps.matching.services import (
    WEIGHT_BHK,
    WEIGHT_BUDGET,
    WEIGHT_LOCATION,
    MatchResult,
    match_leads_for_property,
    match_properties_for_lead,
    _score_bhk,
    _score_budget,
    _score_location,
)
from apps.properties.models import Property


class MatchingServiceTests(TestCase):
    """Tests for the rule-based property matching engine."""

    def setUp(self):
        self.agency_a = Agency.objects.create(
            name="Agency A",
            owner_email="owner-a@example.com",
            owner_phone="1111111111",
            city="Ahmedabad",
        )
        self.agency_b = Agency.objects.create(
            name="Agency B",
            owner_email="owner-b@example.com",
            owner_phone="2222222222",
            city="Mumbai",
        )
        self.owner_user = User.objects.create_user(
            username="owner-a", email="owner-a@example.com", password="pass"
        )
        self.owner = AgentProfile.objects.create(
            user=self.owner_user,
            agency=self.agency_a,
            role=AgentProfile.Role.OWNER,
            phone="1111111111",
        )

        # Lead: wants 2BHK, budget 50L-80L, location Bopal
        self.lead = Lead.objects.create(
            agency=self.agency_a,
            assigned_agent=self.owner,
            name="Test Lead",
            phone="9000000001",
            preferred_bhk=BHKChoices.TWO_BHK,
            budget_min=Decimal("5000000"),
            budget_max=Decimal("8000000"),
            preferred_location="Bopal",
        )

        # Property A: exact match — 2BHK, 65L, Bopal Ahmedabad
        self.property_a = Property.objects.create(
            agency=self.agency_a,
            title="2BHK in Bopal",
            city="Ahmedabad",
            locality="Bopal",
            price=Decimal("6500000"),
            bhk=BHKChoices.TWO_BHK,
            status=Property.PropertyStatus.AVAILABLE,
        )
        # Property B: partial — 3BHK, 70L, Bopal (adjacent BHK)
        self.property_b = Property.objects.create(
            agency=self.agency_a,
            title="3BHK in Bopal",
            city="Ahmedabad",
            locality="Bopal",
            price=Decimal("7000000"),
            bhk=BHKChoices.THREE_BHK,
            status=Property.PropertyStatus.AVAILABLE,
        )
        # Property C: no match — 1BHK, 30L, different city
        self.property_c = Property.objects.create(
            agency=self.agency_a,
            title="1BHK in Mumbai",
            city="Mumbai",
            locality="Andheri",
            price=Decimal("3000000"),
            bhk=BHKChoices.ONE_BHK,
            status=Property.PropertyStatus.AVAILABLE,
        )
        # Property D: from different agency — should never appear
        self.property_d = Property.objects.create(
            agency=self.agency_b,
            title="2BHK Other Agency",
            city="Ahmedabad",
            locality="Bopal",
            price=Decimal("6000000"),
            bhk=BHKChoices.TWO_BHK,
            status=Property.PropertyStatus.AVAILABLE,
        )
        # Property E: sold — should not appear
        self.property_e = Property.objects.create(
            agency=self.agency_a,
            title="Sold 2BHK",
            city="Ahmedabad",
            locality="Bopal",
            price=Decimal("6000000"),
            bhk=BHKChoices.TWO_BHK,
            status=Property.PropertyStatus.SOLD,
        )

    # ---- Test 1: Exact match scores near 1.0 ----
    def test_exact_match_scores_near_1(self):
        results = match_properties_for_lead(self.lead)
        self.assertTrue(len(results) >= 1)
        top = results[0]
        self.assertEqual(top.object.pk, self.property_a.pk)
        self.assertGreaterEqual(top.score, 0.9)
        self.assertTrue(top.breakdown["bhk"].matched)
        self.assertTrue(top.breakdown["budget"].matched)
        self.assertTrue(top.breakdown["location"].matched)

    # ---- Test 2: No matching properties returns empty, not error ----
    def test_no_matching_properties_returns_empty(self):
        lead_no_match = Lead.objects.create(
            agency=self.agency_a,
            assigned_agent=self.owner,
            name="No Match Lead",
            phone="9000000099",
            preferred_bhk=BHKChoices.FOUR_PLUS_BHK,
            budget_min=Decimal("100000"),
            budget_max=Decimal("200000"),
            preferred_location="Satellite",
        )
        results = match_properties_for_lead(lead_no_match)
        self.assertEqual(results, [])

    # ---- Test 3: Multi-tenant boundary — never cross agencies ----
    def test_never_returns_properties_from_different_agency(self):
        results = match_properties_for_lead(self.lead)
        result_pks = [r.object.pk for r in results]
        self.assertNotIn(self.property_d.pk, result_pks)

    # ---- Test 4: Never returns non-AVAILABLE properties ----
    def test_never_returns_non_available_properties(self):
        results = match_properties_for_lead(self.lead)
        result_pks = [r.object.pk for r in results]
        self.assertNotIn(self.property_e.pk, result_pks)

    # ---- Test 5: Lead with no budget still returns reasonable matches ----
    def test_lead_without_budget_returns_matches(self):
        lead_no_budget = Lead.objects.create(
            agency=self.agency_a,
            assigned_agent=self.owner,
            name="No Budget Lead",
            phone="9000000088",
            preferred_bhk=BHKChoices.TWO_BHK,
            preferred_location="Bopal",
        )
        results = match_properties_for_lead(lead_no_budget)
        self.assertTrue(len(results) >= 1)
        # Budget dimension should be skipped (scored as full)
        top = results[0]
        self.assertEqual(top.object.pk, self.property_a.pk)
        self.assertTrue(top.breakdown["budget"].matched)

    # ---- Test 6: match_leads_for_property is symmetric ----
    def test_match_leads_for_property_symmetric(self):
        lead_results = match_properties_for_lead(self.lead)
        prop_results = match_leads_for_property(self.property_a)

        lead_score_for_prop = next(
            (r.score for r in lead_results if r.object.pk == self.property_a.pk), None
        )
        prop_score_for_lead = next(
            (r.score for r in prop_results if r.object.pk == self.lead.pk), None
        )

        self.assertIsNotNone(lead_score_for_prop)
        self.assertIsNotNone(prop_score_for_lead)
        self.assertAlmostEqual(lead_score_for_prop, prop_score_for_lead, places=4)

    # ---- Test 6b: match_leads_for_property scoped to same agency ----
    def test_match_leads_for_property_scoped_to_agency(self):
        other_agency_lead = Lead.objects.create(
            agency=self.agency_b,
            assigned_agent=self.owner,
            name="Other Agency Lead",
            phone="9000000077",
            preferred_bhk=BHKChoices.TWO_BHK,
            budget_min=Decimal("5000000"),
            budget_max=Decimal("8000000"),
            preferred_location="Bopal",
        )
        results = match_leads_for_property(self.property_a)
        result_pks = [r.object.pk for r in results]
        self.assertNotIn(other_agency_lead.pk, result_pks)

    # ---- Test 7: Link property action sets linked_property and creates Activity ----
    def test_link_property_sets_linked_and_creates_activity(self):
        from django.test import Client

        client = Client()
        client.force_login(self.owner_user)

        response = client.post(
            f"/leads/{self.lead.pk}/link/{self.property_a.pk}/"
        )

        self.lead.refresh_from_db()
        self.assertEqual(self.lead.linked_property, self.property_a)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Activity.objects.for_agency(self.agency_a).filter(
                lead=self.lead,
                activity_type=Activity.ActivityType.NOTE,
                content__icontains="Linked property",
            ).exists()
        )


class ScoringUnitTests(TestCase):
    """Unit tests for individual scoring dimensions."""

    def test_bhk_exact_match(self):
        score, bd = _score_bhk(BHKChoices.TWO_BHK, BHKChoices.TWO_BHK)
        self.assertEqual(score, 1.0)
        self.assertTrue(bd.matched)

    def test_bhk_adjacent(self):
        score, bd = _score_bhk(BHKChoices.TWO_BHK, BHKChoices.THREE_BHK)
        self.assertEqual(score, 0.5)
        self.assertEqual(bd.matched, "partial")

    def test_bhk_no_match(self):
        score, bd = _score_bhk(BHKChoices.TWO_BHK, BHKChoices.ONE_BHK)
        self.assertEqual(score, 0.5)  # adjacent
        score, bd = _score_bhk(BHKChoices.TWO_BHK, BHKChoices.FOUR_BHK)
        self.assertEqual(score, 0.0)

    def test_bhk_missing(self):
        score, bd = _score_bhk(None, BHKChoices.TWO_BHK)
        self.assertEqual(score, 0.0)
        score, bd = _score_bhk(BHKChoices.TWO_BHK, None)
        self.assertEqual(score, 0.0)

    def test_budget_within_range(self):
        score, bd = _score_budget(6500000, 5000000, 8000000)
        self.assertEqual(score, 1.0)
        self.assertTrue(bd.matched)

    def test_budget_outside_15_percent(self):
        # 4.6M is within 15% of 5M min (tolerance = 450k, gap = 400k)
        score, bd = _score_budget(4600000, 5000000, 8000000)
        self.assertEqual(score, 0.5)
        self.assertEqual(bd.matched, "partial")

    def test_budget_far_outside(self):
        score, bd = _score_budget(1000000, 5000000, 8000000)
        self.assertEqual(score, 0.0)

    def test_budget_both_missing_skips(self):
        score, bd = _score_budget(6500000, None, None)
        self.assertEqual(score, 1.0)
        self.assertTrue(bd.matched)

    def test_location_exact(self):
        score, bd = _score_location("Bopal", "Bopal", "Ahmedabad")
        self.assertEqual(score, 1.0)
        self.assertTrue(bd.matched)

    def test_location_partial_locality(self):
        score, bd = _score_location("Bopal", "Bopal, Ahmedabad", "Ahmedabad")
        self.assertEqual(score, 1.0)

    def test_location_same_city(self):
        score, bd = _score_location("Ahmedabad", "Satellite", "Ahmedabad")
        self.assertEqual(score, 1.0)

    def test_location_no_match(self):
        score, bd = _score_location("Bopal", "Andheri", "Mumbai")
        self.assertEqual(score, 0.0)

    def test_location_missing_pref(self):
        score, bd = _score_location("", "Bopal", "Ahmedabad")
        self.assertEqual(score, 1.0)

    def test_weights_are_constants(self):
        self.assertEqual(WEIGHT_BHK + WEIGHT_BUDGET + WEIGHT_LOCATION, 1.0)
