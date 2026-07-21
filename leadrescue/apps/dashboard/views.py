import json
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.utils import timezone
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator

from apps.billing.decorators import require_feature

from apps.accounts.models import AgentProfile
from apps.leads.models import Activity, Lead, Task
from apps.leads.templatetags.lead_extras import SOURCE_COLORS, STATUS_COLORS


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

        # Current period = last 30 days
        period_start = today - timedelta(days=30)
        prior_start = period_start - timedelta(days=30)

        def period_count(qs, start, end):
            return qs.filter(created_at__gte=start, created_at__lt=end).count()

        def pct_trend(current, prior):
            if prior == 0:
                return None, None
            delta = ((current - prior) / prior) * 100
            direction = "up" if delta > 0 else ("down" if delta < 0 else "flat")
            return delta, direction

        # --- Total Leads ---
        total_leads_count = leads.count()
        total_period = period_count(leads, period_start, today)
        total_prior = period_count(leads, prior_start, period_start)
        total_delta, total_dir = pct_trend(total_period, total_prior)

        # --- New Leads (status=new) ---
        new_qs = leads.filter(status=Lead.LeadStatus.NEW)
        new_leads_count = new_qs.count()
        new_period = period_count(new_qs, period_start, today)
        new_prior = period_count(new_qs, prior_start, period_start)
        new_delta, new_dir = pct_trend(new_period, new_prior)

        # --- Follow-ups Today ---
        followups_count = tasks.filter(due_date__date=today).count()
        prior_followups = tasks.filter(
            due_date__date__gte=prior_start, due_date__date__lt=period_start
        ).count()
        fd, fdir = pct_trend(followups_count, prior_followups)

        # --- Missed Follow-ups ---
        missed_count = tasks.filter(due_date__date__lt=today).count()
        prior_missed = tasks.filter(
            due_date__date__gte=prior_start, due_date__date__lt=period_start,
            is_completed=False
        ).count()
        md, mdir = pct_trend(missed_count, prior_missed)

        # --- Site Visits ---
        sv_qs = leads.filter(status=Lead.LeadStatus.SITE_VISIT)
        sv_count = sv_qs.count()
        sv_period = period_count(sv_qs, period_start, today)
        sv_prior = period_count(sv_qs, prior_start, period_start)
        sv_delta, sv_dir = pct_trend(sv_period, sv_prior)

        # --- Closed Deals ---
        closed_qs = leads.filter(status=Lead.LeadStatus.CONVERTED)
        closed_count = closed_qs.count()
        closed_period = period_count(closed_qs, period_start, today)
        closed_prior = period_count(closed_qs, prior_start, period_start)
        closed_delta, closed_dir = pct_trend(closed_period, closed_prior)

        status_counts_data = {
            item["status"]: item["count"]
            for item in leads.values("status").annotate(count=Count("id"))
        }
        source_counts_data = {
            item["source"]: item["count"]
            for item in leads.values("source").annotate(count=Count("id"))
        }

        status_labels = [
            label for value, label in Lead.LeadStatus.choices if value in status_counts_data
        ]
        status_values = [
            status_counts_data[value]
            for value, label in Lead.LeadStatus.choices
            if value in status_counts_data
        ]
        status_total = sum(status_values) or 1
        status_pct = [round((v / status_total) * 100) for v in status_values]

        status_color_list = [
            STATUS_COLORS.get(value, "#78716c")
            for value, label in Lead.LeadStatus.choices
            if value in status_counts_data
        ]

        source_labels = [
            label for value, label in Lead.LeadSource.choices if value in source_counts_data
        ]
        source_values = [
            source_counts_data[value]
            for value, label in Lead.LeadSource.choices
            if value in source_counts_data
        ]
        source_color_list = [
            SOURCE_COLORS.get(value, "#78716c")
            for value, label in Lead.LeadSource.choices
            if value in source_counts_data
        ]

        source_legend = [
            {
                "label": label,
                "value": source_counts_data[value],
                "color": SOURCE_COLORS.get(value, "#78716c"),
            }
            for value, label in Lead.LeadSource.choices
            if value in source_counts_data
        ]

        status_legend = [
            {
                "label": label,
                "value": status_counts_data[value],
                "color": STATUS_COLORS.get(value, "#78716c"),
                "pct": round(
                    (status_counts_data[value] / status_total) * 100
                ),
            }
            for value, label in Lead.LeadStatus.choices
            if value in status_counts_data
        ]

        from apps.billing.entitlements import has_feature
        context.update(
            {
                "agency_name": agency.name,
                "owner_name": self.request.user.get_full_name()
                or self.request.user.email
                or self.request.user.username,
                "is_owner": is_owner,
                "has_ai_scoring": has_feature(agency, "ai_lead_scoring"),
                "has_advanced_analytics": has_feature(agency, "advanced_analytics"),
                "stats": {
                    "total_leads": total_leads_count,
                    "new_leads": new_leads_count,
                    "followups_today": followups_count,
                    "missed_followups": missed_count,
                    "site_visits": sv_count,
                    "closed_deals": closed_count,
                },
                "trends": {
                    "total_leads": {
                        "delta": total_delta,
                        "direction": total_dir,
                    },
                    "new_leads": {"delta": new_delta, "direction": new_dir},
                    "followups_today": {
                        "delta": fd,
                        "direction": fdir,
                    },
                    "missed_followups": {
                        "delta": md,
                        "direction": mdir,
                    },
                    "site_visits": {"delta": sv_delta, "direction": sv_dir},
                    "closed_deals": {
                        "delta": closed_delta,
                        "direction": closed_dir,
                    },
                },
                "recent_activity": activities.order_by("-created_at")[:10],
                "status_labels": json.dumps(status_labels),
                "status_values": json.dumps(status_values),
                "status_colors": json.dumps(status_color_list),
                "status_pct": json.dumps(status_pct),
                "status_legend": status_legend,
                "source_labels": json.dumps(source_labels),
                "source_values": json.dumps(source_values),
                "source_colors": json.dumps(source_color_list),
                "source_legend": source_legend,
            }
        )
        return context


@method_decorator(require_feature("ai_lead_scoring"), name="dispatch")
class HotLeadsWidgetView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/partials/hot_leads_widget.html"


@method_decorator(require_feature("advanced_analytics"), name="dispatch")
class AdvancedAnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/advanced_analytics.html"
