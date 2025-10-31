"""Unit tests for encryption utilities."""

from __future__ import annotations

import os
from unittest.mock import patch

from app.security.encryption import decrypt_api_key, encrypt_api_key


class TestEncryption:
    """Tests for encryption utilities."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encryption and decryption are reversible."""
        api_key = "sk-test-1234567890"

        encrypted = encrypt_api_key(api_key)
        assert encrypted != api_key

        decrypted = decrypt_api_key(encrypted)
        assert decrypted == api_key

    def test_encrypt_empty_string(self):
        """Test encrypting empty string."""
        encrypted = encrypt_api_key("")
        assert encrypted == ""

    def test_decrypt_empty_string(self):
        """Test decrypting empty string."""
        decrypted = decrypt_api_key("")
        assert decrypted is None

    def test_decrypt_invalid_data(self):
        """Test decrypting invalid data returns None."""
        decrypted = decrypt_api_key("invalid-encrypted-data")
        assert decrypted is None

    def test_encryption_with_custom_key(self):
        """Test encryption with custom key from environment."""
        with patch.dict(os.environ, {"ENCRYPTION_KEY": "test-custom-key-12345"}):
            api_key = "sk-test-1234567890"
            encrypted = encrypt_api_key(api_key)
            decrypted = decrypt_api_key(encrypted)
            assert decrypted == api_key

    def test_different_keys_different_results(self):
        """Test that different keys produce different encrypted results."""
        api_key = "sk-test-1234567890"

        with patch.dict(os.environ, {"ENCRYPTION_KEY": "key1"}):
            encrypted1 = encrypt_api_key(api_key)

        with patch.dict(os.environ, {"ENCRYPTION_KEY": "key2"}):
            encrypted2 = encrypt_api_key(api_key)

        assert encrypted1 != encrypted2
