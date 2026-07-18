from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal
from apps.agencies.models import Agency
from apps.accounts.models import User, AgentProfile
from apps.core.choices import BHKChoices
from apps.properties.models import Property
from .models import Lead, Activity


class CoreDataModelTests(TestCase):
    def setUp(self):
        # Create Agency 1
        self.agency_1 = Agency.objects.create(name="Agency 1", owner_email="a1@example.com")
        self.user_1 = User.objects.create_user(username="u1", email="u1@example.com")
        self.agent_1 = AgentProfile.objects.create(user=self.user_1, agency=self.agency_1, role="owner")
        
        # Create Agency 2
        self.agency_2 = Agency.objects.create(name="Agency 2", owner_email="a2@example.com")
        self.user_2 = User.objects.create_user(username="u2", email="u2@example.com")
        self.agent_2 = AgentProfile.objects.create(user=self.user_2, agency=self.agency_2, role="owner")

        # Create properties and leads for Agency 1
        self.prop_1 = Property.objects.create(agency=self.agency_1, title="Prop 1", price=10000)
        self.lead_1 = Lead.objects.create(agency=self.agency_1, name="Lead 1")

        # Create properties and leads for Agency 2
        self.prop_2 = Property.objects.create(agency=self.agency_2, title="Prop 2", price=20000)
        self.lead_2 = Lead.objects.create(agency=self.agency_2, name="Lead 2")

    def test_lead_agency_scoped_manager(self):
        """Lead.objects.for_agency(agency_1) returns only agency_1's leads."""
        leads = Lead.objects.for_agency(self.agency_1)
        self.assertEqual(leads.count(), 1)
        self.assertEqual(leads.first(), self.lead_1)

    def test_property_agency_scoped_manager(self):
        """Property.objects.for_agency(agency_1) returns only agency_1's properties."""
        properties = Property.objects.for_agency(self.agency_1)
        self.assertEqual(properties.count(), 1)
        self.assertEqual(properties.first(), self.prop_1)

    def test_activity_clean_validation(self):
        """Activity.clean() raises ValidationError when both lead and property are None."""
        activity = Activity(
            agent=self.agent_1,
            activity_type=Activity.ActivityType.CALL,
            content="test"
            # leaving lead and property None
        )
        with self.assertRaises(ValidationError):
            activity.clean()

    def test_activity_auto_populate_agency(self):
        """Creating Activity from a Lead auto-populates Activity.agency."""
        activity = Activity.objects.create(
            lead=self.lead_1,
            agent=self.agent_1,
            activity_type=Activity.ActivityType.CALL,
            content="test"
        )
        self.assertEqual(activity.agency, self.agency_1)

    def test_lead_property_matching_fields_round_trip(self):
        lead = Lead.objects.create(
            agency=self.agency_1,
            name="Budgeted Lead",
            budget_min=Decimal("5000000.00"),
            budget_max=Decimal("7500000.00"),
            preferred_location="Andheri",
            preferred_bhk=BHKChoices.TWO_BHK,
        )

        saved_lead = Lead.objects.get(pk=lead.pk)

        self.assertEqual(saved_lead.budget_min, Decimal("5000000.00"))
        self.assertEqual(saved_lead.budget_max, Decimal("7500000.00"))
        self.assertEqual(saved_lead.preferred_location, "Andheri")
        self.assertEqual(saved_lead.preferred_bhk, BHKChoices.TWO_BHK)

    def test_property_amenities_round_trip_as_list(self):
        property_obj = Property.objects.create(
            agency=self.agency_1,
            title="Amenity Property",
            price=Decimal("9000000.00"),
            amenities=["Gym", "Parking"],
        )

        saved_property = Property.objects.get(pk=property_obj.pk)

        self.assertEqual(saved_property.amenities, ["Gym", "Parking"])
        self.assertIsInstance(saved_property.amenities, list)

    def test_new_fields_are_optional_for_backward_compatibility(self):
        lead = Lead.objects.create(agency=self.agency_1, name="Legacy Lead")
        property_obj = Property.objects.create(
            agency=self.agency_1,
            title="Legacy Property",
            price=Decimal("8000000.00"),
        )

        self.assertIsNone(lead.budget_min)
        self.assertIsNone(lead.budget_max)
        self.assertEqual(lead.preferred_location, "")
        self.assertIsNone(lead.preferred_bhk)
        self.assertEqual(property_obj.project_name, "")
        self.assertEqual(property_obj.builder, "")
        self.assertIsNone(property_obj.bhk)
        self.assertIsNone(property_obj.area_sqft)
        self.assertEqual(property_obj.amenities, [])
