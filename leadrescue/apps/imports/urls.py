from django.urls import path
from . import views

app_name = "imports"

urlpatterns = [
    path("upload/", views.import_upload, name="import_upload"),
    path("<int:job_id>/mapping/", views.import_mapping, name="import_mapping"),
    path("<int:job_id>/progress/", views.import_progress, name="import_progress"),
]
