from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import LoginForm, RegisterForm


@login_required
def home_view(request):
    return render(request, "accounts/home.html")


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
