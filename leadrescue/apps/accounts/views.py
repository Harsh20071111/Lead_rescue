from django.contrib.auth import get_user_model
from django.contrib.auth import login as auth_login
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from django.contrib.auth.views import LoginView as DefaultLoginView, LogoutView as DefaultLogoutView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache

from apps.agencies.models import Agency
from apps.accounts.models import AgentProfile
from .forms import SignupForm

User = get_user_model()


class SignupView(FormView):
    template_name = 'registration/signup.html'
    form_class = SignupForm
    success_url = reverse_lazy('accounts:login')

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        data = form.cleaned_data

        with transaction.atomic():
            name_parts = data['owner_name'].split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''

            user = form.save(commit=False)
            user.username = data['email']
            user.email = data['email']
            user.first_name = first_name
            user.last_name = last_name
            user.set_password(data['password1'])
            user.save()

            agency = Agency.objects.create(
                name=data['agency_name'],
                owner_phone=data['phone'],
                owner_email=data['email'],
                city='Not Specified'
            )

            agent_profile = AgentProfile.objects.create(
                user=user,
                agency=agency,
                role='owner',
                phone=data['phone']
            )

        try:
            if not agent_profile.welcome_email_sent:
                from apps.accounts.services.email_service import send_welcome_email
                if send_welcome_email(user):
                    agent_profile.welcome_email_sent = True
                    agent_profile.save(update_fields=['welcome_email_sent'])
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error("Welcome email failed for email signup %s: %s", user.email, e, exc_info=True)

        messages.success(self.request, "Account created. Please sign in.")
        return redirect(self.success_url)


class LoginView(DefaultLoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        if hasattr(user, 'agent_profile') and not user.agent_profile.is_active:
            messages.error(self.request, "Your account has been deactivated. Please contact your agency owner.")
            return self.form_invalid(form)

        auth_login(self.request, user)

        if self.request.POST.get("remember"):
            self.request.session.set_expiry(60 * 60 * 24)
            messages.info(self.request, "You'll stay signed in for 24 hours.")
        else:
            self.request.session.set_expiry(0)
            messages.info(self.request, "Session expires when you close the browser.")

        return redirect(self.get_success_url())

    def form_invalid(self, form):
        # Only show the generic error if we didn't already add a specific one
        if not self.request._messages:
            messages.error(self.request, "Invalid email or password.")
        return super().form_invalid(form)


class LogoutView(DefaultLogoutView):
    next_page = reverse_lazy('accounts:login')

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)
