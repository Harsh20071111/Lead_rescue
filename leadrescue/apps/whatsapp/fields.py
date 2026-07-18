import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _fernet():
    secret = getattr(settings, "FIELD_ENCRYPTION_KEY", "") or settings.SECRET_KEY
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


class EncryptedTextField(models.TextField):
    description = "Text encrypted at rest with Fernet"

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def to_python(self, value):
        if value in (None, ""):
            return value
        if not isinstance(value, str):
            value = str(value)
        try:
            return _fernet().decrypt(value.encode()).decode()
        except (InvalidToken, ValueError):
            return value

    def get_prep_value(self, value):
        if value in (None, ""):
            return value
        value = str(value)
        prefix = "gAAAAA"
        if value.startswith(prefix):
            return value
        return _fernet().encrypt(value.encode()).decode()

