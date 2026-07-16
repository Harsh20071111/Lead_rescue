from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class DashboardHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get AgentProfile and Agency
        try:
            profile = user.agent_profile
            agency = profile.agency
            context['agency_name'] = agency.name
            context['owner_name'] = user.get_full_name() or user.username
        except AttributeError:
            context['agency_name'] = "No Agency Associated"
            context['owner_name'] = user.get_full_name() or user.username

        # Stat placeholders as requested (no real analytics)
        context['stats'] = {
            'total_leads': 0,
            'new_leads': 0,
            'active_properties': 0,
            'converted_leads': 0,
        }
        return context
