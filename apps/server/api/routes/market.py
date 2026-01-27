from fastapi import APIRouter, Depends
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

@router.get("/global")
async def get_global_indices():
    # Mock global indices for now
    return [
        {"name": "S&P 500", "value": 5123.45, "change": 12.3, "percent": 0.24},
        {"name": "Nasdaq", "value": 16234.56, "change": -45.6, "percent": -0.28},
        {"name": "SSE Composite", "value": 3045.67, "change": 5.6, "percent": 0.18},
        {"name": "Hang Seng", "value": 16789.01, "change": 123.4, "percent": 0.74}
    ]
