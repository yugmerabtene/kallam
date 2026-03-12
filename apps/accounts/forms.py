import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import UserProfile

User = get_user_model()

PSEUDO_RE = re.compile(r"^[a-z0-9_]{3,50}$")
RESERVED_PSEUDOS = {"modifier", "profil", "admin", "kallam", "system"}


class RegisterForm(forms.Form):
    pseudo = forms.CharField(
        max_length=50,
        label="Pseudonyme",
        widget=forms.TextInput(
            attrs={
                "placeholder": "tonpseudo",
                "autocomplete": "username",
                "class": "form-input",
            }
        ),
        help_text="3-50 caractères : lettres minuscules, chiffres, _",
    )
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
    cgu_accepted = forms.BooleanField(
        required=True,
        label="J'ai lu et j'accepte les Conditions Générales d'Utilisation",
        error_messages={"required": "Tu dois accepter les CGU pour créer un compte."},
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )

    def clean_pseudo(self):
        pseudo = self.cleaned_data.get("pseudo", "").strip().lower()
        if not PSEUDO_RE.match(pseudo):
            raise ValidationError(
                "Le pseudonyme doit contenir 3-50 caractères (lettres minuscules, chiffres, _)."
            )
        if pseudo in RESERVED_PSEUDOS:
            raise ValidationError("Ce pseudonyme est réservé.")
        if UserProfile.objects.filter(pseudo=pseudo).exists():
            raise ValidationError("Ce pseudonyme est déjà utilisé.")
        return pseudo

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
        UserProfile.objects.create(user=user, pseudo=self.cleaned_data["pseudo"])
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


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["pseudo", "bio", "avatar", "langue"]
        widgets = {
            "pseudo": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "tonpseudo"}
            ),
            "bio": forms.Textarea(
                attrs={"class": "form-input", "rows": 3, "maxlength": 160}
            ),
            "avatar": forms.ClearableFileInput(
                attrs={"class": "form-input form-file-input", "accept": "image/*"}
            ),
            "langue": forms.Select(attrs={"class": "form-input"}),
        }

    def clean_pseudo(self):
        pseudo = self.cleaned_data.get("pseudo", "").strip().lower()
        if not PSEUDO_RE.match(pseudo):
            raise ValidationError(
                "Le pseudonyme doit contenir 3-50 caractères (lettres minuscules, chiffres, _)."
            )
        if pseudo in RESERVED_PSEUDOS:
            raise ValidationError("Ce pseudonyme est réservé.")
        qs = UserProfile.objects.filter(pseudo=pseudo)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Ce pseudonyme est déjà utilisé.")
        return pseudo
