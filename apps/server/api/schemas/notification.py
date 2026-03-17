"""通知相关 Schema (基于 NotificationConfig / NotificationLog 模型)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NotificationConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: Literal["telegram"] = "telegram"
    channel_user_id: str | None = None
    is_enabled: bool = True
    signal_threshold: Literal["STRONG_BUY", "BUY", "ALL"] = "STRONG_BUY"
    quiet_hours_start: int | None = Field(default=None, ge=0, le=23)
    quiet_hours_end: int | None = Field(default=None, ge=0, le=23)


class NotificationConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel: str
    channel_user_id: str | None
    is_enabled: bool
    signal_threshold: str
    quiet_hours_start: int | None
    quiet_hours_end: int | None
    created_at: datetime
    updated_at: datetime

class NotificationLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel: str
    title: str
    body: str
    signal: str | None
    symbol: str | None
    sent_at: datetime
    delivered: bool
    error: str | None


class NotificationLogsPageResponse(BaseModel):
    items: list[NotificationLogResponse]
    total: int
    limit: int
    offset: int


class TestNotificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: Literal["telegram"] = "telegram"
    channel_user_id: str = Field(min_length=1)


class OperationOkResponse(BaseModel):
    ok: bool


class DeleteLogsResponse(OperationOkResponse):
    deleted: int


class TestNotificationResponse(OperationOkResponse):
    message: str


class TestAllResultItem(BaseModel):
    channel: str
    channel_user_id: str
    delivered: bool


class TestAllResponse(BaseModel):
    total: int
    delivered: int
    results: list[TestAllResultItem]


class NotificationStatsResponse(BaseModel):
    total_sent: int
    total_failed: int
    success_rate: float
    channels_count: int
    enabled_channels_count: int
    last_sent_at: datetime | None
