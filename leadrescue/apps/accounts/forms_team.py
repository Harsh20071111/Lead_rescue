from django import forms
from django.contrib.auth import get_user_model
from apps.accounts.models import AgentInvite

User = get_user_model()


class AgentInviteForm(forms.ModelForm):
    class Meta:
        model = AgentInvite
        fields = ["email"]
        widgets = {
            "email": forms.EmailInput(attrs={"class": "rounded-md border border-[#D8CBB8] px-3 py-2 text-sm w-full", "placeholder": "agent@example.com"}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        if AgentInvite.objects.filter(email=email, status=AgentInvite.Status.PENDING).exists():
            raise forms.ValidationError("A pending invite has already been sent to this email.")
        return email


class InviteSignupForm(forms.Form):
    first_name = forms.CharField(
        max_length=150, 
        required=True,
        widget=forms.TextInput(attrs={"class": "rounded-md border border-[#D8CBB8] px-3 py-2 text-sm w-full"})
    )
    last_name = forms.CharField(
        max_length=150, 
        required=False,
        widget=forms.TextInput(attrs={"class": "rounded-md border border-[#D8CBB8] px-3 py-2 text-sm w-full"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "rounded-md border border-[#D8CBB8] px-3 py-2 text-sm w-full"}),
        required=True
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "rounded-md border border-[#D8CBB8] px-3 py-2 text-sm w-full"}),
        required=True
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", "Passwords do not match.")

        return cleaned_data
