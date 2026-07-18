from django import forms

from apps.whatsapp.services.client import WhatsAppClientError, validate_phone_number_token


class WhatsAppSettingsForm(forms.Form):
    phone_number_id = forms.CharField(max_length=64)
    business_account_id = forms.CharField(max_length=64)
    access_token = forms.CharField(widget=forms.PasswordInput(render_value=True))
    display_name = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, agency, **kwargs):
        super().__init__(*args, **kwargs)
        self.agency = agency
        for field in self.fields.values():
            field.widget.attrs.setdefault(
                "class",
                "w-full rounded-md border border-[#D8CBB8] bg-white px-3 py-2 text-sm text-[#1C1C1A] focus:border-[#B87333] focus:outline-none",
            )

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        try:
            details = validate_phone_number_token(
                cleaned["phone_number_id"], cleaned["access_token"]
            )
        except WhatsAppClientError as exc:
            raise forms.ValidationError(
                "Meta rejected these WhatsApp credentials. Check the phone number ID and access token."
            ) from exc
        cleaned["meta_details"] = details
        return cleaned

