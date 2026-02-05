from fastapi import APIRouter, Depends, Query
from typing import List
from services.data_router import MarketRouter
from services.models import StockPrice, KlineData
import structlog

router = APIRouter(prefix="/market", tags=["Market"])
logger = structlog.get_logger()

@router.get("/price/{symbol}", response_model=StockPrice)
async def get_price(symbol: str):
    return await MarketRouter.get_stock_price(symbol)

@router.get("/history/{symbol}", response_model=List[KlineData])
async def get_history(symbol: str, period: str = "1mo"):
    return await MarketRouter.get_history(symbol, period)

@router.get("/kline/{symbol}")
async def get_kline(
    symbol: str,
    days: int = Query(default=90, ge=1, le=3650),
):
    """获取 K 线数据（按天数）

    Args:
        symbol: 股票代码
        days: 天数（1-3650）

    Returns:
        K 线数据列表
    """
    # 将天数转换为 yfinance 支持的 period 格式
    if days <= 7:
        period = "5d"
    elif days <= 30:
        period = "1mo"
    elif days <= 90:
        period = "3mo"
    elif days <= 180:
        period = "6mo"
    elif days <= 365:
        period = "1y"
    elif days <= 730:
        period = "2y"
    elif days <= 1825:
        period = "5y"
    else:
        period = "max"

    try:
        history = await MarketRouter.get_history(symbol, period)

        # 转换为前端需要的格式
        kline_data = [
            {
                "time": h.datetime.strftime("%Y-%m-%d"),
                "open": h.open,
                "high": h.high,
                "low": h.low,
                "close": h.close,
                "volume": h.volume,
            }
            for h in history[-days:]  # 只返回请求的天数
        ]

        return {"kline": kline_data, "symbol": symbol, "days": len(kline_data)}
    except Exception as e:
        logger.error("Failed to get kline data", symbol=symbol, error=str(e))
        return {"kline": [], "symbol": symbol, "days": 0, "error": str(e)}

@router.get("/global")
async def get_global_indices():
    # Mock global indices for now
    return [
        {"name": "S&P 500", "value": 5123.45, "change": 12.3, "percent": 0.24},
        {"name": "Nasdaq", "value": 16234.56, "change": -45.6, "percent": -0.28},
        {"name": "SSE Composite", "value": 3045.67, "change": 5.6, "percent": 0.18},
        {"name": "Hang Seng", "value": 16789.01, "change": 123.4, "percent": 0.74}
    ]
