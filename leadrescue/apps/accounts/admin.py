from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "agency",
        "is_active",
    )
    list_filter = ("role", "is_active", "agency")
    search_fields = ("username", "email", "first_name", "last_name")

    # Add role and agency to the edit form
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "LeadRescue",
            {
                "fields": ("role", "phone", "agency"),
            },
        ),
    )

    # Add role and agency to the create form
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "LeadRescue",
            {
                "fields": ("role", "phone", "agency"),
            },
        ),
    )
