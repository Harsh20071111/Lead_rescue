from django.db import models
from apps.agencies.models import Agency
from apps.accounts.models import AgentProfile
from apps.core.choices import BHKChoices
from apps.core.managers import AgencyScopedManager
from cloudinary.models import CloudinaryField
import cloudinary.uploader
import logging

logger = logging.getLogger(__name__)


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

    @property
    def primary_image(self):
        # We assume prefetch_related('images') might be used, so we use Python filtering
        # to avoid N+1 queries if prefetched, otherwise we hit the DB.
        images = list(self.images.all())
        if not images:
            return None
        primary = next((img for img in images if img.is_primary), None)
        if primary:
            return primary
        # Fallback to the first one based on ordering
        return images[0]

class PropertyImage(models.Model):
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="images"
    )
    image = CloudinaryField("image")
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "uploaded_at"]

    def save(self, *args, **kwargs):
        if self.is_primary:
            # Unset primary on siblings
            PropertyImage.objects.filter(
                property=self.property, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.image:
            try:
                cloudinary.uploader.destroy(self.image.public_id)
            except Exception as e:
                logger.error(f"Failed to delete Cloudinary asset {self.image.public_id}: {e}")
        super().delete(*args, **kwargs)
