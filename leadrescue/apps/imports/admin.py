from django.contrib import admin
from .models import ImportJob

@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = ("id", "agency", "target_model", "status", "processed_rows", "total_rows", "created_at")
    list_filter = ("status", "target_model", "agency")
    search_fields = ("agency__name", "initiated_by__user__email")
    readonly_fields = ("created_at", "updated_at", "total_rows", "processed_rows", "successful_rows", "failed_rows", "error_log")
