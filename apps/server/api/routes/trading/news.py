"""News API Routes

Note: This module provides backward-compatible endpoints.
For new integrations, prefer using /news-aggregator/* endpoints.
"""
import structlog
from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse
from typing import List, Dict, Any

from services.news_aggregator import news_aggregator

router = APIRouter(prefix="/news", tags=["News"])
logger = structlog.get_logger()


@router.get("/flash")
async def get_flash_news(limit: int = Query(10, ge=1, le=50)):
    """
    Get latest flash news.

    Note: This endpoint delegates to news_aggregator service.
    For more options, use /news-aggregator/flash instead.
    """
    try:
        news = await news_aggregator.get_flash_news(limit)
        # Transform to legacy format for backward compatibility
        result = []
        for i, item in enumerate(news):
            result.append({
                "id": i + 1,
                "title": item.title,
                "time": item.published_at.strftime("%H:%M:%S") if item.published_at else "",
                "sentiment": item.sentiment.value if item.sentiment else "neutral",
                "source": item.source,
                "url": item.url,
            })
        return result

    except Exception as e:
        logger.error("Failed to get flash news", error=str(e))
        # Fallback to minimal mock if service fails
        return [{
            "id": 1,
            "title": "News service temporarily unavailable",
            "time": "",
            "sentiment": "neutral"
        }]


@router.get("/{symbol}")
async def get_stock_news(symbol: str, limit: int = Query(20, ge=1, le=100)):
    """
    Get news for a specific stock.

    Note: This endpoint delegates to news_aggregator service.
    For more options, use /news-aggregator/symbol/{symbol} instead.
    """
    try:
        news = await news_aggregator.get_news_by_symbol(symbol.upper())
        news = news[:limit]

        # Transform to legacy format for backward compatibility
        result = []
        for item in news:
            result.append({
                "headline": item.title,
                "source": item.source,
                "url": item.url or "#",
                "time": item.published_at.strftime("%Y-%m-%d %H:%M") if item.published_at else "N/A",
                "sentiment": item.sentiment.value if item.sentiment else "neutral",
                "summary": item.summary,
            })
        return result

    except Exception as e:
        logger.error("Failed to get stock news", symbol=symbol, error=str(e))
        # Fallback to minimal mock if service fails
        return [{
            "headline": f"Unable to fetch news for {symbol}",
            "source": "System",
            "url": "#",
            "time": "N/A",
            "sentiment": "neutral"
        }]
