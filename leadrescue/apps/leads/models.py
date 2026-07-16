from django.db import models
from apps.agencies.models import Agency
from apps.accounts.models import AgentProfile

class Lead(models.Model):
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='leads')
    agent = models.ForeignKey(AgentProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    source = models.CharField(max_length=100)
    
    STATUS_CHOICES = (
        ('New', 'New'),
        ('Contacted', 'Contacted'),
        ('Site Visit', 'Site Visit'),
        ('Negotiation', 'Negotiation'),
        ('Closed Won', 'Closed Won'),
        ('Closed Lost', 'Closed Lost'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='New')
    
    budget = models.CharField(max_length=100, blank=True)
    bhk_preference = models.CharField(max_length=50, blank=True)
    area_preference = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_contacted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.phone}"
