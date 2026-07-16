from django.contrib import admin
from .models import Agency

@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner_phone', 'owner_email', 'subscription_status', 'created_at')
    search_fields = ('name', 'owner_email')
    list_filter = ('subscription_status',)
