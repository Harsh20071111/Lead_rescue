"""
Shared base models and managers for LeadRescue.

All app models should inherit from TimeStampedModel to get
consistent created_at / updated_at timestamps.
"""

from django.db import models


class ActiveManager(models.Manager):
    """Manager that returns only active (non-deleted) records."""

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class TimeStampedModel(models.Model):
    """
    Abstract base model providing self-updating
    created_at and updated_at fields.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]
