"""
Chiffrement symétrique des champs sensibles (Fernet / AES-128-CBC).

La clé est dérivée de DJANGO_SECRET_KEY si MESSAGE_ENCRYPTION_KEY n'est pas
défini explicitement. En production, fixer MESSAGE_ENCRYPTION_KEY dans les
variables d'environnement (valeur base64-urlsafe de 32 octets).
"""
import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db.models import TextField


def _get_fernet() -> Fernet:
    key = getattr(settings, "MESSAGE_ENCRYPTION_KEY", None)
    if not key:
        # Derive a stable 32-byte key from SECRET_KEY
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
    except (InvalidToken, Exception):
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
