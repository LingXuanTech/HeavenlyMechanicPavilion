"""Market status and calendar API endpoints."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from ..db.models import User
from ..security.dependencies import get_current_active_user
from ..services.market_calendar import MarketCalendarService
from ..services.trading_session import TradingSessionService
from ..core.errors import ExternalServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["market"])

# Global trading session service
trading_session_service = TradingSessionService()


def get_market_calendar() -> MarketCalendarService:
    """Get market calendar service instance.
    
    Attempts to get the service from an active trading session's broker,
    otherwise returns None and endpoints will handle the error.
    
    Returns:
        MarketCalendarService instance or None
    """
    try:
        # Try to get from first active session
        if trading_session_service.active_sessions:
            first_session_id = next(iter(trading_session_service.active_sessions))
            execution_service = trading_session_service.get_execution_service(first_session_id)
            if execution_service and hasattr(execution_service.broker, 'market_calendar'):
                return execution_service.broker.market_calendar
    except Exception as e:
        logger.warning(f"Unable to get market calendar from active sessions: {e}")
    
    return None


@router.get("/status")
async def get_market_status(
    market_calendar: MarketCalendarService = Depends(get_market_calendar),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """获取市场状态信息.
    
    Returns:
        市场状态信息:
        - is_open: 市场是否开盘
        - timestamp: 当前时间 (UTC)
        - next_open: 下次开盘时间
        - next_close: 下次收盘时间
        
    Raises:
        HTTPException: 如果无法获取市场状态
    """
    if not market_calendar:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="市场日历服务不可用 - 需要至少一个活跃的交易会话",
        )
    
    try:
        market_status = await market_calendar.get_market_status()
        
        logger.info(
            f"Market status: {'OPEN' if market_status['is_open'] else 'CLOSED'}, "
            f"next_open={market_status['next_open']}"
        )
        
        return market_status
        
    except ExternalServiceError as e:
        logger.error(f"Failed to get market status: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"无法获取市场状态: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error getting market status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取市场状态失败: {str(e)}",
        )


@router.get("/is-open")
async def is_market_open(
    market_calendar: MarketCalendarService = Depends(get_market_calendar),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """检查市场是否开盘.
    
    Returns:
        {"is_open": bool, "checked_at": datetime}
        
    Raises:
        HTTPException: 如果无法检查市场状态
    """
    if not market_calendar:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="市场日历服务不可用 - 需要至少一个活跃的交易会话",
        )
    
    try:
        is_open = await market_calendar.is_market_open()
        
        return {
            "is_open": is_open,
            "checked_at": datetime.utcnow(),
        }
        
    except ExternalServiceError as e:
        logger.error(f"Failed to check market status: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"无法检查市场状态: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error checking market status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检查市场状态失败: {str(e)}",
        )


@router.get("/next-open")
async def get_next_market_open(
    market_calendar: MarketCalendarService = Depends(get_market_calendar),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """获取下次市场开盘时间.
    
    Returns:
        {"next_open": datetime}
        
    Raises:
        HTTPException: 如果无法获取开盘时间
    """
    if not market_calendar:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="市场日历服务不可用 - 需要至少一个活跃的交易会话",
        )
    
    try:
        next_open = await market_calendar.get_next_market_open()
        
        return {
            "next_open": next_open,
        }
        
    except ExternalServiceError as e:
        logger.error(f"Failed to get next market open: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"无法获取开盘时间: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error getting next market open: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取开盘时间失败: {str(e)}",
        )


@router.get("/next-close")
async def get_next_market_close(
    market_calendar: MarketCalendarService = Depends(get_market_calendar),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """获取下次市场收盘时间.
    
    Returns:
        {"next_close": datetime}
        
    Raises:
        HTTPException: 如果无法获取收盘时间
    """
    if not market_calendar:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="市场日历服务不可用 - 需要至少一个活跃的交易会话",
        )
    
    try:
        next_close = await market_calendar.get_next_market_close()
        
        return {
            "next_close": next_close,
        }
        
    except ExternalServiceError as e:
        logger.error(f"Failed to get next market close: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"无法获取收盘时间: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error getting next market close: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取收盘时间失败: {str(e)}",
        )


@router.get("/trading-hours")
async def is_regular_trading_hours(
    market_calendar: MarketCalendarService = Depends(get_market_calendar),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """检查当前是否在常规交易时间内 (9:30 AM - 4:00 PM ET).
    
    Returns:
        {"is_regular_hours": bool, "checked_at": datetime}
        
    Raises:
        HTTPException: 如果无法检查交易时间
    """
    if not market_calendar:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="市场日历服务不可用 - 需要至少一个活跃的交易会话",
        )
    
    try:
        is_regular_hours = await market_calendar.is_regular_trading_hours()
        
        return {
            "is_regular_hours": is_regular_hours,
            "checked_at": datetime.utcnow(),
        }
        
    except ExternalServiceError as e:
        logger.error(f"Failed to check trading hours: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"无法检查交易时间: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error checking trading hours: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检查交易时间失败: {str(e)}",
        )