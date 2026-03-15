from django.core.cache import cache

from .models import Message


def messaging(request):
    if request.user.is_authenticated:
        cache_key = f"unread_msg_count:{request.user.pk}"
        count = cache.get(cache_key)
        if count is None:
            try:
                count = (
                    Message.objects.filter(
                        conversation__participants=request.user,
                        read_at__isnull=True,
                    )
                    .exclude(sender=request.user)
                    .count()
                )
            except Exception:
                count = 0
            cache.set(cache_key, count, timeout=60)
        return {"unread_count": count}
    return {"unread_count": 0}
