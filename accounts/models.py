import re
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.db import models

from .encryption import EncryptedTextField


URL_IN_TEXT_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)
ALLOWED_FILE_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "csv",
    "txt",
    "json",
    "xml",
    "zip",
    "rar",
    "7z",
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp",
    "svg",
    "mp3",
    "wav",
    "ogg",
    "mp4",
    "mov",
    "webm",
    "avi",
    "mkv",
}


def _clean_candidate_url(raw):
    return (raw or "").strip().rstrip(".,;:!?)")


def extract_youtube_video_id(url):
    cleaned_url = _clean_candidate_url(url)
    if not cleaned_url:
        return ""

    try:
        parsed = urlparse(cleaned_url)
    except ValueError:
        return ""

    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").strip("/")
    if host.startswith("www."):
        host = host[4:]

    video_id = ""
    if host == "youtu.be":
        video_id = path.split("/")[0] if path else ""
    elif host in {"youtube.com", "m.youtube.com", "music.youtube.com"}:
        if path == "watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        elif path.startswith("embed/"):
            video_id = path.split("/", 1)[1]
        elif path.startswith("shorts/"):
            video_id = path.split("/", 1)[1]
        elif path.startswith("live/"):
            video_id = path.split("/", 1)[1]

    video_id = (video_id or "").split("&")[0].strip()
    allowed_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    if len(video_id) != 11 or any(ch not in allowed_chars for ch in video_id):
        return ""
    return video_id


def extract_first_youtube_url(text):
    if not text:
        return ""
    for raw_url in URL_IN_TEXT_PATTERN.findall(text):
        candidate = _clean_candidate_url(raw_url)
        if extract_youtube_video_id(candidate):
            return candidate
    return ""


def is_file_url(url):
    cleaned_url = _clean_candidate_url(url)
    if not cleaned_url:
        return False

    try:
        parsed = urlparse(cleaned_url)
    except ValueError:
        return False

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False

    path = (parsed.path or "").strip("/")
    if "." not in path:
        return False

    extension = path.rsplit(".", 1)[-1].lower()
    return extension in ALLOWED_FILE_EXTENSIONS


class UserProfile(models.Model):
    LANGUE_CHOICES = [
        ("fr", "Français"),
        ("en", "English"),
        ("ar", "العربية"),
    ]
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    pseudo = models.CharField(max_length=50, unique=True)
    bio = models.CharField(max_length=160, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    langue = models.CharField(max_length=5, choices=LANGUE_CHOICES, default="fr")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"@{self.pseudo}"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("accounts:profile", kwargs={"pseudo": self.pseudo})


class Follow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following",
    )
    followed = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followers",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["follower", "followed"], name="unique_follow"
            )
        ]


class Post(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts"
    )
    content = models.CharField(max_length=280, blank=True, default="")
    image = models.ImageField(upload_to="posts/images/", null=True, blank=True)
    youtube_url = models.URLField(blank=True)
    file_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.author.username}: {self.content[:30]}"

    @property
    def author_handle(self):
        try:
            return f"@{self.author.profile.pseudo}"
        except Exception:
            raw = self.author.username or self.author.email or "user"
            return f"@{raw.split('@')[0].lower()}"

    @property
    def author_display_name(self):
        full_name = f"{self.author.first_name} {self.author.last_name}".strip()
        return full_name or self.author_handle

    @property
    def youtube_embed_url(self):
        video_id = extract_youtube_video_id(self.youtube_url)
        if not video_id:
            return ""
        return f"https://www.youtube.com/embed/{video_id}"


class Conversation(models.Model):
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="conversations",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def other_participant(self, user):
        return self.participants.exclude(pk=user.pk).first()


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    content = EncryptedTextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]


class PostLike(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="post_likes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["post", "user"], name="unique_like_per_user")
        ]


class PostRepost(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reposts")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="post_reposts"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["post", "user"], name="unique_repost_per_user"
            )
        ]


class PostReport(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reported_posts",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["post", "reporter"], name="unique_report_per_user"
            )
        ]


class TrustList(models.Model):
    """Liste de confiance : utilisateurs dont on veut voir le contenu en priorité."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trust_list"
    )
    trusted = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trusted_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "trusted"], name="unique_trust")
        ]


class ModerationLog(models.Model):
    """Journal horodaté des actions de modération (staff)."""
    ACTION_DELETE  = "delete"
    ACTION_DISMISS = "dismiss"
    ACTION_CHOICES = [
        (ACTION_DELETE,  "Suppression"),
        (ACTION_DISMISS, "Signalements ignorés"),
    ]
    actor        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="mod_actions"
    )
    action       = models.CharField(max_length=20, choices=ACTION_CHOICES)
    post_id_ref  = models.IntegerField()
    post_preview = models.CharField(max_length=120, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class SurveyQuestion(models.Model):
    """Question d'enquête communautaire."""
    text       = models.CharField(max_length=400)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:60]


class SurveyResponse(models.Model):
    """Réponse anonyme à une enquête — aucun lien avec un compte."""
    question   = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE, related_name="responses")
    answer     = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    # Volontairement sans FK utilisateur — anonyme RGPD-friendly
