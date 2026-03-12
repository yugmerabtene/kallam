from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.models import UserProfile

from .models import Conversation, Message


def _rate_limit(key, limit, window):
    from django.core.cache import cache
    count = cache.get(key, 0)
    if count >= limit:
        return True
    cache.set(key, count + 1, timeout=window)
    return False


@login_required
@require_http_methods(["GET"])
def inbox_view(request):
    from django.db.models import OuterRef, Subquery

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
