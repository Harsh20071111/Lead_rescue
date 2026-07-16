"""
Custom User model for LeadRescue.

Extends Django's AbstractUser with role-based access
and agency association for multi-tenant support.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user with role-based permissions.

    Roles:
        - Owner: Agency owner with full access.
        - Admin: Administrative staff with management access.
        - Agent: Sales agent with operational access.
    """

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        AGENT = "agent", "Agent"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.AGENT,
    )
    phone = models.CharField(max_length=15, blank=True)
    agency = models.ForeignKey(
        "agencies.Agency",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    # Role-check helpers
    @property
    def is_owner(self):
        return self.role == self.Role.OWNER

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN

    @property
    def is_agent(self):
        return self.role == self.Role.AGENT
