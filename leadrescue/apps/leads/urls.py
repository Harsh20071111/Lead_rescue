from django.urls import path
from . import views

app_name = "leads"

urlpatterns = [
    path("leads/", views.LeadListView.as_view(), name="list"),
    path("leads/create/", views.LeadCreateView.as_view(), name="create"),
    path("leads/<int:pk>/", views.LeadDetailView.as_view(), name="detail"),
    path("leads/<int:pk>/edit/", views.LeadUpdateView.as_view(), name="edit"),
    path("leads/<int:pk>/delete/", views.LeadDeleteView.as_view(), name="delete"),
    path("leads/<int:pk>/assign/", views.LeadAssignView.as_view(), name="assign"),
    path("leads/<int:pk>/activities/add/", views.add_activity, name="add_activity"),
    path("leads/<int:pk>/tasks/add/", views.add_task, name="add_task"),
    path("tasks/", views.TaskListView.as_view(), name="tasks"),
    path("tasks/<int:pk>/complete/", views.complete_task, name="complete_task"),
    path("leads/<int:lead_pk>/link/<int:property_pk>/", views.link_property, name="link_property"),
]
