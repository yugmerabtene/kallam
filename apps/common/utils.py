"""Utilitaires partagés entre toutes les apps Kallam."""
from functools import wraps

from django.core.cache import cache
from django.http import Http404


def get_client_ip(request):
    """Retourne l'IP réelle du client, même derrière un reverse proxy."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def rate_limit(key, limit, window):
    """Retourne True si la limite est dépassée (requête à bloquer)."""
    count = cache.get(key, 0)
    if count >= limit:
        return True
    cache.set(key, count + 1, timeout=window)
    return False


def staff_required(view_fn):
    """Décorateur : restreint l'accès aux membres du staff (is_staff=True)."""
    @wraps(view_fn)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            raise Http404
        return view_fn(request, *args, **kwargs)
    return wrapper
