from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from apps.accounts.models import UserProfile
from apps.posts.models import Post, PostLike, PostReport, PostRepost

from .models import CharterVersion, SurveyQuestion, SurveyResponse, TrustList


def _rate_limit(key, limit, window):
    from django.core.cache import cache
    count = cache.get(key, 0)
    if count >= limit:
        return True
    cache.set(key, count + 1, timeout=window)
    return False


def _staff_required(view_fn):
    from functools import wraps

    @wraps(view_fn)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            from django.http import Http404
            raise Http404
        return view_fn(request, *args, **kwargs)

    return wrapper


@require_http_methods(["GET"])
def charter_view(request):
    version = CharterVersion.current()
    return render(request, "accounts/charter.html", {"charter_version": version})


@require_http_methods(["GET"])
def cgu_view(request):
    """Conditions Générales d'Utilisation — page publique."""
    return render(request, "accounts/cgu.html")


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


@require_http_methods(["GET"])
def byod_view(request):
    """Page démo BYOD : QR code + guide d'accès smartphone."""
    site_url = request.build_absolute_uri("/")
    return render(request, "accounts/byod.html", {"site_url": site_url})


@_staff_required
@require_http_methods(["GET"])
def survey_summary_view(request):
    """Tableau de synthèse des réponses anonymes (staff uniquement)."""
    questions = (
        SurveyQuestion.objects.annotate(response_count=Count("responses"))
        .prefetch_related("responses")
        .order_by("-created_at")
    )
    return render(request, "accounts/survey_summary.html", {"questions": questions})


@_staff_required
@require_http_methods(["GET"])
def metrics_view(request):
    """Métriques d'impact : participation, engagement, apprentissages (staff uniquement)."""
    from django.contrib.auth import get_user_model
    from apps.messaging.models import Conversation, Message
    from apps.moderation.models import ModerationLog
    from apps.posts.models import Post, PostReport

    User = get_user_model()

    total_users      = User.objects.count()
    total_posts      = Post.objects.count()
    total_messages   = Message.objects.count()
    total_reports    = PostReport.objects.count()
    total_survey     = SurveyResponse.objects.count()
    total_mod_actions = ModerationLog.objects.count()
    total_convs      = Conversation.objects.count()

    # Top 3 questions by response volume
    top_questions = (
        SurveyQuestion.objects.annotate(response_count=Count("responses"))
        .order_by("-response_count")[:3]
    )

    # Recent survey answers (last 5) as proxy for "top attentes"
    recent_answers = SurveyResponse.objects.order_by("-created_at")[:5]

    ctx = {
        "total_users": total_users,
        "total_posts": total_posts,
        "total_messages": total_messages,
        "total_reports": total_reports,
        "total_survey": total_survey,
        "total_mod_actions": total_mod_actions,
        "total_convs": total_convs,
        "top_questions": top_questions,
        "recent_answers": recent_answers,
    }
    return render(request, "accounts/metrics.html", ctx)
