from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.mixins import AccessMixin
from apps.billing.entitlements import has_feature

def require_feature(feature_name):
    """View decorator that redirects to an upgrade page if the agency's plan doesn't include the feature."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and hasattr(request.user, 'agent_profile'):
                agency = request.user.agent_profile.agency
                if has_feature(agency, feature_name):
                    return view_func(request, *args, **kwargs)
            return redirect(reverse('upgrade_required'))
        return _wrapped_view
    return decorator

class RequireFeatureMixin(AccessMixin):
    """View mixin that redirects to an upgrade page if the agency's plan doesn't include the feature."""
    required_feature = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'agent_profile'):
            return self.handle_no_permission()
        
        agency = request.user.agent_profile.agency
        if not has_feature(agency, self.required_feature):
            return redirect(reverse('upgrade_required'))
            
        return super().dispatch(request, *args, **kwargs)
