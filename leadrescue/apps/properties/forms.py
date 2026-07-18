import os
from PIL import Image, UnidentifiedImageError
from django import forms
from django.core.exceptions import ValidationError

from apps.properties.models import Property, PropertyImage


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={
            "multiple": True,
            "accept": ".jpg,.jpeg,.png"
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
        help_text="Select up to 10 images (max 5MB each, JPG/PNG only).",
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
            "image",
            "images",
            "assigned_agent",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, agency, agent_profile, is_owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.agency = agency
        self.agent_profile = agent_profile
        self.is_owner = is_owner
        self.fields["assigned_agent"].queryset = agency.agents.filter(is_active=True)
        if self.instance and self.instance.pk:
            self.fields["amenities_text"].initial = ", ".join(self.instance.amenities or [])

        if not is_owner:
            self.fields.pop("assigned_agent")

        for field in self.fields.values():
            field.widget.attrs.setdefault(
                "class",
                "w-full rounded-md border border-[#D8CBB8] bg-white px-3 py-2 text-sm text-[#1C1C1A] focus:border-[#B87333] focus:outline-none",
            )

    def clean_amenities_text(self):
        value = self.cleaned_data["amenities_text"]
        return [item.strip() for item in value.split(",") if item.strip()]

    def clean_images(self):
        files = self.cleaned_data.get('images')
        
        if not files:
            return []

        # If only one file was uploaded, MultipleFileField might return a single file instead of a list
        if not isinstance(files, (list, tuple)):
            files = [files]

        if len(files) > 10:
            raise ValidationError("You can upload a maximum of 10 images at once.")

        valid_extensions = ['.jpg', '.jpeg', '.png']
        max_size = 5 * 1024 * 1024  # 5MB

        for f in files:
            ext = os.path.splitext(f.name)[1].lower()
            if ext not in valid_extensions:
                raise ValidationError(f"Invalid file type '{ext}' for {f.name}. Only JPG and PNG are allowed.")
            if f.size > max_size:
                raise ValidationError(f"File {f.name} exceeds the 5MB size limit.")
            
            # Prevent malicious payloads by verifying it's a structural image
            try:
                f.seek(0)
                img = Image.open(f)
                img.verify()  # Does not decode image fully, only verifies structure/headers
                f.seek(0)     # Reset file pointer for Cloudinary upload
            except (IOError, SyntaxError, UnidentifiedImageError):
                raise ValidationError(f"File {f.name} is corrupted or contains a malicious payload.")
        
        return files

    def save(self, commit=True):
        property_obj = super().save(commit=False)
        property_obj.agency = self.agency
        property_obj.amenities = self.cleaned_data["amenities_text"]
        if not self.is_owner:
            property_obj.assigned_agent = self.agent_profile
        if commit:
            property_obj.save()
            self.save_m2m()
            
            # Save newly uploaded images
            uploaded_images = self.cleaned_data.get("images")
            if uploaded_images:
                for idx, img in enumerate(uploaded_images):
                    is_primary = False
                    # If this is the first image ever for this property, make it primary
                    if idx == 0 and not property_obj.images.exists():
                        is_primary = True
                    PropertyImage.objects.create(
                        property=property_obj,
                        image=img,
                        is_primary=is_primary
                    )
                    
        return property_obj
