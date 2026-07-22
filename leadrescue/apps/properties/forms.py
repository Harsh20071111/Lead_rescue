import logging
import os
from PIL import Image, UnidentifiedImageError
from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from cloudinary import uploader

from apps.properties.models import Property, PropertyImage

logger = logging.getLogger(__name__)


class PropertyForm(forms.ModelForm):
    amenities_text = forms.CharField(
        required=False,
        label="Amenities",
        help_text="Comma-separated amenities, for example: Gym, Parking",
    )
    uploaded_images = forms.CharField(required=False, widget=forms.HiddenInput)
    uploaded_brochure = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Property
        fields = [
            "title",
            "project_name",
            "builder",
            "description",
            "address",
            "city",
            "locality",
            "location",
            "price",
            "listing_type",
            "status",
            "bhk",
            "area_sqft",
            "assigned_agent",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, agency, agent_profile, is_owner, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.agency = agency
        self.agent_profile = agent_profile
        self.is_owner = is_owner
        self._request = request

        if is_owner:
            self.fields["assigned_agent"].queryset = agency.agents.filter(is_active=True)
        else:
            self.fields.pop("assigned_agent", None)

        if self.instance and self.instance.pk:
            self.fields["amenities_text"].initial = ", ".join(self.instance.amenities or [])

        field_style = (
            "width: 100%; padding: 10px 14px; border: 1px solid var(--line, #efe3d8); "
            "border-radius: 5px; font-size: 14px; color: var(--copy, #2f241f); "
            "background: #fff; outline: none; box-sizing: border-box;"
        )
        for field in self.fields.values():
            field.widget.attrs.setdefault("style", field_style)

    def clean_amenities_text(self):
        value = self.cleaned_data["amenities_text"]
        return [item.strip() for item in value.split(",") if item.strip()]



    def save(self, commit=True):
        property_obj = super().save(commit=False)
        property_obj.agency = self.agency
        property_obj.amenities = self.cleaned_data.get("amenities_text", [])

        if not self.is_owner:
            property_obj.assigned_agent = self.agent_profile

        brochure = self.cleaned_data.get("uploaded_brochure")
        if brochure:
            property_obj.brochure_pdf = brochure

        if commit:
            property_obj.save()

            uploaded_images = self.data.getlist("uploaded_images")
            for idx, public_id in enumerate(uploaded_images):
                if not public_id.strip():
                    continue
                is_primary = idx == 0 and not property_obj.images.exists()
                try:
                    PropertyImage.objects.create(
                        property=property_obj,
                        image=public_id,
                        is_primary=is_primary,
                    )
                except Exception as e:
                    logger.exception("Failed to save image record %s for property %d: %s", public_id, property_obj.pk, e)

        return property_obj
