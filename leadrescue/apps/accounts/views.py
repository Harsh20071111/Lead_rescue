from django.contrib.auth import login, get_user_model
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from django.contrib.auth.views import LoginView as DefaultLoginView, LogoutView as DefaultLogoutView

from apps.agencies.models import Agency
from apps.accounts.models import AgentProfile
from .forms import SignupForm

User = get_user_model()

class SignupView(FormView):
    template_name = 'registration/signup.html'
    form_class = SignupForm
    success_url = reverse_lazy('dashboard:home')

    def form_valid(self, form):
        data = form.cleaned_data

        # Use transaction to ensure either all succeed or none do
        with transaction.atomic():
            # 1. Create Django User (UserCreationForm handles password hashing)
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

            # 2. Create Agency
            agency = Agency.objects.create(
                name=data['agency_name'],
                owner_phone=data['phone'],
                owner_email=data['email'],
                city='Not Specified'
            )

            # 3. Create AgentProfile as owner
            AgentProfile.objects.create(
                user=user,
                agency=agency,
                role='owner',
                phone=data['phone']
            )

        # 4. Login User
        login(self.request, user)

        return redirect(self.success_url)

class LoginView(DefaultLoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

class LogoutView(DefaultLogoutView):
    next_page = reverse_lazy('accounts:login')
