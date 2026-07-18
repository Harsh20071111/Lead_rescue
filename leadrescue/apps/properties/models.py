from django.db import models
from apps.agencies.models import Agency
from apps.accounts.models import AgentProfile
from apps.core.choices import BHKChoices
from apps.core.managers import AgencyScopedManager


class Property(models.Model):
    class ListingType(models.TextChoices):
        SALE = "sale", "Sale"
        RENT = "rent", "Rent"

    class PropertyStatus(models.TextChoices):
        AVAILABLE = "available", "Available"
        PENDING = "pending", "Pending"
        SOLD = "sold", "Sold"
        RENTED = "rented", "Rented"

    agency = models.ForeignKey(
        Agency, on_delete=models.CASCADE, related_name="properties",
        db_index=True,
    )
    assigned_agent = models.ForeignKey(
        AgentProfile, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="properties",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255, default="")
    city = models.CharField(max_length=100, db_index=True)
    locality = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    listing_type = models.CharField(
        max_length=10,
        choices=ListingType.choices,
        default=ListingType.SALE,
    )
    status = models.CharField(
        max_length=20,
        choices=PropertyStatus.choices,
        default=PropertyStatus.AVAILABLE,
    )

    project_name = models.CharField(max_length=255, blank=True)
    builder = models.CharField(max_length=255, blank=True)
    area_sqft = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    amenities = models.JSONField(default=list, blank=True)

    # Preserved from original model
    bhk = models.CharField(
        max_length=20, choices=BHKChoices.choices, null=True, blank=True
    )
    location = models.CharField(max_length=255, blank=True)
    image = models.ImageField(
        upload_to="property_images/", blank=True, null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Multi-tenant manager
    objects = AgencyScopedManager()

    class Meta:
        verbose_name_plural = "properties"

    def __str__(self):
        return self.title
