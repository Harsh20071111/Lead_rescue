from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.agencies.models import Agency


class User(AbstractUser):
    pass


class AgentProfile(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        AGENT = "agent", "Agent"
        ADMIN = "admin", "Admin"

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="agent_profile"
    )
    agency = models.ForeignKey(
        Agency, on_delete=models.CASCADE, related_name="agents"
    )
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.AGENT
    )
    phone = models.CharField(max_length=20)
    avatar = models.ImageField(
        upload_to="agent_avatars/", blank=True, null=True
    )
    is_active = models.BooleanField(default=True)
    welcome_email_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} ({self.get_role_display()})"
