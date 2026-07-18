from django import forms
from django.utils import timezone

from apps.leads.models import Activity, Lead, Task
from apps.properties.models import Property


class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = [
            "name",
            "phone",
            "email",
            "source",
            "status",
            "budget_min",
            "budget_max",
            "preferred_location",
            "preferred_bhk",
            "linked_property",
            "assigned_agent",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, agency, agent_profile, is_owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.agency = agency
        self.agent_profile = agent_profile
        self.is_owner = is_owner
        self.fields["linked_property"].queryset = self._property_queryset()
        self.fields["assigned_agent"].queryset = agency.agents.filter(is_active=True)

        if not is_owner:
            self.fields.pop("assigned_agent")

        for field in self.fields.values():
            field.widget.attrs.setdefault(
                "class",
                "w-full rounded-md border border-[#D8CBB8] bg-white px-3 py-2 text-sm text-[#1C1C1A] focus:border-[#B87333] focus:outline-none",
            )

    def _property_queryset(self):
        queryset = Property.objects.for_agency(self.agency)
        if self.is_owner:
            return queryset
        return queryset.filter(assigned_agent=self.agent_profile)

    def save(self, commit=True):
        lead = super().save(commit=False)
        lead.agency = self.agency
        if not self.is_owner:
            lead.assigned_agent = self.agent_profile
        if commit:
            lead.save()
            self.save_m2m()
        return lead


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ["activity_type", "content"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["activity_type"].initial = Activity.ActivityType.NOTE
        for field in self.fields.values():
            field.widget.attrs.setdefault(
                "class",
                "w-full rounded-md border border-[#D8CBB8] bg-white px-3 py-2 text-sm text-[#1C1C1A] focus:border-[#B87333] focus:outline-none",
            )


class LeadAssignmentForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ["assigned_agent"]

    def __init__(self, *args, agency, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_agent"].queryset = agency.agents.filter(is_active=True)
        self.fields["assigned_agent"].widget.attrs.update(
            {
                "class": "rounded-md border border-[#D8CBB8] bg-white px-3 py-2 text-sm",
                "onchange": "this.form.requestSubmit()",
            }
        )


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["due_date", "note", "assigned_agent"]
        widgets = {
            "due_date": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, agency, agent_profile, is_owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.agency = agency
        self.agent_profile = agent_profile
        self.is_owner = is_owner
        self.fields["assigned_agent"].queryset = agency.agents.filter(is_active=True)
        self.fields["due_date"].initial = timezone.localtime().strftime("%Y-%m-%dT%H:%M")
        if not is_owner:
            self.fields.pop("assigned_agent")

        for field in self.fields.values():
            field.widget.attrs.setdefault(
                "class",
                "w-full rounded-md border border-[#D8CBB8] bg-white px-3 py-2 text-sm text-[#1C1C1A] focus:border-[#B87333] focus:outline-none",
            )

    def save(self, commit=True):
        task = super().save(commit=False)
        if not self.is_owner:
            task.assigned_agent = self.agent_profile
        if commit:
            task.save()
        return task
