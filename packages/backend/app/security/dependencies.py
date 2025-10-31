"""FastAPI dependencies for authentication and authorization."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..db.models import APIKey, User, UserRole
from ..db.session import get_session
from .auth import decode_token, verify_api_key

security_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    db: AsyncSession = Depends(get_session),
) -> Optional[User]:
    """Get current user from JWT token.

    Args:
        credentials: HTTP bearer credentials
        db: Database session

    Returns:
        User if authenticated, None otherwise
    """
    if not credentials:
        return None

    token = credentials.credentials
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        return None

    username: str = payload.get("sub")
    if username is None:
        return None

    statement = select(User).where(User.username == username, User.is_active.is_(True))
    result = await db.execute(statement)
    user = result.scalar_one_or_none()

    return user


async def get_current_user_from_api_key(
    api_key: Optional[str] = Security(api_key_header),
    db: AsyncSession = Depends(get_session),
) -> Optional[User]:
    """Get current user from API key.

    Args:
        api_key: API key from header
        db: Database session

    Returns:
        User if authenticated, None otherwise
    """
    if not api_key:
        return None

    statement = select(APIKey).where(APIKey.is_active.is_(True))
    result = await db.execute(statement)
    api_keys = result.scalars().all()

    for key_record in api_keys:
        if verify_api_key(api_key, key_record.key):
            if key_record.expires_at and key_record.expires_at < datetime.utcnow():
                continue

            key_record.last_used_at = datetime.utcnow()
            db.add(key_record)
            await db.commit()

            user_statement = select(User).where(User.id == key_record.user_id)
            user_result = await db.execute(user_statement)
            return user_result.scalar_one_or_none()

    return None


async def get_current_user(
    token_user: Optional[User] = Depends(get_current_user_from_token),
    api_key_user: Optional[User] = Depends(get_current_user_from_api_key),
) -> User:
    """Get current authenticated user from either token or API key.

    Args:
        token_user: User from JWT token
        api_key_user: User from API key

    Returns:
        Authenticated user

    Raises:
        HTTPException: If no valid authentication provided
    """
    user = token_user or api_key_user

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user.

    Args:
        current_user: Current authenticated user

    Returns:
        Active user

    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


class RoleChecker:
    """Dependency class to check user roles."""

    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        """Check if user has required role.

        Args:
            current_user: Current authenticated user

        Returns:
            User if authorized

        Raises:
            HTTPException: If user doesn't have required role
        """
        if current_user.role not in self.allowed_roles and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user


def require_role(*roles: UserRole):
    """Create a role checker dependency.

    Args:
        *roles: Required roles

    Returns:
        RoleChecker dependency
    """
    return RoleChecker(list(roles))


async def get_optional_user(
    token_user: Optional[User] = Depends(get_current_user_from_token),
    api_key_user: Optional[User] = Depends(get_current_user_from_api_key),
) -> Optional[User]:
    """Get current user if authenticated, otherwise None.

    Args:
        token_user: User from JWT token
        api_key_user: User from API key

    Returns:
        User if authenticated, None otherwise
    """
    return token_user or api_key_user
