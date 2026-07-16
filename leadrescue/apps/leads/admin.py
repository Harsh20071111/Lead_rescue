from django.contrib import admin
from .models import Lead

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'agency', 'agent', 'status', 'created_at')
    search_fields = ('name', 'phone')
    list_filter = ('status', 'agency', 'source')
