"""Audit log model for tracking sensitive operations."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .user import User


class AuditLog(SQLModel, table=True):
    """Audit log for tracking sensitive operations.

    Attributes:
        id: Primary key
        user_id: Foreign key to user (nullable for system operations)
        action: Action performed (e.g., login, api_key_created, config_updated)
        resource_type: Type of resource accessed (e.g., vendor, agent, user)
        resource_id: ID of the resource (optional)
        details: Additional details as JSON string
        ip_address: IP address of the request
        user_agent: User agent string
        status: Status of the action (success, failure)
        created_at: Timestamp when log was created
    """

    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    action: str = Field(index=True, max_length=100)
    resource_type: Optional[str] = Field(default=None, max_length=100)
    resource_id: Optional[str] = Field(default=None, max_length=255)
    details: Optional[str] = Field(default=None)
    ip_address: Optional[str] = Field(default=None, max_length=50)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    status: str = Field(default="success", max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Relationships
    user: Optional["User"] = Relationship(back_populates="audit_logs")
