"""龙虎榜 API 路由

提供 A 股龙虎榜数据接口，包括：
- 每日龙虎榜
- 个股龙虎榜历史
- 知名游资动向
- 龙虎榜概览
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import structlog

from services.lhb_service import lhb_service, LHBStock, LHBRecord, HotMoneySeat, LHBSummary

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/lhb", tags=["龙虎榜"])


@router.get("/daily", response_model=list[LHBStock])
async def get_daily_lhb(
    trade_date: Optional[str] = Query(
        None,
        description="交易日期，格式 YYYYMMDD，默认最近交易日",
        pattern=r"^\d{8}$"
    )
):
    """获取每日龙虎榜

    返回当日所有上榜股票，包括买卖席位明细、机构净买入、游资参与情况。
    """
    try:
        result = await lhb_service.get_daily_lhb(trade_date)
        logger.info("Daily LHB fetched", count=len(result), trade_date=trade_date)
        return result
    except Exception as e:
        logger.error("Failed to fetch daily LHB", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取龙虎榜失败: {str(e)}")


@router.get("/summary", response_model=LHBSummary)
async def get_lhb_summary():
    """获取龙虎榜概览

    返回当日龙虎榜汇总：上榜股票数、全市场净买入、机构净买入、
    净买入/净卖出 TOP、活跃知名游资。
    """
    try:
        result = await lhb_service.get_summary()
        logger.info(
            "LHB summary fetched",
            total_stocks=result.total_stocks,
            total_net_buy=f"{result.total_net_buy:.2f}亿",
        )
        return result
    except Exception as e:
        logger.error("Failed to fetch LHB summary", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取龙虎榜概览失败: {str(e)}")


@router.get("/stock/{symbol}", response_model=list[LHBRecord])
async def get_stock_lhb_history(
    symbol: str,
    days: int = Query(30, ge=1, le=365, description="查询天数，默认 30 天")
):
    """获取个股龙虎榜历史

    返回指定股票的历史上榜记录，包括上榜原因、净买入金额、机构净买入等。

    Args:
        symbol: 股票代码，如 600519.SH 或 000001.SZ
        days: 查询天数
    """
    try:
        result = await lhb_service.get_stock_lhb_history(symbol, days)
        logger.info("Stock LHB history fetched", symbol=symbol, records=len(result))
        return result
    except Exception as e:
        logger.error("Failed to fetch stock LHB history", symbol=symbol, error=str(e))
        raise HTTPException(status_code=500, detail=f"获取个股龙虎榜历史失败: {str(e)}")


@router.get("/hot-money", response_model=list[HotMoneySeat])
async def get_hot_money_activity(
    days: int = Query(5, ge=1, le=30, description="查询天数，默认 5 天")
):
    """获取知名游资近期活动

    返回近期活跃的知名游资席位及其操作的股票。
    包括游资别名、操作风格、近期买卖记录。
    """
    try:
        result = await lhb_service.get_hot_money_activity(days)
        logger.info("Hot money activity fetched", count=len(result), days=days)
        return result
    except Exception as e:
        logger.error("Failed to fetch hot money activity", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取游资动向失败: {str(e)}")


@router.get("/top-buys", response_model=list[LHBStock])
async def get_top_buys(
    limit: int = Query(10, ge=1, le=50, description="返回数量，默认 10")
):
    """获取龙虎榜净买入 TOP

    返回当日净买入金额最高的股票列表。
    """
    try:
        daily = await lhb_service.get_daily_lhb()
        result = sorted(daily, key=lambda x: x.lhb_net_buy, reverse=True)[:limit]
        logger.info("Top buys fetched", count=len(result))
        return result
    except Exception as e:
        logger.error("Failed to fetch top buys", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取净买入 TOP 失败: {str(e)}")


@router.get("/top-sells", response_model=list[LHBStock])
async def get_top_sells(
    limit: int = Query(10, ge=1, le=50, description="返回数量，默认 10")
):
    """获取龙虎榜净卖出 TOP

    返回当日净卖出金额最高的股票列表。
    """
    try:
        daily = await lhb_service.get_daily_lhb()
        result = sorted(daily, key=lambda x: x.lhb_net_buy)[:limit]
        logger.info("Top sells fetched", count=len(result))
        return result
    except Exception as e:
        logger.error("Failed to fetch top sells", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取净卖出 TOP 失败: {str(e)}")


@router.get("/institution-activity", response_model=list[LHBStock])
async def get_institution_activity(
    direction: str = Query("buy", pattern="^(buy|sell|all)$", description="方向: buy/sell/all")
):
    """获取机构专用席位活动

    返回有机构席位参与的股票列表。

    Args:
        direction: 筛选方向 - buy (机构净买入), sell (机构净卖出), all (全部)
    """
    try:
        daily = await lhb_service.get_daily_lhb()

        if direction == "buy":
            result = [s for s in daily if s.institution_net > 0]
            result.sort(key=lambda x: x.institution_net, reverse=True)
        elif direction == "sell":
            result = [s for s in daily if s.institution_net < 0]
            result.sort(key=lambda x: x.institution_net)
        else:
            result = [s for s in daily if s.institution_net != 0]
            result.sort(key=lambda x: abs(x.institution_net), reverse=True)

        logger.info("Institution activity fetched", direction=direction, count=len(result))
        return result
    except Exception as e:
        logger.error("Failed to fetch institution activity", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取机构动向失败: {str(e)}")


@router.get("/hot-money-stocks", response_model=list[LHBStock])
async def get_hot_money_stocks():
    """获取有知名游资参与的股票

    返回当日有知名游资席位参与的股票列表。
    """
    try:
        daily = await lhb_service.get_daily_lhb()
        result = [s for s in daily if s.hot_money_involved]
        result.sort(key=lambda x: x.lhb_net_buy, reverse=True)
        logger.info("Hot money stocks fetched", count=len(result))
        return result
    except Exception as e:
        logger.error("Failed to fetch hot money stocks", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取游资股票失败: {str(e)}")
