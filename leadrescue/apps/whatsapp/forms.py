from django import forms

from apps.whatsapp.services.client import WhatsAppClientError, validate_phone_number_token


class WhatsAppSettingsForm(forms.Form):
    phone_number_id = forms.CharField(max_length=64, required=False)
    business_account_id = forms.CharField(max_length=64, required=False)
    access_token = forms.CharField(
        widget=forms.PasswordInput(render_value=True), required=False
    )
    display_name = forms.CharField(max_length=255, required=False)
    budget_brackets = forms.CharField(
        max_length=500, required=False,
        help_text="Comma-separated budget brackets, e.g.: Under 50L, 50L–1Cr, 1Cr–2Cr, 2Cr+",
        label="Budget brackets",
    )

    def __init__(self, *args, agency, **kwargs):
        super().__init__(*args, **kwargs)
        self.agency = agency
        for field in self.fields.values():
            field.widget.attrs.setdefault(
                "class",
                "w-full rounded-md border border-[#D8CBB8] bg-white px-3 py-2 text-sm text-[#1C1C1A] focus:border-[#B87333] focus:outline-none",
            )

    def clean_budget_brackets(self):
        value = self.cleaned_data["budget_brackets"]
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned

        phone_number_id = cleaned.get("phone_number_id", "").strip()
        access_token = cleaned.get("access_token", "").strip()

        # Only validate WhatsApp creds if they were provided (disconnect scenario)
        if phone_number_id and access_token:
            try:
                details = validate_phone_number_token(phone_number_id, access_token)
            except WhatsAppClientError as exc:
                raise forms.ValidationError(
                    "Meta rejected these WhatsApp credentials. Check the phone number ID and access token."
                ) from exc
            cleaned["meta_details"] = details
        return cleaned
