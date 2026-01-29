"""北向资金 API 路由

提供沪深港通北向资金数据接口
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import structlog

from services.north_money_service import (
    north_money_service,
    NorthMoneyFlow,
    NorthMoneySummary,
    NorthMoneyHistory,
    StockNorthHolding,
    NorthMoneyTopStock,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/north-money", tags=["North Money"])


@router.get("/flow", response_model=NorthMoneyFlow)
async def get_north_money_flow():
    """
    获取当日北向资金流向

    返回沪股通、深股通及合计净流入数据
    """
    try:
        return await north_money_service.get_north_money_flow()
    except Exception as e:
        logger.error("Failed to get north money flow", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary", response_model=NorthMoneySummary)
async def get_north_money_summary():
    """
    获取北向资金概览

    包含：
    - 当日流向
    - 净买入 TOP 10
    - 净卖出 TOP 10
    - 近 5 日历史
    - 本周趋势
    """
    try:
        return await north_money_service.get_summary()
    except Exception as e:
        logger.error("Failed to get north money summary", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=list[NorthMoneyHistory])
async def get_north_money_history(
    days: int = Query(default=30, ge=1, le=365, description="历史天数")
):
    """
    获取北向资金历史数据

    Args:
        days: 历史天数，默认 30 天，最大 365 天
    """
    try:
        return await north_money_service.get_north_money_history(days=days)
    except Exception as e:
        logger.error("Failed to get north money history", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/holding/{symbol}", response_model=Optional[StockNorthHolding])
async def get_stock_north_holding(symbol: str):
    """
    获取个股北向持仓变化

    Args:
        symbol: 股票代码，如 600519.SH
    """
    try:
        result = await north_money_service.get_stock_north_holding(symbol)
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Stock {symbol} not found in north holding data"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get stock north holding", symbol=symbol, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-buys", response_model=list[NorthMoneyTopStock])
async def get_top_north_buys(
    limit: int = Query(default=20, ge=1, le=100, description="返回数量")
):
    """
    获取北向资金净买入 TOP

    Args:
        limit: 返回数量，默认 20，最大 100
    """
    try:
        return await north_money_service.get_top_north_buys(limit=limit)
    except Exception as e:
        logger.error("Failed to get top north buys", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-sells", response_model=list[NorthMoneyTopStock])
async def get_top_north_sells(
    limit: int = Query(default=20, ge=1, le=100, description="返回数量")
):
    """
    获取北向资金净卖出 TOP

    Args:
        limit: 返回数量，默认 20，最大 100
    """
    try:
        return await north_money_service.get_top_north_sells(limit=limit)
    except Exception as e:
        logger.error("Failed to get top north sells", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
