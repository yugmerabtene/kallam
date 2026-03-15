from django.contrib import admin

from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "participants_list", "created_at")
    readonly_fields = ("created_at",)

    def participants_list(self, obj):
        return ", ".join(u.email for u in obj.participants.all())
    participants_list.short_description = "Participants"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "conversation", "created_at", "read_at")
    list_filter = ("created_at",)
    search_fields = ("sender__email",)
    readonly_fields = ("sender", "conversation", "content", "created_at", "read_at")
