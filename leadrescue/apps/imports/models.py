from django.db import models
from django.core.validators import FileExtensionValidator
from django.conf import settings
from django.core.files.storage import FileSystemStorage, Storage
from apps.agencies.models import Agency
from apps.accounts.models import AgentProfile

try:
    from cloudinary_storage.storage import RawMediaCloudinaryStorage
except ImportError:
    RawMediaCloudinaryStorage = None


class ImportFileStorage(Storage):
    def __init__(self):
        self._storage = None

    def deconstruct(self):
        return ("apps.imports.models.ImportFileStorage", [], {})

    @property
    def storage(self):
        if self._storage is None:
            if getattr(settings, "USE_CLOUDINARY_IMPORT_STORAGE", False) and RawMediaCloudinaryStorage is not None:
                self._storage = RawMediaCloudinaryStorage()
            else:
                self._storage = FileSystemStorage(location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL)
        return self._storage

    def _open(self, name, mode="rb"):
        return self.storage.open(name, mode)

    def _save(self, name, content):
        return self.storage.save(name, content)

    def delete(self, name):
        return self.storage.delete(name)

    def exists(self, name):
        return self.storage.exists(name)

    def listdir(self, path):
        return self.storage.listdir(path)

    def size(self, name):
        return self.storage.size(name)

    def url(self, name):
        return self.storage.url(name)

    def get_accessed_time(self, name):
        return self.storage.get_accessed_time(name)

    def get_created_time(self, name):
        return self.storage.get_created_time(name)

    def get_modified_time(self, name):
        return self.storage.get_modified_time(name)


import_storage = ImportFileStorage()


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
        CANCELED = "canceled", "Canceled"

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
