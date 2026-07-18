from django.core.exceptions import ValidationError
from django.db import models
from apps.agencies.models import Agency
from apps.accounts.models import AgentProfile
from apps.core.choices import BHKChoices
from apps.core.managers import AgencyScopedManager


class Lead(models.Model):
    class LeadSource(models.TextChoices):
        WEBSITE = "website", "Website"
        REFERRAL = "referral", "Referral"
        GOOGLE = "google", "Google"
        MANUAL = "manual", "Manual"
        WHATSAPP = "whatsapp", "WhatsApp"

    class LeadStatus(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        QUALIFIED = "qualified", "Qualified"
        SITE_VISIT = "site_visit", "Site Visit"
        NEGOTIATION = "negotiation", "Negotiation"
        CONVERTED = "converted", "Converted"
        LOST = "lost", "Lost"

    agency = models.ForeignKey(
        Agency, on_delete=models.CASCADE, related_name="leads",
        db_index=True,
    )
    assigned_agent = models.ForeignKey(
        AgentProfile, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="leads",
    )
    linked_property = models.ForeignKey(
        "properties.Property", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="leads",
    )
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    source = models.CharField(
        max_length=20,
        choices=LeadSource.choices,
        default=LeadSource.MANUAL,
    )
    status = models.CharField(
        max_length=20,
        choices=LeadStatus.choices,
        default=LeadStatus.NEW,
    )

    # Preserved from original model
    budget = models.CharField(max_length=100, blank=True)
    bhk_preference = models.CharField(max_length=50, blank=True)
    area_preference = models.CharField(max_length=255, blank=True)
    budget_min = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    budget_max = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    preferred_location = models.CharField(max_length=255, blank=True)
    preferred_bhk = models.CharField(
        max_length=20, choices=BHKChoices.choices, null=True, blank=True
    )
    notes = models.TextField(blank=True)
    last_contacted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Multi-tenant manager
    objects = AgencyScopedManager()

    class Meta:
        indexes = [
            models.Index(fields=["agency", "status"], name="lead_agency_status_idx"),
        ]

    def __str__(self):
        return f"{self.name} - {self.phone}"


class Activity(models.Model):
    class ActivityType(models.TextChoices):
        CALL = "call", "Call"
        EMAIL = "email", "Email"
        NOTE = "note", "Note"
        WHATSAPP = "whatsapp", "WhatsApp"
        STATUS_CHANGE = "status_change", "Status Change"

    agency = models.ForeignKey(
        Agency, on_delete=models.CASCADE, related_name="activities",
        db_index=True,
    )
    lead = models.ForeignKey(
        Lead, on_delete=models.CASCADE, null=True, blank=True,
        related_name="activities",
    )
    property = models.ForeignKey(
        "properties.Property", on_delete=models.CASCADE,
        null=True, blank=True, related_name="activities",
    )
    agent = models.ForeignKey(
        AgentProfile, on_delete=models.CASCADE, related_name="activities",
    )
    activity_type = models.CharField(
        max_length=20, choices=ActivityType.choices,
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # Multi-tenant manager
    objects = AgencyScopedManager()

    class Meta:
        verbose_name_plural = "activities"

    def clean(self):
        super().clean()
        if self.lead is None and self.property is None:
            raise ValidationError(
                "An activity must be linked to at least one of: lead, property."
            )

    def save(self, *args, **kwargs):
        # Auto-populate agency from lead or property
        if not self.agency_id:
            if self.lead_id:
                self.agency_id = self.lead.agency_id
            elif self.property_id:
                self.agency_id = self.property.agency_id
        super().save(*args, **kwargs)

    def __str__(self):
        target = self.lead or self.property
        return f"{self.get_activity_type_display()} — {target}"


class Task(models.Model):
    lead = models.ForeignKey(
        Lead, on_delete=models.CASCADE, related_name="tasks",
    )
    assigned_agent = models.ForeignKey(
        AgentProfile, on_delete=models.CASCADE, related_name="tasks",
    )
    due_date = models.DateTimeField()
    is_completed = models.BooleanField(default=False)
    note = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Task for {self.lead.name} — {'Done' if self.is_completed else 'Pending'}"
