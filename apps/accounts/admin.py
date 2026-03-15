from django.contrib import admin

from .models import Follow, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("pseudo", "user", "langue", "created_at")
    list_filter = ("langue",)
    search_fields = ("pseudo", "user__email", "bio")
    readonly_fields = ("created_at",)


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "followed", "created_at")
    search_fields = ("follower__email", "followed__email")
    readonly_fields = ("created_at",)
