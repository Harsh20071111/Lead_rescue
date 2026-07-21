from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.HomePageView.as_view(), name="home"),
    path("contact/", views.ContactPageView.as_view(), name="contact"),
    path("health/", views.health_check, name="health_check"),
]
