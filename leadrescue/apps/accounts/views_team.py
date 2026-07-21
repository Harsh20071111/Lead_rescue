from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, FormView, View

from apps.accounts.models import AgentProfile, AgentInvite
from apps.accounts.forms_team import AgentInviteForm, InviteSignupForm
from apps.accounts.services.email_service import send_agent_invite_email
from apps.core.mixins import AgencyScopedViewMixin, OwnerRequiredMixin

User = get_user_model()


class TeamListView(OwnerRequiredMixin, ListView):
    model = AgentProfile
    template_name = "accounts/team_list.html"
    context_object_name = "agents"

    def get_queryset(self):
        return AgentProfile.objects.filter(agency=self.agency).select_related("user")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pending_invites"] = AgentInvite.objects.filter(
            agency=self.agency, status=AgentInvite.Status.PENDING
        ).order_by("-created_at")
        
        from apps.billing.entitlements import get_limit
        max_agents = get_limit(self.agency, "max_agents")
        current_count = self.agency.agents.filter(is_active=True).count()
        context["max_agents"] = max_agents if max_agents is not None else "unlimited"
        context["current_agents"] = current_count
        context["can_invite"] = max_agents is None or current_count < max_agents
        
        return context


class AgentInviteView(OwnerRequiredMixin, FormView):
    template_name = "accounts/invite_form.html"
    form_class = AgentInviteForm
    success_url = reverse_lazy("accounts:team_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.billing.entitlements import get_limit
        max_agents = get_limit(self.agency, "max_agents")
        current_count = self.agency.agents.filter(is_active=True).count()
        context["max_agents"] = max_agents if max_agents is not None else "unlimited"
        context["current_agents"] = current_count
        context["can_invite"] = max_agents is None or current_count < max_agents
        return context

    def form_valid(self, form):
        from apps.billing.entitlements import is_within_limit
        current_count = self.agency.agents.filter(is_active=True).count()
        if not is_within_limit(self.agency, "max_agents", current_count):
            form.add_error(None, "You've reached your plan's agent limit (3). Upgrade to Growth for unlimited agents.")
            return self.form_invalid(form)

        invite = form.save(commit=False)
        invite.agency = self.agency
        invite.invited_by = self.agent_profile
        invite.save()

        if send_agent_invite_email(invite):
            messages.success(self.request, f"Invite sent to {invite.email}")
        else:
            messages.error(self.request, f"Failed to send email to {invite.email}, but invite was created.")

        return super().form_valid(form)


class AgentDeactivateView(OwnerRequiredMixin, View):
    def post(self, request, pk):
        # Do not allow deactivating yourself (the owner)
        agent = get_object_or_404(AgentProfile.objects.filter(agency=self.agency), pk=pk)
        if agent.user == request.user:
            messages.error(request, "You cannot deactivate your own account.")
        else:
            agent.is_active = False
            agent.save(update_fields=["is_active"])
            messages.success(request, f"{agent.user.email} deactivated.")
            
        if request.headers.get("HX-Request"):
            return render(request, "accounts/partials/agent_row.html", {"agent": agent})
        return redirect("accounts:team_list")


class AgentReactivateView(OwnerRequiredMixin, View):
    def post(self, request, pk):
        agent = get_object_or_404(AgentProfile.objects.filter(agency=self.agency), pk=pk)
        agent.is_active = True
        agent.save(update_fields=["is_active"])
        messages.success(request, f"{agent.user.email} reactivated.")
            
        if request.headers.get("HX-Request"):
            return render(request, "accounts/partials/agent_row.html", {"agent": agent})
        return redirect("accounts:team_list")


class AgentInviteDeleteView(OwnerRequiredMixin, View):
    def post(self, request, pk):
        invite = get_object_or_404(AgentInvite.objects.filter(agency=self.agency, status=AgentInvite.Status.PENDING), pk=pk)
        invite.delete()
        messages.success(request, f"Invite for {invite.email} deleted.")
        return redirect("accounts:team_list")


class InviteAcceptView(FormView):
    template_name = "accounts/invite_signup.html"
    form_class = InviteSignupForm

    def dispatch(self, request, *args, **kwargs):
        self.invite = get_object_or_404(AgentInvite, token=self.kwargs["token"])
        if self.invite.status != AgentInvite.Status.PENDING or self.invite.expires_at < timezone.now():
            messages.error(request, "This invite link is invalid or has expired.")
            return redirect("accounts:login")
        
        # Store token in session for social login
        request.session["invite_token"] = str(self.invite.token)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invite"] = self.invite
        return context

    def form_valid(self, form):
        from django.db import transaction
        from apps.billing.entitlements import is_within_limit

        current_count = self.invite.agency.agents.filter(is_active=True).count()
        if not is_within_limit(self.invite.agency, "max_agents", current_count):
            messages.error(self.request, "This agency has reached its maximum agent limit.")
            return redirect("accounts:login")
        
        with transaction.atomic():
            data = form.cleaned_data
            
            # Create user
            user = User.objects.create_user(
                username=self.invite.email,
                email=self.invite.email,
                password=data["password"],
                first_name=data["first_name"],
                last_name=data["last_name"]
            )
            
            # Create AgentProfile linked to the existing agency
            agent_profile = AgentProfile.objects.create(
                user=user,
                agency=self.invite.agency,
                role=AgentProfile.Role.AGENT,
                phone="N/A",
                is_active=True
            )
            
            # Mark invite as ACCEPTED
            self.invite.status = AgentInvite.Status.ACCEPTED
            self.invite.save(update_fields=["status"])
            
            # Clear session
            if "invite_token" in self.request.session:
                del self.request.session["invite_token"]

        try:
            if not agent_profile.welcome_email_sent:
                from apps.accounts.services.email_service import send_welcome_email
                if send_welcome_email(user):
                    agent_profile.welcome_email_sent = True
                    agent_profile.save(update_fields=['welcome_email_sent'])
        except Exception:
            pass

        messages.success(self.request, "Account created successfully. Please sign in.")
        return redirect("accounts:login")
