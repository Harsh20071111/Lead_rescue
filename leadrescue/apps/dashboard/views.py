import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.utils import timezone
from django.views.generic import TemplateView

from apps.accounts.models import AgentProfile
from apps.leads.models import Activity, Lead, Task


class DashboardHomeView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.agent_profile
        agency = profile.agency
        is_owner = profile.role == AgentProfile.Role.OWNER
        today = timezone.localdate()

        leads = Lead.objects.for_agency(agency)
        activities = Activity.objects.for_agency(agency).select_related(
            "agent__user", "lead", "property"
        )
        tasks = Task.objects.filter(lead__agency=agency, is_completed=False)

        if not is_owner:
            leads = leads.filter(assigned_agent=profile)
            activities = activities.filter(agent=profile)
            tasks = tasks.filter(assigned_agent=profile)

        status_counts = {
            item["status"]: item["count"]
            for item in leads.values("status").annotate(count=Count("id"))
        }
        source_counts = {
            item["source"]: item["count"]
            for item in leads.values("source").annotate(count=Count("id"))
        }

        context.update(
            {
                "agency_name": agency.name,
                "owner_name": self.request.user.get_full_name()
                or self.request.user.email
                or self.request.user.username,
                "is_owner": is_owner,
                "stats": {
                    "total_leads": leads.count(),
                    "new_leads": leads.filter(status=Lead.LeadStatus.NEW).count(),
                    "followups_today": tasks.filter(due_date__date=today).count(),
                    "missed_followups": tasks.filter(due_date__date__lt=today).count(),
                    "site_visits": leads.filter(status=Lead.LeadStatus.SITE_VISIT).count(),
                    "closed_deals": leads.filter(status=Lead.LeadStatus.CONVERTED).count(),
                },
                "recent_activity": activities.order_by("-created_at")[:10],
                "status_labels": json.dumps([
                    label for value, label in Lead.LeadStatus.choices if value in status_counts
                ]),
                "status_values": json.dumps([
                    status_counts[value]
                    for value, label in Lead.LeadStatus.choices
                    if value in status_counts
                ]),
                "source_labels": json.dumps([
                    label for value, label in Lead.LeadSource.choices if value in source_counts
                ]),
                "source_values": json.dumps([
                    source_counts[value]
                    for value, label in Lead.LeadSource.choices
                    if value in source_counts
                ]),
            }
        )
        return context
