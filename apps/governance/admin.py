from django.contrib import admin

from .models import CharterVersion, SurveyQuestion, SurveyResponse, TrustList


@admin.register(TrustList)
class TrustListAdmin(admin.ModelAdmin):
    list_display = ("user", "trusted", "created_at")
    search_fields = ("user__email", "trusted__email")
    readonly_fields = ("created_at",)


@admin.register(SurveyQuestion)
class SurveyQuestionAdmin(admin.ModelAdmin):
    list_display = ("text_preview", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("text",)
    readonly_fields = ("created_at",)

    def text_preview(self, obj):
        return obj.text[:80]
    text_preview.short_description = "Question"


@admin.register(SurveyResponse)
class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ("question", "answer_preview", "created_at")
    readonly_fields = ("question", "answer", "created_at")

    def answer_preview(self, obj):
        return obj.answer[:80]
    answer_preview.short_description = "Réponse"


@admin.register(CharterVersion)
class CharterVersionAdmin(admin.ModelAdmin):
    list_display = ("version", "is_current", "published_at")
    list_filter = ("is_current",)
    readonly_fields = ("published_at",)
