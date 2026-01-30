"""限售解禁 API 路由

提供 A 股限售解禁数据接口
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import date, datetime
import structlog

from services.unlock_service import (
    unlock_service,
    UnlockCalendar,
    UnlockPressure,
    MarketUnlockOverview,
    UnlockStock,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/unlock", tags=["限售解禁"])


@router.get("/calendar", response_model=list[UnlockCalendar])
async def get_unlock_calendar(
    start_date: Optional[str] = Query(
        None,
        description="开始日期，格式 YYYY-MM-DD，默认今天"
    ),
    end_date: Optional[str] = Query(
        None,
        description="结束日期，格式 YYYY-MM-DD，默认 30 天后"
    )
):
    """获取解禁日历

    返回指定日期范围内的解禁计划，按日期分组展示。
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
        result = await unlock_service.get_unlock_calendar(start, end)
        logger.info("Unlock calendar fetched", days=len(result))
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"日期格式错误: {str(e)}")
    except Exception as e:
        logger.error("Failed to fetch unlock calendar", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取解禁日历失败: {str(e)}")


@router.get("/overview", response_model=MarketUnlockOverview)
async def get_market_overview():
    """获取市场解禁概览

    返回：
    - 本周/下周/本月解禁市值
    - 高压力解禁股列表
    - 解禁趋势判断
    - 市场影响评估
    """
    try:
        result = await unlock_service.get_market_unlock_overview()
        logger.info(
            "Market unlock overview fetched",
            this_week=f"{result.this_week_value:.1f}亿",
        )
        return result
    except Exception as e:
        logger.error("Failed to fetch market unlock overview", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取解禁概览失败: {str(e)}")


@router.get("/stock/{symbol}", response_model=list[UnlockStock])
async def get_stock_unlock_schedule(symbol: str):
    """获取个股解禁计划

    返回指定股票的未来解禁计划列表。

    Args:
        symbol: 股票代码，如 600519.SH
    """
    try:
        result = await unlock_service.get_stock_unlock_schedule(symbol)
        logger.info("Stock unlock schedule fetched", symbol=symbol, count=len(result))
        return result
    except Exception as e:
        logger.error("Failed to fetch stock unlock schedule", symbol=symbol, error=str(e))
        raise HTTPException(status_code=500, detail=f"获取个股解禁计划失败: {str(e)}")


@router.get("/pressure/{symbol}", response_model=UnlockPressure)
async def get_stock_unlock_pressure(symbol: str):
    """获取个股解禁压力评估

    对指定股票的解禁压力进行综合评估，返回：
    - 压力评分（0-100）
    - 压力等级（低/中/高/极高）
    - 未来 30 日解禁计划
    - 风险因素分析
    - 操作建议

    Args:
        symbol: 股票代码
    """
    try:
        result = await unlock_service.get_unlock_pressure(symbol)
        logger.info(
            "Stock unlock pressure fetched",
            symbol=symbol,
            score=result.pressure_score,
            level=result.pressure_level,
        )
        return result
    except Exception as e:
        logger.error("Failed to fetch unlock pressure", symbol=symbol, error=str(e))
        raise HTTPException(status_code=500, detail=f"获取解禁压力评估失败: {str(e)}")


@router.get("/high-pressure", response_model=list[UnlockPressure])
async def get_high_pressure_stocks(
    limit: int = Query(20, ge=1, le=50, description="返回数量，默认 20")
):
    """获取高解禁压力股票列表

    返回近期解禁压力较大的股票列表，按压力评分排序。
    """
    try:
        result = await unlock_service.get_high_pressure_stocks(limit)
        logger.info("High pressure stocks fetched", count=len(result))
        return result
    except Exception as e:
        logger.error("Failed to fetch high pressure stocks", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取高压力股票失败: {str(e)}")
