from django.db import models
from apps.agencies.models import Agency
from apps.accounts.models import AgentProfile


class UpgradeRequest(models.Model):
    class PlanChoice(models.TextChoices):
        STARTER = "starter", "Starter"
        GROWTH = "growth", "Growth"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        LINK_SENT = "LINK_SENT", "Link Sent"
        PAID = "PAID", "Paid"
        ACTIVATED = "ACTIVATED", "Activated"
        CANCELLED = "CANCELLED", "Cancelled"

    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="upgrade_requests")
    requested_by = models.ForeignKey(AgentProfile, on_delete=models.SET_NULL, null=True, blank=True)
    requested_plan = models.CharField(max_length=20, choices=PlanChoice.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    razorpay_payment_link_id = models.CharField(max_length=255, null=True, blank=True)
    razorpay_payment_link_url = models.URLField(max_length=1024, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Upgrade {self.agency.name} → {self.requested_plan} ({self.status})"
