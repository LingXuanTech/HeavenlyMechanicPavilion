"""
推送通知配置与日志 API

所有端点需 JWT 认证，按 user_id + channel 唯一约束管理配置。
"""
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select, col

from api.dependencies import get_current_user
from db.models import User, NotificationConfig, NotificationLog, get_session
from services.notification_service import notification_service

logger = structlog.get_logger()

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ============ 请求/响应模型 ============


class NotificationConfigRequest(BaseModel):
    channel: str = "telegram"
    channel_user_id: Optional[str] = None
    is_enabled: bool = True
    signal_threshold: str = "STRONG_BUY"  # STRONG_BUY | BUY | ALL
    quiet_hours_start: Optional[int] = None  # 0-23
    quiet_hours_end: Optional[int] = None    # 0-23


class NotificationConfigResponse(BaseModel):
    id: int
    channel: str
    channel_user_id: Optional[str]
    is_enabled: bool
    signal_threshold: str
    quiet_hours_start: Optional[int]
    quiet_hours_end: Optional[int]
    created_at: datetime
    updated_at: datetime


class NotificationLogResponse(BaseModel):
    id: int
    channel: str
    title: str
    body: str
    signal: Optional[str]
    symbol: Optional[str]
    sent_at: datetime
    delivered: bool
    error: Optional[str]


class TestNotificationRequest(BaseModel):
    channel: str = "telegram"
    channel_user_id: str


# ============ 路由 ============


@router.get("/config", response_model=list[NotificationConfigResponse])
async def get_notification_configs(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """获取当前用户的所有通知配置"""
    configs = session.exec(
        select(NotificationConfig).where(NotificationConfig.user_id == current_user.id)
    ).all()
    return configs


@router.put("/config", response_model=NotificationConfigResponse)
async def upsert_notification_config(
    body: NotificationConfigRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """创建或更新通知配置（按 user_id + channel 唯一）"""
    existing = session.exec(
        select(NotificationConfig).where(
            NotificationConfig.user_id == current_user.id,
            NotificationConfig.channel == body.channel,
        )
    ).first()

    if existing:
        existing.channel_user_id = body.channel_user_id
        existing.is_enabled = body.is_enabled
        existing.signal_threshold = body.signal_threshold
        existing.quiet_hours_start = body.quiet_hours_start
        existing.quiet_hours_end = body.quiet_hours_end
        existing.updated_at = datetime.now()
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    config = NotificationConfig(
        user_id=current_user.id,
        channel=body.channel,
        channel_user_id=body.channel_user_id,
        is_enabled=body.is_enabled,
        signal_threshold=body.signal_threshold,
        quiet_hours_start=body.quiet_hours_start,
        quiet_hours_end=body.quiet_hours_end,
    )
    session.add(config)
    session.commit()
    session.refresh(config)
    return config


@router.delete("/config/{channel}")
async def delete_notification_config(
    channel: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """删除指定渠道的通知配置"""
    config = session.exec(
        select(NotificationConfig).where(
            NotificationConfig.user_id == current_user.id,
            NotificationConfig.channel == channel,
        )
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    session.delete(config)
    session.commit()
    return {"ok": True}


@router.get("/logs", response_model=list[NotificationLogResponse])
async def get_notification_logs(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """获取当前用户的通知发送日志"""
    logs = session.exec(
        select(NotificationLog)
        .where(NotificationLog.user_id == current_user.id)
        .order_by(col(NotificationLog.sent_at).desc())
        .limit(limit)
    ).all()
    return logs


@router.post("/test")
async def send_test_notification(
    body: TestNotificationRequest,
    current_user: User = Depends(get_current_user),
):
    """发送测试通知"""
    delivered = await notification_service.send_test(
        user_id=current_user.id,
        channel=body.channel,
        channel_user_id=body.channel_user_id,
    )

    if not delivered:
        raise HTTPException(
            status_code=502,
            detail="Failed to deliver test notification. Check bot token and chat ID.",
        )

    return {"ok": True, "message": "测试通知已发送"}
