from django.db import models
from django.core.validators import FileExtensionValidator
from apps.agencies.models import Agency
from apps.accounts.models import AgentProfile

from django.core.files.storage import default_storage
try:
    from cloudinary_storage.storage import RawMediaCloudinaryStorage
    import_storage = RawMediaCloudinaryStorage()
except ImportError:
    import_storage = default_storage


class ImportJob(models.Model):
    class TargetModel(models.TextChoices):
        LEAD = "lead", "Lead"
        PROPERTY = "property", "Property"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        MAPPING = "mapping", "Mapping"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="imports", db_index=True)
    initiated_by = models.ForeignKey(AgentProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="imports")
    target_model = models.CharField(max_length=20, choices=TargetModel.choices)
    file = models.FileField(
        upload_to="imports/%Y/%m/",
        storage=import_storage,
        validators=[FileExtensionValidator(allowed_extensions=["csv", "xls", "xlsx"])]
    )
    # Stores the Cloudinary/public URL so Celery can download it later
    file_url = models.URLField(max_length=500, blank=True, default="")
    # Cached headers from upload time (avoids re-reading from Cloudinary)
    cached_headers = models.JSONField(default=list, blank=True)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Stores how CSV columns map to our model fields
    column_mapping = models.JSONField(default=dict, blank=True)
    
    # Progress tracking
    total_rows = models.PositiveIntegerField(default=0)
    processed_rows = models.PositiveIntegerField(default=0)
    successful_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)
    
    # Detailed error logs per row
    error_log = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Import {self.get_target_model_display()} ({self.id}) - {self.get_status_display()}"
