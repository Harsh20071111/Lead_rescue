from django.db import models
from apps.agencies.models import Agency

class Property(models.Model):
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='properties')
    title = models.CharField(max_length=255)
    bhk = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    location = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('sold', 'Sold'),
        ('on_hold', 'On Hold'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    image = models.ImageField(upload_to='property_images/', blank=True, null=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title
