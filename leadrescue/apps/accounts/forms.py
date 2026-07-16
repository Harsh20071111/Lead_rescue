from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

User = get_user_model()


class SignupForm(UserCreationForm):
    agency_name = forms.CharField(
        max_length=255,
        label="Agency Name",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-md bg-[#F5F2EC] border border-[#E5DFD5] text-[#1C1C1A] focus:outline-none focus:border-[#B87333]'
        })
    )
    owner_name = forms.CharField(
        max_length=255,
        label="Owner Name",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-md bg-[#F5F2EC] border border-[#E5DFD5] text-[#1C1C1A] focus:outline-none focus:border-[#B87333]'
        })
    )
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 rounded-md bg-[#F5F2EC] border border-[#E5DFD5] text-[#1C1C1A] focus:outline-none focus:border-[#B87333]'
        })
    )
    phone = forms.CharField(
        max_length=20,
        label="Phone Number",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-md bg-[#F5F2EC] border border-[#E5DFD5] text-[#1C1C1A] focus:outline-none focus:border-[#B87333]'
        })
    )

    class Meta:
        model = User
        fields = ("email", "username")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use email as username — hide the separate username field
        self.fields['username'].widget = forms.HiddenInput()
        self.fields['username'].required = False
        # Style password fields to match the rest
        self.fields['password1'].widget.attrs.update({
            'class': 'w-full px-4 py-3 rounded-md bg-[#F5F2EC] border border-[#E5DFD5] text-[#1C1C1A] focus:outline-none focus:border-[#B87333]'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'w-full px-4 py-3 rounded-md bg-[#F5F2EC] border border-[#E5DFD5] text-[#1C1C1A] focus:outline-none focus:border-[#B87333]'
        })
        self.fields['password1'].label = "Password"
        self.fields['password2'].label = "Confirm Password"

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        # Set username = email so Django's AbstractUser is happy
        cleaned_data['username'] = cleaned_data.get('email', '').lower()
        return cleaned_data
