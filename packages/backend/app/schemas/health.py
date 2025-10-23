"""Pydantic models describing health endpoints."""

from typing import Any, Dict, Literal

from pydantic import BaseModel


class HealthStatus(BaseModel):
    """Health check payload."""

    status: Literal["ok", "degraded", "error"]
    details: Dict[str, Any]
