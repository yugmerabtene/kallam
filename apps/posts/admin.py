from django.contrib import admin

from .models import Post, PostLike, PostReport, PostRepost


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("author", "content_preview", "created_at", "likes_count", "reports_count")
    list_filter = ("created_at",)
    search_fields = ("author__email", "content")
    readonly_fields = ("created_at",)

    def content_preview(self, obj):
        return obj.content[:60]
    content_preview.short_description = "Contenu"

    def likes_count(self, obj):
        return obj.likes.count()
    likes_count.short_description = "Likes"

    def reports_count(self, obj):
        return obj.reports.count()
    reports_count.short_description = "Signalements"


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "created_at")
    search_fields = ("user__email",)
    readonly_fields = ("created_at",)


@admin.register(PostRepost)
class PostRepostAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "created_at")
    search_fields = ("user__email",)
    readonly_fields = ("created_at",)


@admin.register(PostReport)
class PostReportAdmin(admin.ModelAdmin):
    list_display = ("reporter", "post", "created_at")
    search_fields = ("reporter__email",)
    readonly_fields = ("created_at",)
