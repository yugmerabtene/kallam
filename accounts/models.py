import re
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.db import models


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
