from django.urls import path

from .views import (
    charter_view,
    conversation_view,
    delete_account_view,
    edit_profile_view,
    export_data_view,
    follow_view,
    home_view,
    inbox_view,
    login_view,
    logout_view,
    moderation_action_view,
    moderation_log_view,
    moderation_view,
    post_action_view,
    post_detail_view,
    profile_view,
    register_view,
    start_conversation_view,
    survey_view,
    trust_view,
    trusted_feed_view,
)

app_name = "accounts"

urlpatterns = [
    path("", home_view, name="home"),
    path("posts/<int:post_id>/", post_detail_view, name="post_detail"),
    path("posts/<int:post_id>/<str:action>/", post_action_view, name="post_action"),
    path("inscription/", register_view, name="register"),
    path("connexion/", login_view, name="login"),
    path("deconnexion/", logout_view, name="logout"),
    # Profils
    path("profil/modifier/", edit_profile_view, name="edit_profile"),
    path("profil/<str:pseudo>/", profile_view, name="profile"),
    path("profil/<str:pseudo>/suivre/", follow_view, name="follow"),
    # Modération (staff only)
    path("moderation/", moderation_view, name="moderation"),
    path("moderation/journal/", moderation_log_view, name="moderation_log"),
    path("moderation/<int:post_id>/<str:action>/", moderation_action_view, name="moderation_action"),
    # Messagerie
    path("messages/", inbox_view, name="inbox"),
    path("messages/<int:pk>/", conversation_view, name="conversation"),
    path("messages/nouveau/<str:pseudo>/", start_conversation_view, name="start_conversation"),
    # Gouvernance Sprint 3
    path("charte/", charter_view, name="charter"),
    path("profil/<str:pseudo>/confiance/", trust_view, name="trust"),
    path("fil-confiance/", trusted_feed_view, name="trusted_feed"),
    path("enquete/", survey_view, name="survey"),
    path("mes-donnees/", export_data_view, name="export_data"),
    path("supprimer-mon-compte/", delete_account_view, name="delete_account"),
]
