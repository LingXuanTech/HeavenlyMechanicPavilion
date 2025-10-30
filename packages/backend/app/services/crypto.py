"""Utility helpers for encrypting and decrypting sensitive values."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from ..config.settings import Settings


class EncryptionError(RuntimeError):
    """Raised when encryption or decryption fails."""


@lru_cache
def _get_fernet() -> Fernet:
    """Create a Fernet instance using application settings."""
    settings = Settings()
    key = settings.encryption_key
    if not key:
        raise EncryptionError(
            "APP_ENCRYPTION_KEY is not configured. Cannot encrypt secrets."
        )
    if isinstance(key, str):
        key_bytes = key.encode()
    else:
        key_bytes = key
    try:
        return Fernet(key_bytes)
    except Exception as exc:  # pragma: no cover - defensive
        raise EncryptionError("Invalid encryption key configuration") from exc


def encrypt_secret(value: Optional[str]) -> Optional[str]:
    """Encrypt a secret value using Fernet.

    Args:
        value: Plain text string to encrypt

    Returns:
        The encrypted token as a UTF-8 string, or None if value is None.
    """
    if value is None:
        return None
    token = _get_fernet().encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_secret(token: Optional[str]) -> Optional[str]:
    """Decrypt a previously encrypted secret token.

    Args:
        token: Encrypted token string

    Returns:
        Decrypted plain text string or None if token is None.
    """
    if token is None:
        return None
    try:
        value = _get_fernet().decrypt(token.encode("utf-8"))
        return value.decode("utf-8")
    except InvalidToken as exc:
        raise EncryptionError("Failed to decrypt secret; invalid token") from exc
