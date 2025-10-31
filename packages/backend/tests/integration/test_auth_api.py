"""Integration tests for authentication API endpoints."""

import pytest
from httpx import AsyncClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.models import AuditLog, User, UserRole
from app.security.auth import hash_password


@pytest.mark.asyncio
async def test_register_user(async_client: AsyncClient, db_session: AsyncSession):
    """Test user registration."""
    response = await async_client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123",
            "full_name": "Test User",
            "role": "viewer",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert data["role"] == "viewer"
    assert data["is_active"] is True
    assert "id" in data

    statement = select(User).where(User.username == "testuser")
    result = await db_session.execute(statement)
    user = result.scalar_one_or_none()
    assert user is not None


@pytest.mark.asyncio
async def test_register_duplicate_user(async_client: AsyncClient, db_session: AsyncSession):
    """Test registering a duplicate user."""
    user_data = {
        "username": "duplicate",
        "email": "duplicate@example.com",
        "password": "password123",
        "role": "viewer",
    }

    response1 = await async_client.post("/auth/register", json=user_data)
    assert response1.status_code == 201

    response2 = await async_client.post("/auth/register", json=user_data)
    assert response2.status_code == 400
    assert "already registered" in response2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, db_session: AsyncSession):
    """Test successful login."""
    user = User(
        username="loginuser",
        email="login@example.com",
        hashed_password=hash_password("password123"),
        role=UserRole.TRADER,
    )
    db_session.add(user)
    await db_session.commit()

    response = await async_client.post(
        "/auth/login",
        json={"username": "loginuser", "password": "password123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client: AsyncClient, db_session: AsyncSession):
    """Test login with invalid credentials."""
    user = User(
        username="loginuser2",
        email="login2@example.com",
        hashed_password=hash_password("password123"),
        role=UserRole.VIEWER,
    )
    db_session.add(user)
    await db_session.commit()

    response = await async_client.post(
        "/auth/login",
        json={"username": "loginuser2", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_inactive_user(async_client: AsyncClient, db_session: AsyncSession):
    """Test login with inactive user."""
    user = User(
        username="inactive",
        email="inactive@example.com",
        hashed_password=hash_password("password123"),
        role=UserRole.VIEWER,
        is_active=False,
    )
    db_session.add(user)
    await db_session.commit()

    response = await async_client.post(
        "/auth/login",
        json={"username": "inactive", "password": "password123"},
    )

    assert response.status_code == 403
    assert "inactive" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_current_user(async_client: AsyncClient, db_session: AsyncSession):
    """Test getting current user info."""
    user = User(
        username="currentuser",
        email="current@example.com",
        hashed_password=hash_password("password123"),
        role=UserRole.TRADER,
    )
    db_session.add(user)
    await db_session.commit()

    login_response = await async_client.post(
        "/auth/login",
        json={"username": "currentuser", "password": "password123"},
    )
    token = login_response.json()["access_token"]

    response = await async_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "currentuser"
    assert data["email"] == "current@example.com"
    assert data["role"] == "trader"


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(async_client: AsyncClient):
    """Test getting current user without authentication."""
    response = await async_client.get("/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(async_client: AsyncClient, db_session: AsyncSession):
    """Test token refresh."""
    user = User(
        username="refreshuser",
        email="refresh@example.com",
        hashed_password=hash_password("password123"),
        role=UserRole.VIEWER,
    )
    db_session.add(user)
    await db_session.commit()

    login_response = await async_client.post(
        "/auth/login",
        json={"username": "refreshuser", "password": "password123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    response = await async_client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_change_password(async_client: AsyncClient, db_session: AsyncSession):
    """Test password change."""
    user = User(
        username="changepass",
        email="changepass@example.com",
        hashed_password=hash_password("oldpassword"),
        role=UserRole.VIEWER,
    )
    db_session.add(user)
    await db_session.commit()

    login_response = await async_client.post(
        "/auth/login",
        json={"username": "changepass", "password": "oldpassword"},
    )
    token = login_response.json()["access_token"]

    response = await async_client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"old_password": "oldpassword", "new_password": "newpassword123"},
    )

    assert response.status_code == 200

    login_response2 = await async_client.post(
        "/auth/login",
        json={"username": "changepass", "password": "newpassword123"},
    )
    assert login_response2.status_code == 200


@pytest.mark.asyncio
async def test_create_api_key(async_client: AsyncClient, db_session: AsyncSession):
    """Test API key creation."""
    user = User(
        username="apiuser",
        email="api@example.com",
        hashed_password=hash_password("password123"),
        role=UserRole.TRADER,
    )
    db_session.add(user)
    await db_session.commit()

    login_response = await async_client.post(
        "/auth/login",
        json={"username": "apiuser", "password": "password123"},
    )
    token = login_response.json()["access_token"]

    response = await async_client.post(
        "/auth/api-keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Test API Key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test API Key"
    assert "key" in data
    assert data["key"].startswith("ta_")


@pytest.mark.asyncio
async def test_list_api_keys(async_client: AsyncClient, db_session: AsyncSession):
    """Test listing API keys."""
    user = User(
        username="listkeys",
        email="listkeys@example.com",
        hashed_password=hash_password("password123"),
        role=UserRole.TRADER,
    )
    db_session.add(user)
    await db_session.commit()

    login_response = await async_client.post(
        "/auth/login",
        json={"username": "listkeys", "password": "password123"},
    )
    token = login_response.json()["access_token"]

    await async_client.post(
        "/auth/api-keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Key 1"},
    )

    await async_client.post(
        "/auth/api-keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Key 2"},
    )

    response = await async_client.get(
        "/auth/api-keys",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_admin_list_users(async_client: AsyncClient, db_session: AsyncSession):
    """Test admin listing users."""
    admin = User(
        username="admin",
        email="admin@example.com",
        hashed_password=hash_password("password123"),
        role=UserRole.ADMIN,
        is_superuser=True,
    )
    db_session.add(admin)
    await db_session.commit()

    login_response = await async_client.post(
        "/auth/login",
        json={"username": "admin", "password": "password123"},
    )
    token = login_response.json()["access_token"]

    response = await async_client.get(
        "/auth/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_non_admin_cannot_list_users(async_client: AsyncClient, db_session: AsyncSession):
    """Test non-admin cannot list users."""
    user = User(
        username="viewer",
        email="viewer@example.com",
        hashed_password=hash_password("password123"),
        role=UserRole.VIEWER,
    )
    db_session.add(user)
    await db_session.commit()

    login_response = await async_client.post(
        "/auth/login",
        json={"username": "viewer", "password": "password123"},
    )
    token = login_response.json()["access_token"]

    response = await async_client.get(
        "/auth/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_audit_log_creation(async_client: AsyncClient, db_session: AsyncSession):
    """Test that audit logs are created."""
    response = await async_client.post(
        "/auth/register",
        json={
            "username": "audituser",
            "email": "audit@example.com",
            "password": "password123",
            "role": "viewer",
        },
    )

    assert response.status_code == 201

    statement = select(AuditLog).where(AuditLog.action == "user_registered")
    result = await db_session.execute(statement)
    audit_log = result.scalar_one_or_none()
    assert audit_log is not None
    assert audit_log.resource_type == "user"
