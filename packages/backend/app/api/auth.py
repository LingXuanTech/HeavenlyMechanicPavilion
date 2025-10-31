"""Authentication API endpoints."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..db.models import APIKey, AuditLog, User, UserRole
from ..db.session import get_session
from ..schemas.auth import (
    APIKeyCreate,
    APIKeyResponse,
    AuditLogResponse,
    PasswordChange,
    Token,
    TokenRefresh,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from ..security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    get_current_active_user,
    hash_api_key,
    hash_password,
    require_role,
    verify_password,
)
from ..security.rate_limit import check_ip_rate_limit, check_user_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])


async def log_audit(
    db: AsyncSession,
    action: str,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    status_val: str = "success",
):
    """Log an audit entry.

    Args:
        db: Database session
        action: Action performed
        user_id: User ID
        resource_type: Resource type
        resource_id: Resource ID
        details: Additional details
        ip_address: IP address
        user_agent: User agent
        status_val: Status
    """
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        status=status_val,
    )
    db.add(audit_log)
    await db.commit()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """Register a new user.

    Args:
        user_data: User registration data
        request: FastAPI request
        db: Database session

    Returns:
        Created user

    Raises:
        HTTPException: If username or email already exists
    """
    ip_address = request.client.host if request.client else None
    await check_ip_rate_limit(ip_address, request)

    statement = select(User).where(
        (User.username == user_data.username) | (User.email == user_data.email)
    )
    result = await db.execute(statement)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        await log_audit(
            db,
            action="register_failed",
            details=f"Username or email already exists: {user_data.username}",
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent"),
            status_val="failure",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered",
        )

    user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hash_password(user_data.password),
        role=user_data.role,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    await log_audit(
        db,
        action="user_registered",
        user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent"),
    )

    logger.info(f"User registered: {user.username}")
    return user


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """Login user and return JWT tokens.

    Args:
        credentials: User credentials
        request: FastAPI request
        db: Database session

    Returns:
        JWT access and refresh tokens

    Raises:
        HTTPException: If credentials are invalid
    """
    ip_address = request.client.host if request.client else None
    await check_ip_rate_limit(ip_address, request)

    statement = select(User).where(User.username == credentials.username)
    result = await db.execute(statement)
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        await log_audit(
            db,
            action="login_failed",
            details=f"Invalid credentials for user: {credentials.username}",
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent"),
            status_val="failure",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        await log_audit(
            db,
            action="login_failed",
            user_id=user.id,
            details=f"Inactive user login attempt: {credentials.username}",
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent"),
            status_val="failure",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    user.last_login_at = datetime.utcnow()
    db.add(user)
    await db.commit()

    access_token = create_access_token(data={"sub": user.username, "role": user.role.value})
    refresh_token = create_refresh_token(data={"sub": user.username})

    await log_audit(
        db,
        action="user_login",
        user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent"),
    )

    logger.info(f"User logged in: {user.username}")
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """Refresh access token using refresh token.

    Args:
        token_data: Refresh token
        request: FastAPI request
        db: Database session

    Returns:
        New access and refresh tokens

    Raises:
        HTTPException: If refresh token is invalid
    """
    payload = decode_token(token_data.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    statement = select(User).where(User.username == username, User.is_active.is_(True))
    result = await db.execute(statement)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    access_token = create_access_token(data={"sub": user.username, "role": user.role.value})
    refresh_token = create_refresh_token(data={"sub": user.username})

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
):
    """Get current user information.

    Args:
        current_user: Current authenticated user

    Returns:
        User information
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
):
    """Update current user information.

    Args:
        user_data: User update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated user
    """
    if user_data.email is not None:
        current_user.email = user_data.email
    if user_data.full_name is not None:
        current_user.full_name = user_data.full_name

    current_user.updated_at = datetime.utcnow()
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    return current_user


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
):
    """Change user password.

    Args:
        password_data: Password change data
        request: FastAPI request
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If old password is incorrect
    """
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password",
        )

    current_user.hashed_password = hash_password(password_data.new_password)
    current_user.updated_at = datetime.utcnow()
    db.add(current_user)
    await db.commit()

    ip_address = request.client.host if request.client else None
    await log_audit(
        db,
        action="password_changed",
        user_id=current_user.id,
        resource_type="user",
        resource_id=str(current_user.id),
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent"),
    )

    return {"message": "Password changed successfully"}


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    """List all users (admin only).

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of users
    """
    statement = select(User)
    result = await db.execute(statement)
    users = result.scalars().all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    """Get user by ID (admin only).

    Args:
        user_id: User ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        User

    Raises:
        HTTPException: If user not found
    """
    statement = select(User).where(User.id == user_id)
    result = await db.execute(statement)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    request: Request,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    """Update user (admin only).

    Args:
        user_id: User ID
        user_data: User update data
        request: FastAPI request
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated user

    Raises:
        HTTPException: If user not found
    """
    statement = select(User).where(User.id == user_id)
    result = await db.execute(statement)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user_data.email is not None:
        user.email = user_data.email
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    user.updated_at = datetime.utcnow()
    db.add(user)
    await db.commit()
    await db.refresh(user)

    ip_address = request.client.host if request.client else None
    await log_audit(
        db,
        action="user_updated",
        user_id=current_user.id,
        resource_type="user",
        resource_id=str(user.id),
        details=f"Updated by admin: {current_user.username}",
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent"),
    )

    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    """Delete user (admin only).

    Args:
        user_id: User ID
        request: FastAPI request
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If user not found or trying to delete self
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    statement = select(User).where(User.id == user_id)
    result = await db.execute(statement)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await db.delete(user)
    await db.commit()

    ip_address = request.client.host if request.client else None
    await log_audit(
        db,
        action="user_deleted",
        user_id=current_user.id,
        resource_type="user",
        resource_id=str(user_id),
        details=f"Deleted by admin: {current_user.username}",
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent"),
    )

    return {"message": "User deleted successfully"}


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    key_data: APIKeyCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
):
    """Create a new API key.

    Args:
        key_data: API key data
        request: FastAPI request
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created API key (with plain key only on creation)
    """
    await check_user_rate_limit(current_user.id, request)

    plain_key = generate_api_key()
    hashed_key = hash_api_key(plain_key)

    api_key = APIKey(
        key=hashed_key,
        name=key_data.name,
        user_id=current_user.id,
        expires_at=key_data.expires_at,
    )

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    ip_address = request.client.host if request.client else None
    await log_audit(
        db,
        action="api_key_created",
        user_id=current_user.id,
        resource_type="api_key",
        resource_id=str(api_key.id),
        details=f"API key name: {key_data.name}",
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent"),
    )

    response = APIKeyResponse.model_validate(api_key)
    response.key = plain_key
    return response


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
):
    """List user's API keys.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of API keys (without plain keys)
    """
    statement = select(APIKey).where(APIKey.user_id == current_user.id)
    result = await db.execute(statement)
    api_keys = result.scalars().all()
    return api_keys


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
):
    """Revoke an API key.

    Args:
        key_id: API key ID
        request: FastAPI request
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If key not found or not owned by user
    """
    statement = select(APIKey).where(APIKey.id == key_id, APIKey.user_id == current_user.id)
    result = await db.execute(statement)
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    await db.delete(api_key)
    await db.commit()

    ip_address = request.client.host if request.client else None
    await log_audit(
        db,
        action="api_key_revoked",
        user_id=current_user.id,
        resource_type="api_key",
        resource_id=str(key_id),
        details=f"API key name: {api_key.name}",
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent"),
    )

    return {"message": "API key revoked successfully"}


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def list_audit_logs(
    limit: int = 100,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    """List audit logs (admin only).

    Args:
        limit: Maximum number of logs to return
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of audit logs
    """
    statement = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    result = await db.execute(statement)
    logs = result.scalars().all()
    return logs


@router.get("/audit-logs/me", response_model=list[AuditLogResponse])
async def list_my_audit_logs(
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
):
    """List current user's audit logs.

    Args:
        limit: Maximum number of logs to return
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of audit logs
    """
    statement = (
        select(AuditLog)
        .where(AuditLog.user_id == current_user.id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(statement)
    logs = result.scalars().all()
    return logs
