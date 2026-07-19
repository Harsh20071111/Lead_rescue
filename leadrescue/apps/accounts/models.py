from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid
from datetime import timedelta
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


def default_invite_expiry():
    return timezone.now() + timedelta(days=7)


class AgentInvite(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        EXPIRED = "EXPIRED", "Expired"

    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="invites")
    email = models.EmailField()
    invited_by = models.ForeignKey(AgentProfile, on_delete=models.CASCADE, related_name="sent_invites")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_invite_expiry)

    def __str__(self):
        return f"Invite to {self.email} from {self.agency.name}"
