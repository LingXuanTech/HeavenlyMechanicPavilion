"""
推送通知配置与日志 API

所有端点需 JWT 认证, 按 user_id + channel 唯一约束管理配置.
"""
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, col, func, select

from api.dependencies import get_current_user
from api.schemas.notification import (
    DeleteLogsResponse,
    NotificationConfigRequest,
    NotificationConfigResponse,
    NotificationLogResponse,
    NotificationLogsPageResponse,
    NotificationStatsResponse,
    OperationOkResponse,
    TestAllResponse,
    TestAllResultItem,
    TestNotificationRequest,
    TestNotificationResponse,
)
from db.models import NotificationConfig, NotificationLog, User, get_session
from services.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _validate_quiet_hours(body: NotificationConfigRequest) -> None:
    """静默时段需同时配置开始和结束, 或都不配置."""
    if (body.quiet_hours_start is None) ^ (body.quiet_hours_end is None):
        raise HTTPException(
            status_code=422,
            detail="quiet_hours_start and quiet_hours_end must be both set or both null",
        )


def _apply_log_filters(
    query,
    user_id: int,
    symbol: str | None,
    delivered: bool | None,
    sent_after: datetime | None,
    sent_before: datetime | None,
):
    query = query.where(NotificationLog.user_id == user_id)
    if symbol:
        query = query.where(NotificationLog.symbol == symbol)
    if delivered is not None:
        query = query.where(NotificationLog.delivered == delivered)
    if sent_after is not None:
        query = query.where(NotificationLog.sent_at >= sent_after)
    if sent_before is not None:
        query = query.where(NotificationLog.sent_at <= sent_before)
    return query


def _validate_log_time_range(sent_after: datetime | None, sent_before: datetime | None) -> None:
    if sent_after is not None and sent_before is not None and sent_after > sent_before:
        raise HTTPException(
            status_code=422,
            detail="sent_after must be earlier than or equal to sent_before",
        )


@router.get("/config", response_model=list[NotificationConfigResponse])
async def get_notification_configs(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """获取当前用户的所有通知配置"""
    configs = session.exec(
        select(NotificationConfig).where(NotificationConfig.user_id == current_user.id)
    ).all()
    return configs


@router.put("/config", response_model=NotificationConfigResponse)
async def upsert_notification_config(
    body: NotificationConfigRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """创建或更新通知配置 (按 user_id + channel 唯一)."""
    _validate_quiet_hours(body)

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


@router.delete("/config/{channel}", response_model=OperationOkResponse)
async def delete_notification_config(
    channel: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
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


@router.get("/logs", response_model=NotificationLogsPageResponse)
async def get_notification_logs(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    symbol: str | None = Query(default=None, min_length=1),
    delivered: bool | None = None,
    sent_after: datetime | None = None,
    sent_before: datetime | None = None,
):
    """获取当前用户的通知发送日志"""
    _validate_log_time_range(sent_after=sent_after, sent_before=sent_before)

    query = _apply_log_filters(
        select(NotificationLog),
        user_id=current_user.id,
        symbol=symbol,
        delivered=delivered,
        sent_after=sent_after,
        sent_before=sent_before,
    )
    count_query = _apply_log_filters(
        select(func.count()).select_from(NotificationLog),
        user_id=current_user.id,
        symbol=symbol,
        delivered=delivered,
        sent_after=sent_after,
        sent_before=sent_before,
    )
    total = int(session.exec(count_query).one())

    logs = session.exec(
        query.order_by(col(NotificationLog.sent_at).desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return NotificationLogsPageResponse(
        items=[NotificationLogResponse.model_validate(item) for item in logs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.delete("/logs", response_model=DeleteLogsResponse)
async def delete_notification_logs(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    symbol: str | None = Query(default=None, min_length=1),
    delivered: bool | None = None,
    sent_after: datetime | None = None,
    sent_before: datetime | None = None,
):
    """删除当前用户通知日志 (可按筛选条件删除)."""
    _validate_log_time_range(sent_after=sent_after, sent_before=sent_before)

    query = _apply_log_filters(
        select(NotificationLog),
        user_id=current_user.id,
        symbol=symbol,
        delivered=delivered,
        sent_after=sent_after,
        sent_before=sent_before,
    )
    logs = session.exec(query).all()
    for item in logs:
        session.delete(item)
    session.commit()

    return DeleteLogsResponse(ok=True, deleted=len(logs))


@router.get("/stats", response_model=NotificationStatsResponse)
async def get_notification_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """获取当前用户通知统计"""
    total_sent = int(
        session.exec(
            select(func.count())
            .select_from(NotificationLog)
            .where(
                NotificationLog.user_id == current_user.id,
                col(NotificationLog.delivered).is_(True),
            )
        ).one()
    )
    total_failed = int(
        session.exec(
            select(func.count())
            .select_from(NotificationLog)
            .where(
                NotificationLog.user_id == current_user.id,
                col(NotificationLog.delivered).is_(False),
            )
        ).one()
    )
    channels_count = int(
        session.exec(
            select(func.count())
            .select_from(NotificationConfig)
            .where(NotificationConfig.user_id == current_user.id)
        ).one()
    )
    enabled_channels_count = int(
        session.exec(
            select(func.count())
            .select_from(NotificationConfig)
            .where(
                NotificationConfig.user_id == current_user.id,
                col(NotificationConfig.is_enabled).is_(True),
            )
        ).one()
    )

    last_sent_at = session.exec(
        select(NotificationLog.sent_at)
        .where(NotificationLog.user_id == current_user.id)
        .order_by(col(NotificationLog.sent_at).desc())
        .limit(1)
    ).first()

    total = total_sent + total_failed
    success_rate = round((total_sent / total) * 100, 2) if total > 0 else 0.0

    return NotificationStatsResponse(
        total_sent=total_sent,
        total_failed=total_failed,
        success_rate=success_rate,
        channels_count=channels_count,
        enabled_channels_count=enabled_channels_count,
        last_sent_at=last_sent_at,
    )


@router.post("/test", response_model=TestNotificationResponse)
async def send_test_notification(
    body: TestNotificationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
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


@router.post("/test-all", response_model=TestAllResponse)
async def send_test_notification_all_configs(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """向当前用户所有启用配置发送测试通知"""
    configs = session.exec(
        select(NotificationConfig).where(
            NotificationConfig.user_id == current_user.id,
            col(NotificationConfig.is_enabled).is_(True),
            col(NotificationConfig.channel_user_id).is_not(None),
        )
    ).all()

    results: list[TestAllResultItem] = []
    delivered_count = 0

    for config in configs:
        delivered = await notification_service.send_test(
            user_id=current_user.id,
            channel=config.channel,
            channel_user_id=config.channel_user_id or "",
        )
        if delivered:
            delivered_count += 1
        results.append(
            TestAllResultItem(
                channel=config.channel,
                channel_user_id=config.channel_user_id or "",
                delivered=delivered,
            )
        )

    return TestAllResponse(
        total=len(results),
        delivered=delivered_count,
        results=results,
    )
