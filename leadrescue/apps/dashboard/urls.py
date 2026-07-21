from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardHomeView.as_view(), name="home"),
    path("hot-leads/", views.HotLeadsWidgetView.as_view(), name="hot_leads_widget"),
    path("analytics/", views.AdvancedAnalyticsView.as_view(), name="advanced_analytics"),
]
