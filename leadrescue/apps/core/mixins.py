from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from apps.accounts.models import AgentProfile


class AgencyScopedViewMixin(LoginRequiredMixin):
    agent_lookup_field = "assigned_agent"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.agent_profile = request.user.agent_profile
        self.agency = self.agent_profile.agency
        return super().dispatch(request, *args, **kwargs)

    def is_owner(self):
        return self.agent_profile.role == AgentProfile.Role.OWNER

    def scope_queryset_for_profile(self, queryset):
        queryset = queryset.for_agency(self.agency)
        if self.is_owner():
            return queryset
        return queryset.filter(**{self.agent_lookup_field: self.agent_profile})

    def get_agent_choices(self):
        return self.agency.agents.filter(is_active=True).select_related("user")


class OwnerRequiredMixin(AgencyScopedViewMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.agent_profile = request.user.agent_profile
        self.agency = self.agent_profile.agency
        if self.agent_profile.role != AgentProfile.Role.OWNER:
            raise PermissionDenied
        return super(AgencyScopedViewMixin, self).dispatch(request, *args, **kwargs)
