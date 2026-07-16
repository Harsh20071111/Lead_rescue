"""
Agency model for LeadRescue.

Each agency represents a real estate company/brokerage
that uses the platform.
"""

from django.db import models
from django.utils.text import slugify

from apps.common.models import TimeStampedModel


class Agency(TimeStampedModel):
    """Real estate agency or brokerage."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Agencies"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
