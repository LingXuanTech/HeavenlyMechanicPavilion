"""Encryption utilities for sensitive data like API keys."""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from typing import Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


def _get_encryption_key() -> bytes:
    """Get or generate encryption key from environment.

    Returns:
        bytes: Encryption key

    Raises:
        ValueError: If encryption key cannot be obtained
    """
    # Get encryption key from environment or generate one
    key_str = os.getenv("ENCRYPTION_KEY")

    if key_str:
        # Ensure the key is properly formatted
        try:
            # If it's already a valid Fernet key, use it
            return key_str.encode()
        except Exception:
            # Otherwise, derive a key from the string
            key_hash = hashlib.sha256(key_str.encode()).digest()
            return base64.urlsafe_b64encode(key_hash)
    else:
        # Generate a deterministic key from a fallback
        # WARNING: This is not secure for production!
        # In production, always set ENCRYPTION_KEY environment variable
        logger.warning(
            "ENCRYPTION_KEY not set in environment. Using fallback key. "
            "This is NOT secure for production!"
        )
        fallback = "tradingagents-fallback-key-change-in-production"
        key_hash = hashlib.sha256(fallback.encode()).digest()
        return base64.urlsafe_b64encode(key_hash)


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key.

    Args:
        api_key: The API key to encrypt

    Returns:
        str: Base64-encoded encrypted API key
    """
    if not api_key:
        return ""

    try:
        key = _get_encryption_key()
        f = Fernet(key)
        encrypted = f.encrypt(api_key.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    except Exception as e:
        logger.error(f"Error encrypting API key: {e}")
        raise


def decrypt_api_key(encrypted_api_key: str) -> Optional[str]:
    """Decrypt an API key.

    Args:
        encrypted_api_key: The encrypted API key

    Returns:
        Optional[str]: The decrypted API key, or None if decryption fails
    """
    if not encrypted_api_key:
        return None

    try:
        key = _get_encryption_key()
        f = Fernet(key)
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_api_key.encode())
        decrypted = f.decrypt(encrypted_bytes)
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Error decrypting API key: {e}")
        return None
