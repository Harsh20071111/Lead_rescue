from django.db import models

from apps.agencies.models import Agency
from apps.leads.models import Lead


class WhatsAppConversation(models.Model):
    class State(models.TextChoices):
        START = "start", "Start"
        AWAITING_PURPOSE = "awaiting_purpose", "Awaiting purpose"
        AWAITING_BHK = "awaiting_bhk", "Awaiting BHK"
        AWAITING_BUDGET = "awaiting_budget", "Awaiting budget"
        AWAITING_LOCALITY = "awaiting_locality", "Awaiting locality"
        COMPLETED = "completed", "Completed"
        HANDED_OFF = "handed_off", "Handed off"

    agency = models.ForeignKey(
        Agency, on_delete=models.CASCADE, related_name="whatsapp_conversations",
        db_index=True,
    )
    customer_phone = models.CharField(max_length=32, db_index=True)
    lead = models.ForeignKey(
        Lead, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="whatsapp_conversations",
    )
    state = models.CharField(
        max_length=32, choices=State.choices, default=State.START
    )

    purpose = models.CharField(max_length=32, blank=True, default="")
    bhk = models.CharField(max_length=20, blank=True, default="")
    budget_bracket = models.CharField(max_length=64, blank=True, default="")
    locality = models.CharField(max_length=255, blank=True, default="")

    collected_data = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["agency", "customer_phone", "is_active"],
                name="wa_conv_route_idx",
            ),
        ]

    def __str__(self):
        return f"{self.agency} - {self.customer_phone} ({self.state})"


class WhatsAppMessage(models.Model):
    class Direction(models.TextChoices):
        INBOUND = "inbound", "Inbound"
        OUTBOUND = "outbound", "Outbound"

    conversation = models.ForeignKey(
        WhatsAppConversation, on_delete=models.CASCADE, related_name="messages"
    )
    direction = models.CharField(max_length=12, choices=Direction.choices)
    message_id = models.CharField(max_length=255, unique=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.direction}: {self.message_id}"
