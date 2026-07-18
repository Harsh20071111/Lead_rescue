from django.urls import path

from . import views

app_name = "whatsapp"

urlpatterns = [
    path("settings/whatsapp/", views.WhatsAppSettingsView.as_view(), name="settings"),
    path("settings/whatsapp/disconnect/", views.disconnect_whatsapp, name="disconnect"),
    path("webhooks/whatsapp/", views.webhook, name="webhook"),
]
