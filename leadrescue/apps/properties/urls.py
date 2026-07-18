from django.urls import path

from . import views

app_name = "properties"

urlpatterns = [
    path("properties/", views.PropertyListView.as_view(), name="list"),
    path("properties/create/", views.PropertyCreateView.as_view(), name="create"),
    path("properties/<int:pk>/", views.PropertyDetailView.as_view(), name="detail"),
    path("properties/<int:pk>/edit/", views.PropertyUpdateView.as_view(), name="edit"),
    path("properties/<int:pk>/delete/", views.PropertyDeleteView.as_view(), name="delete"),
]
