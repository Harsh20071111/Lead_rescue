from django import forms

from apps.properties.models import Property


class PropertyForm(forms.ModelForm):
    amenities_text = forms.CharField(
        required=False,
        label="Amenities",
        help_text="Comma-separated amenities, for example: Gym, Parking",
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

    def save(self, commit=True):
        property_obj = super().save(commit=False)
        property_obj.agency = self.agency
        property_obj.amenities = self.cleaned_data["amenities_text"]
        if not self.is_owner:
            property_obj.assigned_agent = self.agent_profile
        if commit:
            property_obj.save()
            self.save_m2m()
        return property_obj
