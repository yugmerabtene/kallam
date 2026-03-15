from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    LANGUE_CHOICES = [
        ("fr", "Français"),
        ("en", "English"),
        ("ar", "العربية"),
        ("de", "Deutsch"),
        ("es", "Español"),
        ("it", "Italiano"),
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
