"""API Key model for service-to-service authentication."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, SQLModel

if TYPE_CHECKING:
    pass


class APIKey(SQLModel, table=True):
    """API Key model for service-to-service authentication.

    Attributes:
        id: Primary key
        key: Unique API key (hashed)
        name: Descriptive name for the key
        user_id: Foreign key to user
        is_active: Whether the key is active
        created_at: Timestamp when key was created
        expires_at: Optional expiration timestamp
        last_used_at: Timestamp of last use
    """

    __tablename__ = "api_keys"

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(unique=True, index=True, max_length=255)
    name: str = Field(max_length=255)
    user_id: int = Field(foreign_key="users.id")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(default=None)
    last_used_at: Optional[datetime] = Field(default=None)

    # Relationships
    # Commented out to avoid SQLAlchemy 2.0 relationship resolution issues
    # user: "User" = Relationship(back_populates="api_keys")
