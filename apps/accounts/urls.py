from django.urls import path

from apps.governance.views import charter_view, survey_view, trust_view, trusted_feed_view
from apps.messaging.views import conversation_view, inbox_view, start_conversation_view
from apps.moderation.views import moderation_action_view, moderation_log_view, moderation_view
from apps.posts.views import home_view, post_action_view, post_detail_view

from .views import (
    delete_account_view,
    edit_profile_view,
    export_data_view,
    follow_view,
    login_view,
    logout_view,
    profile_view,
    register_view,
)

app_name = "accounts"

urlpatterns = [
    # Auth
    path("inscription/", register_view, name="register"),
    path("connexion/", login_view, name="login"),
    path("deconnexion/", logout_view, name="logout"),
    # Feed principal
    path("", home_view, name="home"),
    path("posts/<int:post_id>/", post_detail_view, name="post_detail"),
    path("posts/<int:post_id>/<str:action>/", post_action_view, name="post_action"),
    # Profils
    path("profil/modifier/", edit_profile_view, name="edit_profile"),
    path("profil/<str:pseudo>/", profile_view, name="profile"),
    path("profil/<str:pseudo>/suivre/", follow_view, name="follow"),
    # Compte
    path("supprimer-mon-compte/", delete_account_view, name="delete_account"),
    path("mes-donnees/", export_data_view, name="export_data"),
    # Messagerie
    path("messages/", inbox_view, name="inbox"),
    path("messages/<int:pk>/", conversation_view, name="conversation"),
    path("messages/nouveau/<str:pseudo>/", start_conversation_view, name="start_conversation"),
    # Modération (staff only)
    path("moderation/", moderation_view, name="moderation"),
    path("moderation/journal/", moderation_log_view, name="moderation_log"),
    path("moderation/<int:post_id>/<str:action>/", moderation_action_view, name="moderation_action"),
    # Gouvernance
    path("charte/", charter_view, name="charter"),
    path("profil/<str:pseudo>/confiance/", trust_view, name="trust"),
    path("fil-confiance/", trusted_feed_view, name="trusted_feed"),
    path("enquete/", survey_view, name="survey"),
]
