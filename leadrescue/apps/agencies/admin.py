from django.contrib import admin
from .models import Agency


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "plan_tier", "owner_email", "city", "created_at")
    search_fields = ("name", "owner_email", "slug")
    list_filter = ("plan_tier",)
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at",)
