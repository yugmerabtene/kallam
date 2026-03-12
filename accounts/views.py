import json
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Count, Exists, OuterRef, Value
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods


def _rate_limit(key, limit, window):
    """Return True if the request should be blocked (limit exceeded)."""
    count = cache.get(key, 0)
    if count >= limit:
        return True
    cache.set(key, count + 1, timeout=window)
    return False

from .forms import LoginForm, PostForm, ProfileForm, RegisterForm
from .models import (
    Conversation,
    Follow,
    Message,
    ModerationLog,
    Post,
    PostLike,
    PostReport,
    PostRepost,
    SurveyQuestion,
    SurveyResponse,
    TrustList,
    UserProfile,
)


@login_required
@require_http_methods(["GET", "POST"])
def home_view(request):
    post_form = PostForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if _rate_limit(f"post:{request.user.pk}", limit=20, window=60):
            messages.error(request, _("Trop de publications. Attends un peu."))
            return redirect("accounts:home")
        if post_form.is_valid():
            Post.objects.create(
                author=request.user,
                content=post_form.cleaned_data["content"],
                image=post_form.cleaned_data.get("image"),
                youtube_url=post_form.cleaned_data.get("youtube_url", ""),
                file_url=post_form.cleaned_data.get("attachment_url", ""),
            )
            messages.success(request, _("Message publie."))
            return redirect("accounts:home")
        messages.error(request, _("Impossible de publier ce message."))

    try:
        user_profile = request.user.profile
    except UserProfile.DoesNotExist:
        user_profile = None
    followers_count = Follow.objects.filter(followed=request.user).count()
    following_count = Follow.objects.filter(follower=request.user).count()

    posts = (
        Post.objects.select_related("author", "author__profile")
        .annotate(
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
        )[:50]
    )
    return render(
        request,
        "accounts/home.html",
        {
            "post_form": post_form,
            "posts": posts,
            "user_profile": user_profile,
            "followers_count": followers_count,
            "following_count": following_count,
        },
    )


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


@login_required
@require_http_methods(["POST"])
def post_action_view(request, post_id, action):
    post = get_object_or_404(Post, id=post_id)

    if action == "like":
        like, created = PostLike.objects.get_or_create(post=post, user=request.user)
        if not created:
            like.delete()
    elif action == "repost":
        repost, created = PostRepost.objects.get_or_create(post=post, user=request.user)
        if not created:
            repost.delete()
    elif action == "report":
        _report, created = PostReport.objects.get_or_create(post=post, reporter=request.user)
        if created:
            messages.info(request, _("Publication signalee."))
        else:
            messages.info(request, _("Publication deja signalee."))
    else:
        messages.error(request, _("Action non supportee."))

    next_url = request.POST.get("next") or reverse("accounts:home")
    if not url_has_allowed_host_and_scheme(
        url=next_url, allowed_hosts={request.get_host()}
    ):
        next_url = reverse("accounts:home")
    return redirect(next_url)


@require_http_methods(["GET"])
def post_detail_view(request, post_id):
    qs = Post.objects.select_related("author", "author__profile")
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
    post = get_object_or_404(qs, pk=post_id)
    return render(request, "accounts/post_detail.html", {"post": post})


@require_http_methods(["GET"])
def profile_view(request, pseudo):
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


# ── Modération ────────────────────────────────────────────────────────────────

def _staff_required(view_fn):
    """Restreint l'accès aux membres du staff (is_staff=True)."""
    from functools import wraps

    @wraps(view_fn)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            from django.http import Http404
            raise Http404
        return view_fn(request, *args, **kwargs)

    return wrapper


@_staff_required
@require_http_methods(["GET"])
def moderation_view(request):
    from django.db.models import Count as DbCount

    reported_posts = (
        Post.objects.select_related("author", "author__profile")
        .annotate(report_count=DbCount("reports", distinct=True))
        .filter(report_count__gt=0)
        .order_by("-report_count", "-created_at")
    )
    total_reports = PostReport.objects.count()
    return render(
        request,
        "accounts/moderation.html",
        {
            "reported_posts": reported_posts,
            "total_reports": total_reports,
        },
    )


@_staff_required
@require_http_methods(["POST"])
def moderation_action_view(request, post_id, action):
    post = get_object_or_404(Post, id=post_id)
    preview = (post.content or "")[:120]
    if action == "delete":
        post.delete()
        ModerationLog.objects.create(
            actor=request.user,
            action=ModerationLog.ACTION_DELETE,
            post_id_ref=post_id,
            post_preview=preview,
        )
        messages.success(request, f"Post #{post_id} supprimé.")
    elif action == "dismiss":
        PostReport.objects.filter(post=post).delete()
        ModerationLog.objects.create(
            actor=request.user,
            action=ModerationLog.ACTION_DISMISS,
            post_id_ref=post_id,
            post_preview=preview,
        )
        messages.info(request, f"Signalements du post #{post_id} ignorés.")
    return redirect("accounts:moderation")


# ── Messagerie ────────────────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def inbox_view(request):
    from django.db.models import Max, OuterRef, Subquery

    last_msg_time = (
        Message.objects.filter(conversation=OuterRef("pk"))
        .order_by("-created_at")
        .values("created_at")[:1]
    )
    last_msg_content = (
        Message.objects.filter(conversation=OuterRef("pk"))
        .order_by("-created_at")
        .values("content")[:1]
    )
    conversations = (
        request.user.conversations.prefetch_related("participants", "participants__profile")
        .annotate(last_at=Subquery(last_msg_time), last_preview=Subquery(last_msg_content))
        .order_by("-last_at")
    )
    return render(request, "accounts/inbox.html", {"conversations": conversations})


@login_required
@require_http_methods(["GET", "POST"])
def conversation_view(request, pk):
    conversation = get_object_or_404(
        Conversation, pk=pk, participants=request.user
    )
    if request.method == "POST":
        if _rate_limit(f"msg:{request.user.pk}", limit=30, window=60):
            messages.error(request, "Trop de messages. Attends un peu.")
            return redirect("accounts:conversation", pk=pk)
        content = request.POST.get("content", "").strip()
        if content and len(content) <= 2000:
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=content,
            )
        return redirect("accounts:conversation", pk=pk)

    # Mark incoming messages as read
    conversation.messages.filter(
        read_at__isnull=True
    ).exclude(sender=request.user).update(read_at=timezone.now())

    msgs = conversation.messages.select_related("sender", "sender__profile").all()
    other = conversation.other_participant(request.user)
    return render(
        request,
        "accounts/conversation.html",
        {"conversation": conversation, "messages": msgs, "other": other},
    )


@login_required
@require_http_methods(["POST"])
def start_conversation_view(request, pseudo):
    profile = get_object_or_404(UserProfile, pseudo=pseudo)
    if profile.user == request.user:
        return redirect("accounts:home")

    existing = (
        Conversation.objects.filter(participants=request.user)
        .filter(participants=profile.user)
        .first()
    )
    if existing:
        return redirect("accounts:conversation", pk=existing.pk)

    conversation = Conversation.objects.create()
    conversation.participants.add(request.user, profile.user)
    return redirect("accounts:conversation", pk=conversation.pk)


# ── Gouvernance (Sprint 3) ─────────────────────────────────────────────────────

@require_http_methods(["GET"])
def charter_view(request):
    return render(request, "accounts/charter.html")


@login_required
@require_http_methods(["POST"])
def trust_view(request, pseudo):
    profile = get_object_or_404(UserProfile, pseudo=pseudo)
    if profile.user == request.user:
        messages.error(request, _("Tu ne peux pas te faire confiance à toi-même."))
    else:
        trust, created = TrustList.objects.get_or_create(
            user=request.user, trusted=profile.user
        )
        if not created:
            trust.delete()
    return redirect("accounts:profile", pseudo=pseudo)


@login_required
@require_http_methods(["GET"])
def trusted_feed_view(request):
    trusted_ids = TrustList.objects.filter(user=request.user).values_list(
        "trusted", flat=True
    )
    posts = (
        Post.objects.filter(author__in=trusted_ids)
        .select_related("author", "author__profile")
        .annotate(
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
        )[:50]
    )
    try:
        user_profile = request.user.profile
    except UserProfile.DoesNotExist:
        user_profile = None
    return render(
        request,
        "accounts/trusted_feed.html",
        {
            "posts": posts,
            "trusted_count": trusted_ids.count(),
            "user_profile": user_profile,
        },
    )


@_staff_required
@require_http_methods(["GET"])
def moderation_log_view(request):
    logs = ModerationLog.objects.select_related("actor", "actor__profile").order_by(
        "-created_at"
    )[:200]
    return render(request, "accounts/moderation_log.html", {"logs": logs})


@require_http_methods(["GET", "POST"])
def survey_view(request):
    question = SurveyQuestion.objects.filter(is_active=True).first()
    if not question:
        question = SurveyQuestion.objects.create(
            text="Comment améliorer Kallam ? Partage ton avis (anonyme, sans lien avec ton compte)."
        )
    submitted = False
    if request.method == "POST":
        if _rate_limit(f"survey:{request.META.get('REMOTE_ADDR','x')}", limit=3, window=3600):
            messages.error(request, _("Trop de réponses. Réessaie plus tard."))
        else:
            answer = request.POST.get("answer", "").strip()
            if answer and len(answer) <= 1000:
                SurveyResponse.objects.create(question=question, answer=answer)
                submitted = True
            else:
                messages.error(request, _("Réponse invalide (1-1000 caractères)."))
    return render(
        request, "accounts/survey.html", {"question": question, "submitted": submitted}
    )


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
            "first_name": user.first_name,
            "last_name": user.last_name,
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
