from django.urls import path

from . import views

app_name = "properties"

urlpatterns = [
    path("properties/", views.PropertyListView.as_view(), name="list"),
    path("properties/create/", views.PropertyCreateView.as_view(), name="create"),
    path("properties/<int:pk>/", views.PropertyDetailView.as_view(), name="detail"),
    path("properties/<int:pk>/edit/", views.PropertyUpdateView.as_view(), name="edit"),
    path("properties/<int:pk>/delete/", views.PropertyDeleteView.as_view(), name="delete"),
    path("properties/<int:pk>/images/<int:image_id>/set-primary/", views.SetPrimaryImageView.as_view(), name="set_primary_image"),
    path("properties/<int:pk>/images/<int:image_id>/delete/", views.DeleteImageView.as_view(), name="delete_image"),
    path("properties/cloudinary-signature/", views.CloudinarySignatureView.as_view(), name="cloudinary_signature"),
]
