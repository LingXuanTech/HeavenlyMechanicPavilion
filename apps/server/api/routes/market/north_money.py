"""北向资金 API 路由

提供沪深港通北向资金数据接口
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import structlog

from services.north_money_service import (
    north_money_service,
    NorthMoneyFlow,
    NorthMoneySummary,
    NorthMoneyHistory,
    StockNorthHolding,
    NorthMoneyTopStock,
    NorthMoneySectorFlow,
    SectorRotationSignal,
    IntradayFlowSummary,
    NorthMoneyAnomaly,
    NorthMoneyRealtime,
    HistoryQueryResult,
    CorrelationAnalysis,
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


@router.get("/sector-flow", response_model=list[NorthMoneySectorFlow])
async def get_sector_flow():
    """
    获取北向资金板块流向

    返回各申万一级行业的资金流向汇总：
    - 板块名称和代码
    - 净买入金额（亿元）
    - 涉及股票数量
    - 资金流向（inflow/outflow/neutral）
    - TOP 净买入个股
    """
    try:
        return await north_money_service.get_sector_flow()
    except Exception as e:
        logger.error("Failed to get sector flow", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rotation-signal", response_model=SectorRotationSignal)
async def get_rotation_signal():
    """
    获取板块轮动信号

    分析北向资金在不同板块间的流动，返回：
    - 资金流入板块列表（按流入强度排序）
    - 资金流出板块列表（按流出强度排序）
    - 轮动模式判断（defensive/aggressive/mixed/broad_inflow/broad_outflow）
    - 信号强度（0-100）
    - 投资建议解读
    """
    try:
        return await north_money_service.get_sector_rotation_signal()
    except Exception as e:
        logger.error("Failed to get rotation signal", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============ 实时增强接口 ============

@router.get("/intraday", response_model=IntradayFlowSummary)
async def get_intraday_flow():
    """
    获取盘中分时北向资金流向

    返回：
    - 当前累计净流入
    - 分时数据点列表（分钟级）
    - 盘中峰值净流入/流出
    - 流向波动率
    - 动量方向（accelerating/decelerating/stable）

    注意：仅在交易时段（9:30-11:30, 13:00-15:00）返回分时数据
    """
    try:
        return await north_money_service.get_intraday_flow()
    except Exception as e:
        logger.error("Failed to get intraday flow", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anomalies", response_model=List[NorthMoneyAnomaly])
async def get_anomalies():
    """
    检测北向资金异常流动

    检测规则：
    - 突然大额流入/流出（单日超过 100 亿）
    - 流向反转（连续多日后方向突变）
    - 盘中剧烈波动（波动率超阈值）
    - 个股异常集中（单一股票占比过高）

    返回异常列表，每条包含：
    - 异常类型和严重程度
    - 描述和受影响个股
    - 操作建议
    """
    try:
        return await north_money_service.detect_anomalies()
    except Exception as e:
        logger.error("Failed to detect anomalies", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/realtime", response_model=NorthMoneyRealtime)
async def get_realtime_panorama():
    """
    获取北向资金实时全景数据

    整合所有北向资金相关数据，适合前端仪表盘使用。

    包含：
    - 基础概览（summary）
    - 盘中实时（intraday，仅交易时段）
    - 异常信号（anomalies）
    - 与主要指数相关性（index_correlation）
    - 是否交易时段标识

    建议前端轮询间隔：交易时段 1 分钟，非交易时段 5 分钟
    """
    try:
        return await north_money_service.get_realtime_panorama()
    except Exception as e:
        logger.error("Failed to get realtime panorama", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history-db", response_model=HistoryQueryResult)
async def get_north_money_history_db(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数")
):
    """
    从数据库查询北向资金历史数据
    """
    try:
        return await north_money_service.get_history(start_date, end_date, limit)
    except Exception as e:
        logger.error("Failed to get north money history from DB", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/correlation", response_model=CorrelationAnalysis)
async def get_north_money_correlation(
    days: int = Query(20, ge=5, le=250, description="计算窗口天数")
):
    """
    获取北向资金与指数的相关性分析
    """
    try:
        return await north_money_service.calculate_correlation(days)
    except Exception as e:
        logger.error("Failed to get north money correlation", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync", status_code=201)
async def sync_north_money_data(
    date: Optional[str] = Query(None, description="同步日期 (YYYY-MM-DD)，默认为今日")
):
    """
    手动触发北向资金数据同步到数据库
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date() if date else None
        success = await north_money_service.save_daily_data(target_date)
        if not success:
            raise HTTPException(status_code=400, detail="Data sync failed or no data available for the date")
        return {"status": "success", "date": date or datetime.now().strftime("%Y-%m-%d")}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")
    except Exception as e:
        logger.error("Failed to sync north money data", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
