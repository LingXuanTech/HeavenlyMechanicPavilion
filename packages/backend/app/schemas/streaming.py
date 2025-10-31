"""Schemas for real-time data streaming."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DataType(str, Enum):
    """Types of real-time data."""

    MARKET_DATA = "market_data"
    NEWS = "news"
    FUNDAMENTALS = "fundamentals"
    ANALYTICS = "analytics"
    INSIDER_DATA = "insider_data"


class UpdateType(str, Enum):
    """Types of data updates."""

    SNAPSHOT = "snapshot"
    DELTA = "delta"


class StreamMessage(BaseModel):
    """Real-time stream message."""

    channel: str
    data_type: DataType
    update_type: UpdateType
    timestamp: datetime
    symbol: Optional[str] = None
    data: Dict[str, Any]
    vendor: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InstrumentConfig(BaseModel):
    """Configuration for a tracked instrument."""

    symbol: str
    data_types: List[DataType] = Field(
        default=[DataType.MARKET_DATA], description="Types of data to track for this symbol"
    )
    enabled: bool = Field(default=True, description="Whether tracking is enabled")
    custom_config: Dict[str, Any] = Field(
        default_factory=dict, description="Custom configuration per symbol"
    )


class RefreshCadence(BaseModel):
    """Refresh cadence configuration for a data type."""

    data_type: DataType
    interval_seconds: int = Field(ge=1, description="Polling interval in seconds")
    enabled: bool = Field(default=True, description="Whether polling is enabled")
    retry_attempts: int = Field(default=3, ge=0, description="Number of retry attempts")
    retry_backoff_multiplier: float = Field(
        default=2.0, ge=1.0, description="Backoff multiplier for retries"
    )
    vendor_fallback: bool = Field(default=True, description="Enable vendor fallback on failure")


class StreamingConfig(BaseModel):
    """Complete streaming configuration."""

    instruments: List[InstrumentConfig]
    cadences: List[RefreshCadence]
    global_enabled: bool = Field(default=True, description="Global streaming toggle")
    max_retries: int = Field(default=3, description="Global max retries")
    cache_ttl_seconds: int = Field(default=300, description="Default cache TTL")


class WorkerStatus(BaseModel):
    """Status of a background worker."""

    worker_id: str
    data_type: DataType
    status: str  # running, stopped, error
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    success_count: int = 0
    error_count: int = 0
    current_vendor: Optional[str] = None
    last_error: Optional[str] = None


class StreamSubscription(BaseModel):
    """Client subscription to a stream."""

    channels: List[str] = Field(description="Redis channels to subscribe to")
    data_types: Optional[List[DataType]] = Field(default=None, description="Filter by data types")
    symbols: Optional[List[str]] = Field(default=None, description="Filter by symbols")


class TelemetryRecord(BaseModel):
    """Telemetry record for vendor operations."""

    vendor: str
    data_type: DataType
    symbol: Optional[str]
    timestamp: datetime
    success: bool
    latency_ms: float
    error: Optional[str] = None
    retry_count: int = 0
    fallback_used: bool = False
