from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.posts.models import Post, PostReport

from .models import ModerationLog


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
    from django.db.models import Count

    reported_posts = (
        Post.objects.select_related("author", "author__profile")
        .annotate(report_count=Count("reports", distinct=True))
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


@_staff_required
@require_http_methods(["GET"])
def moderation_log_view(request):
    logs = ModerationLog.objects.select_related("actor", "actor__profile").order_by(
        "-created_at"
    )[:200]
    return render(request, "accounts/moderation_log.html", {"logs": logs})
