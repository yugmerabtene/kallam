from django.conf import settings
from django.db import models


class TrustList(models.Model):
    """Liste de confiance : utilisateurs dont on veut voir le contenu en priorité."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trust_list"
    )
    trusted = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trusted_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "trusted"], name="unique_trust")
        ]


class SurveyQuestion(models.Model):
    """Question d'enquête communautaire."""
    text       = models.CharField(max_length=400)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:60]


class SurveyResponse(models.Model):
    """Réponse anonyme à une enquête — aucun lien avec un compte."""
    question   = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE, related_name="responses")
    answer     = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    # Volontairement sans FK utilisateur — anonyme RGPD-friendly


class CharterVersion(models.Model):
    """Version horodatée de la charte communautaire."""
    version      = models.CharField(max_length=20)   # ex: "1.0", "1.1"
    published_at = models.DateTimeField(auto_now_add=True)
    is_current   = models.BooleanField(default=True)

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return f"v{self.version}"

    @classmethod
    def current(cls):
        obj = cls.objects.filter(is_current=True).first()
        if not obj:
            obj = cls.objects.create(version="1.0")
        return obj
