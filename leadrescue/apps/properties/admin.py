from django.contrib import admin
from .models import Property


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        "title", "agency", "assigned_agent", "price", "listing_type",
        "city", "locality", "bhk", "area_sqft", "status", "created_at",
    )
    search_fields = ("title", "project_name", "builder", "address", "city", "locality")
    list_filter = ("status", "listing_type", "bhk", "agency", "city")
    readonly_fields = ("created_at", "updated_at")
