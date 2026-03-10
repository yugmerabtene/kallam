from .models import Message


def messaging(request):
    if request.user.is_authenticated:
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
        return {"unread_count": count}
    return {"unread_count": 0}
