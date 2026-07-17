from django.contrib.auth import login, get_user_model
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

            AgentProfile.objects.create(
                user=user,
                agency=agency,
                role='owner',
                phone=data['phone']
            )

        messages.success(self.request, "Account created. Please sign in.")
        return redirect(self.success_url)


class LoginView(DefaultLoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_invalid(self, form):
        messages.error(self.request, "Invalid email or password.")
        return super().form_invalid(form)


class LogoutView(DefaultLogoutView):
    next_page = reverse_lazy('accounts:login')

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)
