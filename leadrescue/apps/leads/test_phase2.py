from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AgentProfile, User
from apps.agencies.models import Agency
from apps.leads.models import Activity, Lead, Task


class Phase2ViewTests(TestCase):
    def setUp(self):
        self.agency_a = Agency.objects.create(
            name="Agency A",
            owner_email="owner-a@example.com",
            owner_phone="1111111111",
            city="Mumbai",
        )
        self.agency_b = Agency.objects.create(
            name="Agency B",
            owner_email="owner-b@example.com",
            owner_phone="2222222222",
            city="Pune",
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
        self.agent_a_user = User.objects.create_user(
            username="agent-a", email="agent-a@example.com", password="pass"
        )
        self.agent_a = AgentProfile.objects.create(
            user=self.agent_a_user,
            agency=self.agency_a,
            role=AgentProfile.Role.AGENT,
            phone="3333333333",
        )
        self.agent_b_user = User.objects.create_user(
            username="agent-b", email="agent-b@example.com", password="pass"
        )
        self.agent_b = AgentProfile.objects.create(
            user=self.agent_b_user,
            agency=self.agency_a,
            role=AgentProfile.Role.AGENT,
            phone="4444444444",
        )
        self.other_owner_user = User.objects.create_user(
            username="owner-b", email="owner-b@example.com", password="pass"
        )
        self.other_owner = AgentProfile.objects.create(
            user=self.other_owner_user,
            agency=self.agency_b,
            role=AgentProfile.Role.OWNER,
            phone="5555555555",
        )
        self.agent_a_lead = Lead.objects.create(
            agency=self.agency_a,
            assigned_agent=self.agent_a,
            name="Agent A Lead",
            phone="9000000001",
            status=Lead.LeadStatus.NEW,
            source=Lead.LeadSource.MANUAL,
        )
        self.agent_b_lead = Lead.objects.create(
            agency=self.agency_a,
            assigned_agent=self.agent_b,
            name="Agent B Lead",
            phone="9000000002",
            status=Lead.LeadStatus.CONTACTED,
            source=Lead.LeadSource.WEBSITE,
        )
        self.other_agency_lead = Lead.objects.create(
            agency=self.agency_b,
            assigned_agent=self.other_owner,
            name="Other Agency Lead",
            phone="9000000003",
            status=Lead.LeadStatus.NEW,
            source=Lead.LeadSource.REFERRAL,
        )

    def test_agent_cannot_view_or_edit_another_agents_lead(self):
        self.client.force_login(self.agent_a_user)

        detail_response = self.client.get(reverse("leads:detail", args=[self.agent_b_lead.pk]))
        edit_response = self.client.get(reverse("leads:edit", args=[self.agent_b_lead.pk]))

        self.assertIn(detail_response.status_code, [403, 404])
        self.assertIn(edit_response.status_code, [403, 404])
        self.assertNotContains(
            detail_response,
            self.agent_b_lead.name,
            status_code=detail_response.status_code,
        )

    def test_owner_can_view_and_assign_any_lead_in_agency(self):
        self.client.force_login(self.owner_user)

        detail_response = self.client.get(reverse("leads:detail", args=[self.agent_b_lead.pk]))
        assign_response = self.client.post(
            reverse("leads:assign", args=[self.agent_b_lead.pk]),
            {"assigned_agent": self.agent_a.pk},
        )
        self.agent_b_lead.refresh_from_db()

        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(assign_response.status_code, 302)
        self.assertEqual(self.agent_b_lead.assigned_agent, self.agent_a)

    def test_owner_from_other_agency_cannot_access_lead(self):
        self.client.force_login(self.other_owner_user)

        response = self.client.get(reverse("leads:detail", args=[self.agent_a_lead.pk]))

        self.assertIn(response.status_code, [403, 404])

    def test_changing_lead_status_creates_activity(self):
        self.client.force_login(self.agent_a_user)

        response = self.client.post(
            reverse("leads:edit", args=[self.agent_a_lead.pk]),
            {
                "name": self.agent_a_lead.name,
                "phone": self.agent_a_lead.phone,
                "email": "",
                "source": self.agent_a_lead.source,
                "status": Lead.LeadStatus.QUALIFIED,
                "budget_min": "",
                "budget_max": "",
                "preferred_location": "",
                "preferred_bhk": "",
                "linked_property": "",
                "notes": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Activity.objects.for_agency(self.agency_a).filter(
                lead=self.agent_a_lead,
                activity_type=Activity.ActivityType.STATUS_CHANGE,
                content__icontains="Status changed",
            ).exists()
        )

    def test_reassigning_lead_creates_activity(self):
        self.client.force_login(self.owner_user)

        response = self.client.post(
            reverse("leads:assign", args=[self.agent_a_lead.pk]),
            {"assigned_agent": self.agent_b.pk},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Activity.objects.for_agency(self.agency_a).filter(
                lead=self.agent_a_lead,
                activity_type=Activity.ActivityType.STATUS_CHANGE,
                content__icontains="Reassigned from",
            ).exists()
        )

    def test_dashboard_counts_match_seeded_scenario(self):
        Lead.objects.create(
            agency=self.agency_a,
            assigned_agent=self.agent_a,
            name="Site Visit Lead",
            phone="9000000004",
            status=Lead.LeadStatus.SITE_VISIT,
            source=Lead.LeadSource.GOOGLE,
        )
        Lead.objects.create(
            agency=self.agency_a,
            assigned_agent=self.agent_a,
            name="Closed Lead",
            phone="9000000005",
            status=Lead.LeadStatus.CONVERTED,
            source=Lead.LeadSource.REFERRAL,
        )
        Task.objects.create(
            lead=self.agent_a_lead,
            assigned_agent=self.agent_a,
            due_date=timezone.now(),
        )
        Task.objects.create(
            lead=self.agent_b_lead,
            assigned_agent=self.agent_b,
            due_date=timezone.now() - timedelta(days=1),
        )
        self.client.force_login(self.owner_user)

        response = self.client.get(reverse("dashboard:home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["stats"]["total_leads"], 4)
        self.assertEqual(response.context["stats"]["new_leads"], 1)
        self.assertEqual(response.context["stats"]["followups_today"], 1)
        self.assertEqual(response.context["stats"]["missed_followups"], 1)
        self.assertEqual(response.context["stats"]["site_visits"], 1)
        self.assertEqual(response.context["stats"]["closed_deals"], 1)

    def test_marking_task_complete_updates_dashboard_counts(self):
        missed_task = Task.objects.create(
            lead=self.agent_a_lead,
            assigned_agent=self.agent_a,
            due_date=timezone.now() - timedelta(days=1),
        )
        self.client.force_login(self.agent_a_user)

        before_response = self.client.get(reverse("dashboard:home"))
        complete_response = self.client.post(reverse("leads:complete_task", args=[missed_task.pk]))
        missed_task.refresh_from_db()
        after_response = self.client.get(reverse("dashboard:home"))

        self.assertEqual(before_response.context["stats"]["missed_followups"], 1)
        self.assertEqual(complete_response.status_code, 302)
        self.assertTrue(missed_task.is_completed)
        self.assertEqual(after_response.context["stats"]["missed_followups"], 0)
