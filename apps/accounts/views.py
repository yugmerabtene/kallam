import json

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from apps.governance.models import TrustList
from apps.posts.models import Post

from .forms import LoginForm, ProfileForm, RegisterForm
from .models import Follow, UserProfile


def _rate_limit(key, limit, window):
    """Return True if the request should be blocked (limit exceeded)."""
    count = cache.get(key, 0)
    if count >= limit:
        return True
    cache.set(key, count + 1, timeout=window)
    return False


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:home")

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, _("Inscription reussie."))
        return redirect("accounts:home")

    return render(request, "accounts/register.html", {"form": form})


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:home")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ip = request.META.get("REMOTE_ADDR", "unknown")
        if _rate_limit(f"login:{ip}", limit=5, window=300):
            form.add_error(None, _("Trop de tentatives. Reessaie dans 5 minutes."))
            return render(request, "accounts/login.html", {"form": form})

        email = form.cleaned_data["email"].strip().lower()
        password = form.cleaned_data["password"]
        user = authenticate(request, username=email, password=password)
        if user is None:
            form.add_error(None, "Identifiants invalides.")
        else:
            login(request, user)
            messages.success(request, _("Connexion reussie."))
            return redirect("accounts:home")

    return render(request, "accounts/login.html", {"form": form})


@require_http_methods(["POST"])
def logout_view(request):
    logout(request)
    messages.info(request, _("Vous etes deconnecte."))
    return redirect("accounts:login")


@require_http_methods(["GET"])
def profile_view(request, pseudo):
    from django.db.models import Count, Exists, OuterRef, Value

    from apps.posts.models import PostLike, PostReport, PostRepost

    from django.shortcuts import get_object_or_404
    profile = get_object_or_404(UserProfile, pseudo=pseudo)

    qs = Post.objects.filter(author=profile.user).select_related(
        "author", "author__profile"
    )
    if request.user.is_authenticated:
        qs = qs.annotate(
            like_count=Count("likes", distinct=True),
            repost_count=Count("reposts", distinct=True),
            liked_by_me=Exists(
                PostLike.objects.filter(post=OuterRef("pk"), user=request.user)
            ),
            reposted_by_me=Exists(
                PostRepost.objects.filter(post=OuterRef("pk"), user=request.user)
            ),
            reported_by_me=Exists(
                PostReport.objects.filter(post=OuterRef("pk"), reporter=request.user)
            ),
        )
    else:
        qs = qs.annotate(
            like_count=Count("likes", distinct=True),
            repost_count=Count("reposts", distinct=True),
            liked_by_me=Value(False),
            reposted_by_me=Value(False),
            reported_by_me=Value(False),
        )
    posts = qs[:50]

    followers_count = Follow.objects.filter(followed=profile.user).count()
    following_count = Follow.objects.filter(follower=profile.user).count()
    is_following = False
    if request.user.is_authenticated and request.user != profile.user:
        is_following = Follow.objects.filter(
            follower=request.user, followed=profile.user
        ).exists()

    is_trusted = False
    if request.user.is_authenticated and request.user != profile.user:
        is_trusted = TrustList.objects.filter(
            user=request.user, trusted=profile.user
        ).exists()

    return render(
        request,
        "accounts/profile.html",
        {
            "profile": profile,
            "posts": posts,
            "is_following": is_following,
            "is_trusted": is_trusted,
            "followers_count": followers_count,
            "following_count": following_count,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def edit_profile_view(request):
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = None

    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        saved.user = request.user
        saved.save()
        messages.success(request, _("Profil mis a jour."))
        return redirect("accounts:profile", pseudo=saved.pseudo)
    return render(request, "accounts/edit_profile.html", {"form": form, "profile": profile})


@login_required
@require_http_methods(["POST"])
def follow_view(request, pseudo):
    from django.shortcuts import get_object_or_404
    profile = get_object_or_404(UserProfile, pseudo=pseudo)
    if profile.user == request.user:
        messages.error(request, "Tu ne peux pas te suivre toi-même.")
    else:
        follow, created = Follow.objects.get_or_create(
            follower=request.user, followed=profile.user
        )
        if not created:
            follow.delete()
    return redirect("accounts:profile", pseudo=pseudo)


@login_required
@require_http_methods(["GET", "POST"])
def delete_account_view(request):
    if request.method == "POST":
        password = request.POST.get("password", "")
        user = authenticate(request, username=request.user.email, password=password)
        if user is None:
            messages.error(request, _("Mot de passe incorrect. Suppression annulée."))
            return render(request, "accounts/delete_account.html")
        logout(request)
        user.delete()
        messages.success(request, _("Ton compte a été supprimé définitivement."))
        return redirect("accounts:login")
    return render(request, "accounts/delete_account.html")


@login_required
@require_http_methods(["GET"])
def export_data_view(request):
    user = request.user
    try:
        profile = user.profile
        profile_data = {
            "pseudo": profile.pseudo,
            "bio": profile.bio,
            "langue": profile.langue,
            "created_at": profile.created_at.isoformat(),
        }
    except UserProfile.DoesNotExist:
        profile_data = None

    posts_qs = Post.objects.filter(author=user).values(
        "id", "content", "youtube_url", "file_url", "created_at"
    )
    posts = [
        {**p, "created_at": p["created_at"].isoformat()} for p in posts_qs
    ]

    following = list(
        Follow.objects.filter(follower=user)
        .select_related("followed__profile")
        .values_list("followed__profile__pseudo", flat=True)
    )
    followers = list(
        Follow.objects.filter(followed=user)
        .select_related("follower__profile")
        .values_list("follower__profile__pseudo", flat=True)
    )
    trusted = list(
        TrustList.objects.filter(user=user)
        .select_related("trusted__profile")
        .values_list("trusted__profile__pseudo", flat=True)
    )

    data = {
        "export_date": timezone.now().isoformat(),
        "user": {
            "email": user.email,
            "date_joined": user.date_joined.isoformat(),
        },
        "profile": profile_data,
        "posts": posts,
        "following": following,
        "followers": followers,
        "trusted_users": trusted,
    }

    response = HttpResponse(
        json.dumps(data, ensure_ascii=False, indent=2),
        content_type="application/json; charset=utf-8",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="kallam-mes-donnees-{user.id}.json"'
    )
    return response
