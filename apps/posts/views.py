from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Exists, OuterRef, Value
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from apps.accounts.models import Follow, UserProfile

from .forms import PostForm
from .models import Post, PostLike, PostReport, PostRepost


def _annotate_posts(qs, user):
    if user.is_authenticated:
        return qs.annotate(
            like_count=Count("likes", distinct=True),
            repost_count=Count("reposts", distinct=True),
            liked_by_me=Exists(PostLike.objects.filter(post=OuterRef("pk"), user=user)),
            reposted_by_me=Exists(PostRepost.objects.filter(post=OuterRef("pk"), user=user)),
            reported_by_me=Exists(PostReport.objects.filter(post=OuterRef("pk"), reporter=user)),
        )
    return qs.annotate(
        like_count=Count("likes", distinct=True),
        repost_count=Count("reposts", distinct=True),
        liked_by_me=Value(False),
        reposted_by_me=Value(False),
        reported_by_me=Value(False),
    )


def _rate_limit(key, limit, window):
    from django.core.cache import cache
    count = cache.get(key, 0)
    if count >= limit:
        return True
    cache.set(key, count + 1, timeout=window)
    return False


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

    posts = _annotate_posts(
        Post.objects.select_related("author", "author__profile"),
        request.user,
    )[:50]

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


@require_http_methods(["GET"])
def post_detail_view(request, post_id):
    qs = Post.objects.select_related("author", "author__profile")
    post = get_object_or_404(_annotate_posts(qs, request.user), pk=post_id)
    return render(request, "accounts/post_detail.html", {"post": post})


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
