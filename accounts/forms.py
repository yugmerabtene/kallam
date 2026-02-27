from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import extract_youtube_video_id

User = get_user_model()


class RegisterForm(forms.Form):
    first_name = forms.CharField(
        max_length=150,
        label="Prenom",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Ton prenom",
                "autocomplete": "given-name",
                "class": "form-input",
            }
        ),
    )
    last_name = forms.CharField(
        max_length=150,
        label="Nom",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Ton nom",
                "autocomplete": "family-name",
                "class": "form-input",
            }
        ),
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "exemple@email.com",
                "autocomplete": "email",
                "class": "form-input",
            }
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Mot de passe",
                "autocomplete": "new-password",
                "class": "form-input",
            }
        ),
        label="Mot de passe",
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Confirme le mot de passe",
                "autocomplete": "new-password",
                "class": "form-input",
            }
        ),
        label="Confirmer le mot de passe",
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Cet email est deja utilise.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", "Les mots de passe ne correspondent pas.")

        if password:
            try:
                validate_password(password)
            except ValidationError as exc:
                self.add_error("password", exc)

        return cleaned_data

    def save(self):
        email = self.cleaned_data["email"]
        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=self.cleaned_data["first_name"].strip(),
            last_name=self.cleaned_data["last_name"].strip(),
            password=self.cleaned_data["password"],
        )
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "exemple@email.com",
                "autocomplete": "email",
                "class": "form-input",
            }
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Mot de passe",
                "autocomplete": "current-password",
                "class": "form-input",
            }
        ),
        label="Mot de passe",
    )


class PostForm(forms.Form):
    content = forms.CharField(
        max_length=280,
        label="Message",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-input composer-input",
                "placeholder": "Quoi de neuf ?",
                "rows": 3,
                "maxlength": 280,
            }
        ),
    )
    image = forms.ImageField(
        required=False,
        label="Image",
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-input form-file-input",
                "accept": "image/*",
            }
        ),
    )
    youtube_url = forms.URLField(
        required=False,
        label="Lien YouTube",
        widget=forms.URLInput(
            attrs={
                "class": "form-input",
                "placeholder": "https://www.youtube.com/watch?v=...",
            }
        ),
    )

    def clean_content(self):
        return (self.cleaned_data.get("content") or "").strip()

    def clean(self):
        cleaned_data = super().clean()
        content = (cleaned_data.get("content") or "").strip()
        image = cleaned_data.get("image")
        youtube_url = (cleaned_data.get("youtube_url") or "").strip()

        if youtube_url and not extract_youtube_video_id(youtube_url):
            self.add_error("youtube_url", "Ajoute un lien YouTube valide.")

        if not content and not image and not youtube_url:
            raise ValidationError("Ajoute un message, une image ou un lien YouTube.")

        cleaned_data["content"] = content
        cleaned_data["youtube_url"] = youtube_url
        return cleaned_data
