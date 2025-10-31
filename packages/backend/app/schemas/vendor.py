"""Schemas for vendor plugin management."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VendorPluginInfo(BaseModel):
    """Information about a vendor plugin."""

    name: str = Field(..., description="Plugin name")
    provider: str = Field(..., description="Provider name")
    description: str = Field(..., description="Plugin description")
    version: str = Field(..., description="Plugin version")
    priority: int = Field(..., description="Default priority")
    capabilities: List[str] = Field(..., description="List of supported capabilities")
    rate_limits: Dict[str, Optional[int]] = Field(..., description="Rate limit information")
    is_active: bool = Field(default=True, description="Whether plugin is active")


class VendorPluginList(BaseModel):
    """List of vendor plugins."""

    plugins: List[VendorPluginInfo]
    count: int


class VendorConfigUpdate(BaseModel):
    """Request to update vendor configuration."""

    config: Dict[str, Any] = Field(..., description="Vendor configuration")


class VendorConfigResponse(BaseModel):
    """Response with vendor configuration."""

    vendor_name: str
    config: Dict[str, Any]


class RoutingConfigUpdate(BaseModel):
    """Request to update routing configuration."""

    method: str = Field(..., description="Method name")
    vendors: List[str] = Field(..., description="Vendor priority list")


class RoutingConfigResponse(BaseModel):
    """Response with routing configuration."""

    method: str
    vendors: List[str]


class AllRoutingConfigResponse(BaseModel):
    """Response with all routing configuration."""

    routing: Dict[str, List[str]]


class ConfigReloadResponse(BaseModel):
    """Response for configuration reload."""

    success: bool
    message: str
    last_reload: Optional[datetime] = None


class VendorCapabilitiesResponse(BaseModel):
    """Response with vendors supporting a capability."""

    capability: str
    vendors: List[str]
