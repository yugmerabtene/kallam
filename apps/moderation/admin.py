from django.contrib import admin

from .models import ModerationLog


@admin.register(ModerationLog)
class ModerationLogAdmin(admin.ModelAdmin):
    list_display = ("actor", "action", "post_id_ref", "post_preview", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("actor__email", "post_preview")
    readonly_fields = ("actor", "action", "post_id_ref", "post_preview", "created_at")
