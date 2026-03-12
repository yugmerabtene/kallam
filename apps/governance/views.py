from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Exists, OuterRef, Value
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from apps.accounts.models import UserProfile
from apps.posts.models import Post, PostLike, PostReport, PostRepost

from .models import SurveyQuestion, SurveyResponse, TrustList


def _rate_limit(key, limit, window):
    from django.core.cache import cache
    count = cache.get(key, 0)
    if count >= limit:
        return True
    cache.set(key, count + 1, timeout=window)
    return False


@require_http_methods(["GET"])
def charter_view(request):
    return render(request, "accounts/charter.html")


@login_required
@require_http_methods(["POST"])
def trust_view(request, pseudo):
    profile = get_object_or_404(UserProfile, pseudo=pseudo)
    if profile.user == request.user:
        messages.error(request, _("Tu ne peux pas te faire confiance à toi-même."))
    else:
        trust, created = TrustList.objects.get_or_create(
            user=request.user, trusted=profile.user
        )
        if not created:
            trust.delete()
    return redirect("accounts:profile", pseudo=pseudo)


@login_required
@require_http_methods(["GET"])
def trusted_feed_view(request):
    trusted_ids = TrustList.objects.filter(user=request.user).values_list(
        "trusted", flat=True
    )
    posts = (
        Post.objects.filter(author__in=trusted_ids)
        .select_related("author", "author__profile")
        .annotate(
            like_count=Count("likes", distinct=True),
            repost_count=Count("reposts", distinct=True),
            liked_by_me=Exists(
                PostLike.objects.filter(post=OuterRef("pk"), user=request.user)
            ),
            reposted_by_me=Exists(
                PostRepost.objects.filter(post=OuterRef("pk"), user=request.user)
            ),
            reported_by_me=Exists(
                PostReport.objects.filter(post=OuterRef("pk"), reporter=request.user)
            ),
        )[:50]
    )
    try:
        user_profile = request.user.profile
    except UserProfile.DoesNotExist:
        user_profile = None
    return render(
        request,
        "accounts/trusted_feed.html",
        {
            "posts": posts,
            "trusted_count": trusted_ids.count(),
            "user_profile": user_profile,
        },
    )


@require_http_methods(["GET", "POST"])
def survey_view(request):
    question = SurveyQuestion.objects.filter(is_active=True).first()
    if not question:
        question = SurveyQuestion.objects.create(
            text="Comment améliorer Kallam ? Partage ton avis (anonyme, sans lien avec ton compte)."
        )
    submitted = False
    if request.method == "POST":
        if _rate_limit(f"survey:{request.META.get('REMOTE_ADDR','x')}", limit=3, window=3600):
            messages.error(request, _("Trop de réponses. Réessaie plus tard."))
        else:
            answer = request.POST.get("answer", "").strip()
            if answer and len(answer) <= 1000:
                SurveyResponse.objects.create(question=question, answer=answer)
                submitted = True
            else:
                messages.error(request, _("Réponse invalide (1-1000 caractères)."))
    return render(
        request, "accounts/survey.html", {"question": question, "submitted": submitted}
    )
