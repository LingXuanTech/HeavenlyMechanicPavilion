"""Pydantic models describing health endpoints."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel


class HealthStatus(BaseModel):
    """Health check payload."""

    status: Literal["ok", "degraded", "error"]
    details: Dict[str, Any]


class FeatureCheckStatus(BaseModel):
    """Represents the outcome of a single feature completeness check."""

    name: str
    description: str
    passed: bool
    detail: Optional[str] = None


class FeatureChecklist(BaseModel):
    """Aggregated response for feature completeness checks."""

    status: Literal["complete", "incomplete"]
    passed: int
    failed: int
    total: int
    checks: List[FeatureCheckStatus]
