from django.contrib import admin

from .models import Agency


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "email")
    prepopulated_fields = {"slug": ("name",)}
