from django.conf import settings
from django.db import models


class Post(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts"
    )
    content = models.CharField(max_length=280)
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
