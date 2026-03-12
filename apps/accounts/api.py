"""
API REST Kallam — Django Ninja
Endpoints publics (lecture) + authentifiés (écriture)
Documentation auto : /api/docs
"""
from datetime import datetime
from typing import List, Optional

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI, Schema
from ninja.security import django_auth

from apps.messaging.models import Conversation, Message
from apps.posts.models import Post, PostLike, PostReport, PostRepost

from .models import Follow, UserProfile

User = get_user_model()

api = NinjaAPI(title="Kallam API", version="1.0", urls_namespace="api")


# ── Schémas ──────────────────────────────────────────────────────────────────

class ProfileOut(Schema):
    pseudo: str
    bio: str
    langue: str
    avatar_url: Optional[str] = None
    followers_count: int
    following_count: int
    posts_count: int


class PostOut(Schema):
    id: int
    content: str
    youtube_url: str
    file_url: str
    image_url: Optional[str] = None
    created_at: datetime
    author_pseudo: str
    author_display_name: str
    like_count: int
    repost_count: int


class PostIn(Schema):
    content: str
    youtube_url: str = ""
    file_url: str = ""


class ToggleOut(Schema):
    active: bool
    count: int


class ConversationOut(Schema):
    id: int
    other_pseudo: str
    created_at: datetime


class MessageOut(Schema):
    id: int
    sender_pseudo: str
    content: str
    created_at: datetime
    read_at: Optional[datetime] = None


class MessageIn(Schema):
    content: str


# ── Utilitaire ────────────────────────────────────────────────────────────────

def _post_to_schema(p) -> PostOut:
    return PostOut(
        id=p.id,
        content=p.content,
        youtube_url=p.youtube_url,
        file_url=p.file_url,
        image_url=p.image.url if p.image else None,
        created_at=p.created_at,
        author_pseudo=p.author_handle.lstrip("@"),
        author_display_name=p.author_display_name,
        like_count=getattr(p, "like_count", p.likes.count()),
        repost_count=getattr(p, "repost_count", p.reposts.count()),
    )


# ── Posts ─────────────────────────────────────────────────────────────────────

@api.get("/posts/", response=List[PostOut], tags=["posts"], summary="Liste des publications")
def list_posts(request: HttpRequest, limit: int = 50):
    """Retourne les `limit` dernières publications (max 100)."""
    limit = min(limit, 100)
    posts = (
        Post.objects.select_related("author", "author__profile")
        .annotate(
            like_count=Count("likes", distinct=True),
            repost_count=Count("reposts", distinct=True),
        )[:limit]
    )
    return [_post_to_schema(p) for p in posts]


@api.get("/posts/{post_id}/", response=PostOut, tags=["posts"], summary="Détail d'une publication")
def get_post(request: HttpRequest, post_id: int):
    p = get_object_or_404(
        Post.objects.select_related("author", "author__profile").annotate(
            like_count=Count("likes", distinct=True),
            repost_count=Count("reposts", distinct=True),
        ),
        pk=post_id,
    )
    return _post_to_schema(p)


@api.post("/posts/", auth=django_auth, response=PostOut, tags=["posts"], summary="Créer une publication")
def create_post(request: HttpRequest, payload: PostIn):
    """Requiert une session authentifiée (cookie sessionid)."""
    content = payload.content.strip()
    if not content:
        from ninja.errors import HttpError
        raise HttpError(400, "Le contenu ne peut pas être vide.")
    p = Post.objects.create(
        author=request.user,
        content=content,
        youtube_url=payload.youtube_url,
        file_url=payload.file_url,
    )
    return PostOut(
        id=p.id,
        content=p.content,
        youtube_url=p.youtube_url,
        file_url=p.file_url,
        image_url=None,
        created_at=p.created_at,
        author_pseudo=p.author_handle.lstrip("@"),
        author_display_name=p.author_display_name,
        like_count=0,
        repost_count=0,
    )


@api.post("/posts/{post_id}/like/", auth=django_auth, response=ToggleOut, tags=["posts"], summary="Liker / unliker")
def toggle_like(request: HttpRequest, post_id: int):
    post = get_object_or_404(Post, pk=post_id)
    like, created = PostLike.objects.get_or_create(post=post, user=request.user)
    if not created:
        like.delete()
    return ToggleOut(active=created, count=post.likes.count())


@api.post("/posts/{post_id}/repost/", auth=django_auth, response=ToggleOut, tags=["posts"], summary="Reposter / annuler")
def toggle_repost(request: HttpRequest, post_id: int):
    post = get_object_or_404(Post, pk=post_id)
    repost, created = PostRepost.objects.get_or_create(post=post, user=request.user)
    if not created:
        repost.delete()
    return ToggleOut(active=created, count=post.reposts.count())


# ── Profils ───────────────────────────────────────────────────────────────────

@api.get("/profiles/{pseudo}/", response=ProfileOut, tags=["profiles"], summary="Profil utilisateur")
def get_profile(request: HttpRequest, pseudo: str):
    profile = get_object_or_404(UserProfile, pseudo=pseudo)
    return ProfileOut(
        pseudo=profile.pseudo,
        bio=profile.bio,
        langue=profile.langue,
        avatar_url=profile.avatar.url if profile.avatar else None,
        followers_count=Follow.objects.filter(followed=profile.user).count(),
        following_count=Follow.objects.filter(follower=profile.user).count(),
        posts_count=Post.objects.filter(author=profile.user).count(),
    )


@api.get("/profiles/{pseudo}/posts/", response=List[PostOut], tags=["profiles"], summary="Publications d'un profil")
def get_profile_posts(request: HttpRequest, pseudo: str, limit: int = 50):
    profile = get_object_or_404(UserProfile, pseudo=pseudo)
    limit = min(limit, 100)
    posts = (
        Post.objects.filter(author=profile.user)
        .select_related("author", "author__profile")
        .annotate(
            like_count=Count("likes", distinct=True),
            repost_count=Count("reposts", distinct=True),
        )[:limit]
    )
    return [_post_to_schema(p) for p in posts]


# ── Utilisateur courant ────────────────────────────────────────────────────────

@api.get("/me/", auth=django_auth, response=ProfileOut, tags=["me"], summary="Mon profil")
def get_me(request: HttpRequest):
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        from ninja.errors import HttpError
        raise HttpError(404, "Profil non configuré.")
    return ProfileOut(
        pseudo=profile.pseudo,
        bio=profile.bio,
        langue=profile.langue,
        avatar_url=profile.avatar.url if profile.avatar else None,
        followers_count=Follow.objects.filter(followed=request.user).count(),
        following_count=Follow.objects.filter(follower=request.user).count(),
        posts_count=Post.objects.filter(author=request.user).count(),
    )


# ── Report / Follow ────────────────────────────────────────────────────────────

@api.post("/posts/{post_id}/report/", auth=django_auth, response=ToggleOut, tags=["posts"], summary="Signaler / annuler un signalement")
def toggle_report(request: HttpRequest, post_id: int):
    post = get_object_or_404(Post, pk=post_id)
    report, created = PostReport.objects.get_or_create(post=post, reporter=request.user)
    if not created:
        report.delete()
    return ToggleOut(active=created, count=post.reports.count())


@api.post("/follow/{pseudo}/", auth=django_auth, response=ToggleOut, tags=["profiles"], summary="Suivre / ne plus suivre un profil")
def toggle_follow(request: HttpRequest, pseudo: str):
    profile = get_object_or_404(UserProfile, pseudo=pseudo)
    if profile.user == request.user:
        from ninja.errors import HttpError
        raise HttpError(400, "Tu ne peux pas te suivre toi-même.")
    follow, created = Follow.objects.get_or_create(follower=request.user, followed=profile.user)
    if not created:
        follow.delete()
    return ToggleOut(active=created, count=Follow.objects.filter(followed=profile.user).count())


# ── Messaging ─────────────────────────────────────────────────────────────────

def _conv_to_schema(conv, user) -> ConversationOut:
    other = conv.other_participant(user)
    return ConversationOut(
        id=conv.id,
        other_pseudo=other.profile.pseudo if hasattr(other, "profile") else str(other.pk),
        created_at=conv.created_at,
    )


@api.get("/conversations/", auth=django_auth, response=List[ConversationOut], tags=["messaging"], summary="Mes conversations")
def list_conversations(request: HttpRequest):
    convs = (
        Conversation.objects.filter(participants=request.user)
        .prefetch_related("participants", "participants__profile")
        .order_by("-created_at")
    )
    return [_conv_to_schema(c, request.user) for c in convs]


@api.post("/conversations/", auth=django_auth, response=ConversationOut, tags=["messaging"], summary="Démarrer une conversation")
def start_conversation(request: HttpRequest, pseudo: str):
    profile = get_object_or_404(UserProfile, pseudo=pseudo)
    if profile.user == request.user:
        from ninja.errors import HttpError
        raise HttpError(400, "Tu ne peux pas te parler à toi-même.")
    existing = (
        Conversation.objects.filter(participants=request.user)
        .filter(participants=profile.user)
        .prefetch_related("participants", "participants__profile")
        .first()
    )
    if existing:
        return _conv_to_schema(existing, request.user)
    conv = Conversation.objects.create()
    conv.participants.add(request.user, profile.user)
    conv.refresh_from_db()
    conv.participants.prefetch_related("profile")
    return _conv_to_schema(conv, request.user)


@api.get("/conversations/{conv_id}/messages/", auth=django_auth, response=List[MessageOut], tags=["messaging"], summary="Messages d'une conversation")
def list_messages(request: HttpRequest, conv_id: int, limit: int = 50):
    from ninja.errors import HttpError
    conv = get_object_or_404(Conversation, pk=conv_id)
    if not conv.participants.filter(pk=request.user.pk).exists():
        raise HttpError(403, "Accès refusé.")
    limit = min(limit, 200)
    msgs = (
        conv.messages.select_related("sender", "sender__profile")
        .order_by("created_at")
    )[-limit:]
    return [
        MessageOut(
            id=m.id,
            sender_pseudo=m.sender.profile.pseudo if hasattr(m.sender, "profile") else str(m.sender.pk),
            content=m.content,
            created_at=m.created_at,
            read_at=m.read_at,
        )
        for m in msgs
    ]


@api.post("/conversations/{conv_id}/messages/", auth=django_auth, response=MessageOut, tags=["messaging"], summary="Envoyer un message")
def send_message(request: HttpRequest, conv_id: int, payload: MessageIn):
    from django.core.cache import cache
    from ninja.errors import HttpError

    conv = get_object_or_404(Conversation, pk=conv_id)
    if not conv.participants.filter(pk=request.user.pk).exists():
        raise HttpError(403, "Accès refusé.")

    key = f"api_msg:{request.user.pk}"
    count = cache.get(key, 0)
    if count >= 30:
        raise HttpError(429, "Trop de messages. Attends un peu.")
    cache.set(key, count + 1, timeout=60)

    content = payload.content.strip()
    if not content or len(content) > 2000:
        raise HttpError(400, "Contenu invalide (1-2000 caractères).")

    msg = Message.objects.create(conversation=conv, sender=request.user, content=content)
    try:
        sender_pseudo = request.user.profile.pseudo
    except Exception:
        sender_pseudo = str(request.user.pk)
    return MessageOut(
        id=msg.id,
        sender_pseudo=sender_pseudo,
        content=msg.content,
        created_at=msg.created_at,
        read_at=msg.read_at,
    )
