from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, DetailView

from apps.billing.models import UpgradeRequest
from apps.billing.pricing import PLAN_PRICING
from apps.agencies.models import Agency


class UpgradeRequiredView(TemplateView):
    template_name = "billing/upgrade_required.html"


class OwnerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return (
            hasattr(self.request.user, "agent_profile")
            and self.request.user.agent_profile.role == "owner"
        )


class UpgradeView(OwnerRequiredMixin, DetailView):
    template_name = "billing/upgrade.html"

    def get_object(self, queryset=None):
        plan = self.kwargs.get("plan")
        valid = dict(Agency.PlanTier.choices)
        if plan not in valid:
            return None
        return plan

    def get(self, request, *args, **kwargs):
        plan = self.get_object()
        if plan is None:
            return redirect("billing_home")
        agency = request.user.agent_profile.agency
        if agency.plan_tier == plan:
            return redirect("billing_home")
        if UpgradeRequest.objects.filter(
            agency=agency, requested_plan=plan, status__in=[
                UpgradeRequest.Status.PENDING,
                UpgradeRequest.Status.LINK_SENT,
            ]
        ).exists():
            return redirect("billing_home")
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        plan = self.get_object()
        if plan is None:
            return redirect("billing_home")
        agency = request.user.agent_profile.agency
        if agency.plan_tier == plan:
            return redirect("billing_home")
        amount = PLAN_PRICING.get(plan)
        if amount is None:
            return redirect("billing_home")
        UpgradeRequest.objects.create(
            agency=agency,
            requested_by=request.user.agent_profile,
            requested_plan=plan,
            amount=amount,
        )
        return redirect("billing_confirmation")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan = self.get_object()
        context["plan"] = plan
        context["plan_label"] = dict(Agency.PlanTier.choices).get(plan, plan)
        context["amount"] = PLAN_PRICING.get(plan)
        return context


class UpgradeConfirmationView(OwnerRequiredMixin, TemplateView):
    template_name = "billing/upgrade_confirmation.html"


class RazorpayCallbackView(LoginRequiredMixin, TemplateView):
    template_name = "billing/razorpay_callback.html"


class BillingHomeView(OwnerRequiredMixin, TemplateView):
    template_name = "billing/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agency = self.request.user.agent_profile.agency
        context["agency"] = agency
        context["current_plan_label"] = agency.get_plan_tier_display()
        context["upgrade_requests"] = UpgradeRequest.objects.filter(agency=agency)[:20]
        context["can_upgrade"] = agency.plan_tier != Agency.PlanTier.GROWTH
        return context
