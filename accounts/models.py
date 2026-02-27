from django.conf import settings
from django.db import models
from urllib.parse import parse_qs, urlparse


def extract_youtube_video_id(url):
    if not url:
        return ""

    try:
        parsed = urlparse(url.strip())
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


class Post(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts"
    )
    content = models.CharField(max_length=280, blank=True, default="")
    image = models.ImageField(upload_to="posts/images/", null=True, blank=True)
    youtube_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.author.username}: {self.content[:30]}"

    @property
    def author_handle(self):
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
