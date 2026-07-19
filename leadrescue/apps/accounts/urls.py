from django.urls import path
from . import views, views_team

app_name = "accounts"

urlpatterns = [
    path("signup/", views.SignupView.as_view(), name="signup"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    
    # Team Management
    path("team/", views_team.TeamListView.as_view(), name="team_list"),
    path("team/invite/", views_team.AgentInviteView.as_view(), name="team_invite"),
    path("team/<int:pk>/deactivate/", views_team.AgentDeactivateView.as_view(), name="team_deactivate"),
    path("team/<int:pk>/reactivate/", views_team.AgentReactivateView.as_view(), name="team_reactivate"),
    path("team/invite/<int:pk>/delete/", views_team.AgentInviteDeleteView.as_view(), name="team_invite_delete"),
    path("invites/accept/<uuid:token>/", views_team.InviteAcceptView.as_view(), name="invite_accept"),
]
