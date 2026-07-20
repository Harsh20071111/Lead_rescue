import logging
import os
from PIL import Image, UnidentifiedImageError
from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from cloudinary import uploader

from apps.properties.models import Property, PropertyImage

logger = logging.getLogger(__name__)


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        value = files.get(name)
        if value:
            return [value]
        return []


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={
            "multiple": True,
            "accept": ".jpg,.jpeg,.png,.webp"
        }))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class PropertyForm(forms.ModelForm):
    amenities_text = forms.CharField(
        required=False,
        label="Amenities",
        help_text="Comma-separated amenities, for example: Gym, Parking",
    )
    images = MultipleFileField(
        required=False,
        label="Property Images",
        help_text="Select up to 10 images (max 5MB each, JPG/PNG/WebP only).",
    )
    brochure_file = forms.FileField(
        required=False,
        label="Brochure PDF",
        help_text="Upload a brochure PDF for WhatsApp bot delivery.",
    )

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

    def clean_images(self):
        files = self.cleaned_data.get("images")

        if not files:
            return []

        if not isinstance(files, (list, tuple)):
            files = [files]

        if len(files) > 10:
            raise ValidationError("You can upload a maximum of 10 images at once.")

        valid_extensions = [".jpg", ".jpeg", ".png", ".webp"]
        max_size = 5 * 1024 * 1024

        validated = []
        for f in files:
            ext = os.path.splitext(f.name)[1].lower()
            if ext not in valid_extensions:
                raise ValidationError(
                    f"Invalid file type '{ext}' for {f.name}. Only JPG, PNG, and WebP are allowed."
                )
            if f.size > max_size:
                raise ValidationError(f"File {f.name} exceeds the 5MB size limit.")

            try:
                f.seek(0)
                img = Image.open(f)
                img.verify()
                f.seek(0)
            except (IOError, SyntaxError, UnidentifiedImageError):
                raise ValidationError(
                    f"File {f.name} is corrupted or not a valid image."
                )

            validated.append(f)

        return validated

    def save(self, commit=True):
        property_obj = super().save(commit=False)
        property_obj.agency = self.agency
        property_obj.amenities = self.cleaned_data.get("amenities_text", [])

        if not self.is_owner:
            property_obj.assigned_agent = self.agent_profile

        brochure = self.cleaned_data.get("brochure_file")
        if brochure:
            brochure.seek(0)
            result = uploader.upload(
                brochure,
                resource_type="raw",
                folder="brochures",
                timeout=60,
            )
            property_obj.brochure_pdf = result.get("public_id")

        if commit:
            property_obj.save()

            uploaded_images = self.cleaned_data.get("images", [])
            failed_count = 0
            for idx, img in enumerate(uploaded_images):
                try:
                    is_primary = idx == 0 and not property_obj.images.exists()
                    img.seek(0)
                    result = uploader.upload(
                        img,
                        resource_type="image",
                        folder="property_images",
                        timeout=60,
                    )
                    PropertyImage.objects.create(
                        property=property_obj,
                        image=result.get("public_id"),
                        is_primary=is_primary,
                    )
                except Exception as e:
                    logger.exception("Failed to upload image %d for property %d: %s", idx, property_obj.pk, e)
                    failed_count += 1

            if failed_count and self._request:
                total = len(uploaded_images)
                messages.warning(
                    self._request,
                    f"{failed_count} of {total} image(s) failed to upload. The property was created.",
                )

        return property_obj
