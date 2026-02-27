from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from .forms import LoginForm, PostForm, RegisterForm
from .models import Post, PostLike, PostReport, PostRepost


@login_required
@require_http_methods(["GET", "POST"])
def home_view(request):
    post_form = PostForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if post_form.is_valid():
            Post.objects.create(
                author=request.user,
                content=post_form.cleaned_data["content"],
                image=post_form.cleaned_data.get("image"),
                youtube_url=post_form.cleaned_data.get("youtube_url", ""),
                file_url=post_form.cleaned_data.get("attachment_url", ""),
            )
            messages.success(request, "Message publie.")
            return redirect("accounts:home")
        messages.error(request, "Impossible de publier ce message.")

    posts = (
        Post.objects.select_related("author")
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
    return render(
        request,
        "accounts/home.html",
        {
            "post_form": post_form,
            "posts": posts,
        },
    )


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:home")

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Inscription reussie.")
        return redirect("accounts:home")

    return render(request, "accounts/register.html", {"form": form})


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:home")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip().lower()
        password = form.cleaned_data["password"]
        user = authenticate(request, username=email, password=password)
        if user is None:
            form.add_error(None, "Identifiants invalides.")
        else:
            login(request, user)
            messages.success(request, "Connexion reussie.")
            return redirect("accounts:home")

    return render(request, "accounts/login.html", {"form": form})


@require_http_methods(["POST"])
def logout_view(request):
    logout(request)
    messages.info(request, "Vous etes deconnecte.")
    return redirect("accounts:login")


@login_required
@require_http_methods(["POST"])
def post_action_view(request, post_id, action):
    post = get_object_or_404(Post, id=post_id)

    if action == "like":
        like, created = PostLike.objects.get_or_create(post=post, user=request.user)
        if not created:
            like.delete()
    elif action == "repost":
        repost, created = PostRepost.objects.get_or_create(post=post, user=request.user)
        if not created:
            repost.delete()
    elif action == "report":
        _, created = PostReport.objects.get_or_create(post=post, reporter=request.user)
        if created:
            messages.info(request, "Publication signalee.")
        else:
            messages.info(request, "Publication deja signalee.")
    else:
        messages.error(request, "Action non supportee.")

    next_url = request.POST.get("next") or reverse("accounts:home")
    if not url_has_allowed_host_and_scheme(
        url=next_url, allowed_hosts={request.get_host()}
    ):
        next_url = reverse("accounts:home")
    return redirect(next_url)
