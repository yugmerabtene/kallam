"""
Chiffrement symétrique des champs sensibles (Fernet / AES-128-CBC).

En production, définir MESSAGE_ENCRYPTION_KEY dans les variables d'environnement
(valeur base64-urlsafe de 32 octets générée avec : python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

Si MESSAGE_ENCRYPTION_KEY est absent, la clé est dérivée de SECRET_KEY (fallback
dev uniquement). Un warning est émis pour alerter en production.
"""
import base64
import hashlib
import logging
import warnings

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db.models import TextField

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    key = getattr(settings, "MESSAGE_ENCRYPTION_KEY", None)
    if not key:
        if not getattr(settings, "DEBUG", True):
            warnings.warn(
                "MESSAGE_ENCRYPTION_KEY non défini en production. "
                "La clé est dérivée de SECRET_KEY — configurer MESSAGE_ENCRYPTION_KEY.",
                RuntimeWarning,
                stacklevel=2,
            )
        raw = settings.SECRET_KEY.encode("utf-8")
        derived = hashlib.sha256(raw).digest()
        key = base64.urlsafe_b64encode(derived)
    if isinstance(key, str):
        key = key.encode("utf-8")
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    if not plaintext:
        return plaintext
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(token: str) -> str:
    if not token:
        return token
    try:
        return _get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, ValueError):
        # Fallback: return as-is (covers unencrypted legacy data)
        return token


class EncryptedTextField(TextField):
    """TextField transparent : chiffre à l'écriture, déchiffre à la lecture."""

    def from_db_value(self, value, expression, connection):
        return decrypt(value) if value is not None else value

    def get_prep_value(self, value):
        return encrypt(value) if value is not None else value

    def to_python(self, value):
        return value
