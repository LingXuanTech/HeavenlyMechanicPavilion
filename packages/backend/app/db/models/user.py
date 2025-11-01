"""User model for authentication."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, SQLModel

if TYPE_CHECKING:
    pass


class UserRole(str, Enum):
    """User roles for RBAC."""

    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"


class User(SQLModel, table=True):
    """User model for authentication and authorization.

    Attributes:
        id: Primary key
        username: Unique username
        email: Unique email address
        hashed_password: Bcrypt hashed password
        full_name: Optional full name
        role: User role (admin, trader, viewer)
        is_active: Whether the user is active
        is_superuser: Whether the user has superuser privileges
        created_at: Timestamp when user was created
        updated_at: Timestamp when user was last updated
        last_login_at: Timestamp of last successful login
    """

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=50)
    email: str = Field(unique=True, index=True, max_length=255)
    hashed_password: str = Field(max_length=255)
    full_name: Optional[str] = Field(default=None, max_length=255)
    role: UserRole = Field(default=UserRole.VIEWER)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = Field(default=None)

    # Relationships - using lowercase list for SQLModel compatibility
    # These will be populated automatically by SQLModel
    # api_keys: list["APIKey"] = Relationship(back_populates="user")
    # audit_logs: list["AuditLog"] = Relationship(back_populates="user")
