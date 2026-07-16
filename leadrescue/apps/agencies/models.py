from django.db import models

class Agency(models.Model):
    name = models.CharField(max_length=255)
    owner_phone = models.CharField(max_length=20)
    owner_email = models.EmailField()
    city = models.CharField(max_length=100)
    
    SUBSCRIPTION_CHOICES = (
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('expired', 'Expired'),
    )
    subscription_status = models.CharField(max_length=20, choices=SUBSCRIPTION_CHOICES, default='trial')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
