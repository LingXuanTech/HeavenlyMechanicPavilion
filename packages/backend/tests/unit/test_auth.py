"""Unit tests for authentication functionality."""

from datetime import datetime, timedelta

from app.security.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_api_key,
    verify_password,
)


def test_hash_password():
    """Test password hashing."""
    password = "test_password_123"
    hashed = hash_password(password)

    assert hashed != password
    assert len(hashed) > 0
    assert hashed.startswith("$2b$")


def test_verify_password():
    """Test password verification."""
    password = "test_password_123"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_create_access_token():
    """Test JWT access token creation."""
    data = {"sub": "testuser", "role": "admin"}
    token = create_access_token(data)

    assert isinstance(token, str)
    assert len(token) > 0

    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "testuser"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_create_refresh_token():
    """Test JWT refresh token creation."""
    data = {"sub": "testuser"}
    token = create_refresh_token(data)

    assert isinstance(token, str)
    assert len(token) > 0

    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "testuser"
    assert payload["type"] == "refresh"
    assert "exp" in payload


def test_decode_token_invalid():
    """Test decoding invalid token."""
    invalid_token = "invalid.token.here"
    payload = decode_token(invalid_token)

    assert payload is None


def test_decode_token_expired():
    """Test decoding expired token."""
    data = {"sub": "testuser"}
    expired_delta = timedelta(seconds=-1)
    token = create_access_token(data, expires_delta=expired_delta)

    payload = decode_token(token)
    assert payload is None


def test_generate_api_key():
    """Test API key generation."""
    key1 = generate_api_key()
    key2 = generate_api_key()

    assert isinstance(key1, str)
    assert isinstance(key2, str)
    assert key1.startswith("ta_")
    assert key2.startswith("ta_")
    assert key1 != key2
    assert len(key1) > 40


def test_hash_api_key():
    """Test API key hashing."""
    api_key = generate_api_key()
    hashed = hash_api_key(api_key)

    assert hashed != api_key
    assert len(hashed) > 0
    assert hashed.startswith("$2b$")


def test_verify_api_key():
    """Test API key verification."""
    api_key = generate_api_key()
    hashed = hash_api_key(api_key)

    assert verify_api_key(api_key, hashed) is True
    assert verify_api_key("wrong_key", hashed) is False


def test_token_with_custom_expiration():
    """Test token creation with custom expiration."""
    data = {"sub": "testuser"}
    custom_delta = timedelta(minutes=5)
    token = create_access_token(data, expires_delta=custom_delta)

    payload = decode_token(token)
    assert payload is not None

    exp_timestamp = payload["exp"]
    exp_datetime = datetime.fromtimestamp(exp_timestamp)
    now = datetime.utcnow()

    time_diff = exp_datetime - now
    assert 4 <= time_diff.total_seconds() / 60 <= 6
