from django.urls import path

from .views import home_view, login_view, logout_view, post_action_view, register_view

app_name = "accounts"

urlpatterns = [
    path("", home_view, name="home"),
    path("posts/<int:post_id>/<str:action>/", post_action_view, name="post_action"),
    path("inscription/", register_view, name="register"),
    path("connexion/", login_view, name="login"),
    path("deconnexion/", logout_view, name="logout"),
]
