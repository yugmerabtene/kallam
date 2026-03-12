from django.conf import settings
from django.db import models


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
