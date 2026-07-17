import re
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
            'class': 'w-full px-4 py-3 rounded-md bg-[#FAF8F4] border border-[#E5DFD5] text-[#1C1C1A] placeholder-[#8B7355]/60 focus:outline-none focus:border-[#B87333] focus:ring-2 focus:ring-[#B87333]/15 transition',
            'placeholder': 'Aarav Realty Partners'
        })
    )
    owner_name = forms.CharField(
        max_length=255,
        label="Owner Name",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-md bg-[#FAF8F4] border border-[#E5DFD5] text-[#1C1C1A] placeholder-[#8B7355]/60 focus:outline-none focus:border-[#B87333] focus:ring-2 focus:ring-[#B87333]/15 transition',
            'placeholder': 'Priya Sharma'
        })
    )
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 rounded-md bg-[#FAF8F4] border border-[#E5DFD5] text-[#1C1C1A] placeholder-[#8B7355]/60 focus:outline-none focus:border-[#B87333] focus:ring-2 focus:ring-[#B87333]/15 transition',
            'placeholder': 'owner@agency.com'
        })
    )
    phone = forms.CharField(
        max_length=20,
        label="Phone Number",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-md bg-[#FAF8F4] border border-[#E5DFD5] text-[#1C1C1A] placeholder-[#8B7355]/60 focus:outline-none focus:border-[#B87333] focus:ring-2 focus:ring-[#B87333]/15 transition',
            'placeholder': '+91 98765 43210'
        })
    )

    class Meta:
        model = User
        fields = ("email", "username")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget = forms.HiddenInput()
        self.fields['username'].required = False
        self.fields['password1'].widget.attrs.update({
            'class': 'w-full px-4 py-3 rounded-md bg-[#FAF8F4] border border-[#E5DFD5] text-[#1C1C1A] placeholder-[#8B7355]/60 focus:outline-none focus:border-[#B87333] focus:ring-2 focus:ring-[#B87333]/15 transition',
            'placeholder': 'Create a secure password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'w-full px-4 py-3 rounded-md bg-[#FAF8F4] border border-[#E5DFD5] text-[#1C1C1A] placeholder-[#8B7355]/60 focus:outline-none focus:border-[#B87333] focus:ring-2 focus:ring-[#B87333]/15 transition',
            'placeholder': 'Repeat your password'
        })
        self.fields['password1'].label = "Password"
        self.fields['password2'].label = "Confirm Password"

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email address already exists.")
        if User.objects.filter(username=email).exists():
            raise ValidationError("A user with this email address already exists.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        phone_digits = re.sub(r'[\s\-\(\)\+]', '', phone)
        if not phone_digits.isdigit() or len(phone_digits) < 10 or len(phone_digits) > 15:
            raise ValidationError("Enter a valid phone number (10-15 digits).")
        return phone

    def clean_owner_name(self):
        name = self.cleaned_data.get('owner_name', '').strip()
        if len(name) < 2:
            raise ValidationError("Name must be at least 2 characters.")
        if not re.match(r'^[a-zA-Z\s]+$', name):
            raise ValidationError("Name can only contain letters and spaces.")
        return name

    def clean_agency_name(self):
        name = self.cleaned_data.get('agency_name', '').strip()
        if len(name) < 2:
            raise ValidationError("Agency name must be at least 2 characters.")
        return name

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['username'] = cleaned_data.get('email', '').lower().strip()
        return cleaned_data
