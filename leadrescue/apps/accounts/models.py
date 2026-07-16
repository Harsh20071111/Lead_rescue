from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.agencies.models import Agency

class User(AbstractUser):
    pass

class AgentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='agent_profile')
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='agents')
    
    ROLE_CHOICES = (
        ('owner', 'Owner'),
        ('agent', 'Agent'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='agent')
    phone = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
