"""限售解禁 API 路由

提供 A 股限售股解禁数据接口，包括：
- 近期解禁股票列表
- 解禁日历
- 个股解禁计划
- 解禁预警
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import structlog

from services.jiejin_service import (
    jiejin_service,
    JiejinStock,
    JiejinCalendar,
    StockJiejinPlan,
    JiejinSummary,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/jiejin", tags=["限售解禁"])


@router.get("/upcoming", response_model=list[JiejinStock])
async def get_upcoming_jiejin(
    days: int = Query(30, ge=1, le=90, description="查询未来天数，默认 30 天")
):
    """获取近期解禁股票

    返回未来指定天数内的解禁股票列表，包括解禁数量、市值、比例、压力评估。
    """
    try:
        result = await jiejin_service.get_upcoming_jiejin(days)
        logger.info("Upcoming jiejin fetched", count=len(result), days=days)
        return result
    except Exception as e:
        logger.error("Failed to fetch upcoming jiejin", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取解禁数据失败: {str(e)}")


@router.get("/calendar", response_model=list[JiejinCalendar])
async def get_jiejin_calendar(
    days: int = Query(30, ge=1, le=90, description="查询未来天数，默认 30 天")
):
    """获取解禁日历

    按日期聚合的解禁数据，展示每日解禁股票数、总市值等。
    """
    try:
        result = await jiejin_service.get_jiejin_calendar(days)
        logger.info("Jiejin calendar fetched", days=days, dates=len(result))
        return result
    except Exception as e:
        logger.error("Failed to fetch jiejin calendar", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取解禁日历失败: {str(e)}")


@router.get("/summary", response_model=JiejinSummary)
async def get_jiejin_summary(
    days: int = Query(30, ge=1, le=90, description="统计未来天数，默认 30 天")
):
    """获取解禁概览

    返回解禁汇总：涉及股票数、总解禁市值、日均解禁、高压力股票、完整日历。
    """
    try:
        result = await jiejin_service.get_summary(days)
        logger.info(
            "Jiejin summary fetched",
            total_stocks=result.total_stocks,
            total_value=f"{result.total_market_value:.2f}亿",
        )
        return result
    except Exception as e:
        logger.error("Failed to fetch jiejin summary", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取解禁概览失败: {str(e)}")


@router.get("/stock/{symbol}", response_model=Optional[StockJiejinPlan])
async def get_stock_jiejin_plan(symbol: str):
    """获取个股解禁计划

    返回指定股票的未来解禁计划和历史解禁记录。

    Args:
        symbol: 股票代码，如 600519.SH 或 000001.SZ
    """
    try:
        result = await jiejin_service.get_stock_jiejin_plan(symbol)
        if result:
            logger.info(
                "Stock jiejin plan fetched",
                symbol=symbol,
                upcoming=len(result.upcoming_jiejin),
            )
        return result
    except Exception as e:
        logger.error("Failed to fetch stock jiejin plan", symbol=symbol, error=str(e))
        raise HTTPException(status_code=500, detail=f"获取个股解禁计划失败: {str(e)}")


@router.get("/high-pressure", response_model=list[JiejinStock])
async def get_high_pressure_stocks(
    days: int = Query(7, ge=1, le=30, description="查询未来天数，默认 7 天")
):
    """获取高解禁压力股票

    返回近期解禁压力较大的股票（解禁比例 > 10% 或 解禁市值 > 50 亿）。
    """
    try:
        result = await jiejin_service.get_high_pressure_stocks(days)
        logger.info("High pressure stocks fetched", count=len(result), days=days)
        return result
    except Exception as e:
        logger.error("Failed to fetch high pressure stocks", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取高压力股票失败: {str(e)}")


@router.get("/warning/{symbol}")
async def check_stock_jiejin_warning(
    symbol: str,
    days: int = Query(30, ge=1, le=90, description="预警时间窗口，默认 30 天")
):
    """检查个股解禁预警

    检查指定股票在未来时间窗口内是否有解禁压力。

    Args:
        symbol: 股票代码
        days: 预警时间窗口

    Returns:
        预警信息，包括预警级别（严重/警告/提示）、解禁详情
    """
    try:
        result = await jiejin_service.check_stock_jiejin_warning(symbol, days)
        if result:
            logger.info(
                "Jiejin warning detected",
                symbol=symbol,
                level=result["warning_level"],
            )
        return result or {"symbol": symbol, "warning_level": "无", "message": "未来无解禁计划"}
    except Exception as e:
        logger.error("Failed to check jiejin warning", symbol=symbol, error=str(e))
        raise HTTPException(status_code=500, detail=f"检查解禁预警失败: {str(e)}")


@router.get("/today", response_model=list[JiejinStock])
async def get_today_jiejin():
    """获取今日解禁股票

    返回今日有解禁的股票列表。
    """
    try:
        result = await jiejin_service.get_upcoming_jiejin(1)
        from datetime import date
        today = date.today()
        today_stocks = [s for s in result if s.jiejin_date == today]
        logger.info("Today jiejin fetched", count=len(today_stocks))
        return today_stocks
    except Exception as e:
        logger.error("Failed to fetch today jiejin", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取今日解禁失败: {str(e)}")


@router.get("/week", response_model=list[JiejinStock])
async def get_week_jiejin():
    """获取本周解禁股票

    返回本周有解禁的股票列表。
    """
    try:
        result = await jiejin_service.get_upcoming_jiejin(7)
        logger.info("Week jiejin fetched", count=len(result))
        return result
    except Exception as e:
        logger.error("Failed to fetch week jiejin", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取本周解禁失败: {str(e)}")
