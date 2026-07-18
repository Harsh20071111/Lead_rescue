from django.contrib import admin
from .models import Lead, Activity, Task


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "name", "phone", "email", "agency", "assigned_agent",
        "source", "status", "preferred_bhk", "budget_min", "budget_max",
        "linked_property", "created_at",
    )
    search_fields = ("name", "phone", "email", "preferred_location")
    list_filter = ("status", "source", "preferred_bhk", "agency")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = (
        "activity_type", "agent", "lead", "property",
        "agency", "created_at",
    )
    search_fields = ("content",)
    list_filter = ("activity_type", "agency")
    readonly_fields = ("created_at",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "lead", "assigned_agent", "due_date", "is_completed", "note",
    )
    search_fields = ("note", "lead__name")
    list_filter = ("is_completed", "assigned_agent")
