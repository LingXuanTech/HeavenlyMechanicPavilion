"""新闻聚合 API 路由"""
import structlog
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from services.news_aggregator import (
    news_aggregator,
    NewsItem,
    NewsAggregateResult,
    NewsCategory
)

router = APIRouter(prefix="/news-aggregator", tags=["News Aggregator"])
logger = structlog.get_logger()


@router.get("/status")
async def get_aggregator_status():
    """
    获取新闻聚合服务状态

    返回各新闻源可用性和缓存状态。
    """
    return news_aggregator.get_stats()


@router.get("/all", response_model=NewsAggregateResult)
async def get_all_news(force_refresh: bool = Query(False)):
    """
    获取所有聚合新闻

    返回所有来源的新闻，按发布时间倒序。
    """
    try:
        result = await news_aggregator.aggregate(force_refresh)
        return result

    except Exception as e:
        logger.error("Failed to aggregate news", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取新闻失败: {str(e)}")


@router.get("/flash", response_model=List[NewsItem])
async def get_flash_news(limit: int = Query(10, ge=1, le=50)):
    """
    获取快讯

    返回最新的 N 条新闻，适用于滚动新闻栏。
    """
    try:
        news = await news_aggregator.get_flash_news(limit)
        return news

    except Exception as e:
        logger.error("Failed to get flash news", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取快讯失败: {str(e)}")


@router.get("/category/{category}", response_model=List[NewsItem])
async def get_news_by_category(
    category: NewsCategory,
    limit: int = Query(20, ge=1, le=100)
):
    """
    按类别获取新闻

    类别：
    - market: 市场动态
    - stock: 个股新闻
    - macro: 宏观经济
    - policy: 政策法规
    - earnings: 财报业绩
    - general: 综合
    """
    try:
        news = await news_aggregator.get_news_by_category(category)
        return news[:limit]

    except Exception as e:
        logger.error("Failed to get news by category", category=category, error=str(e))
        raise HTTPException(status_code=500, detail=f"获取新闻失败: {str(e)}")


@router.get("/symbol/{symbol}", response_model=List[NewsItem])
async def get_news_by_symbol(
    symbol: str,
    limit: int = Query(20, ge=1, le=100)
):
    """
    获取特定股票的新闻

    支持美股代码（如 AAPL, TSLA）。
    """
    try:
        news = await news_aggregator.get_news_by_symbol(symbol.upper())
        return news[:limit]

    except Exception as e:
        logger.error("Failed to get news by symbol", symbol=symbol, error=str(e))
        raise HTTPException(status_code=500, detail=f"获取股票新闻失败: {str(e)}")


@router.post("/refresh")
async def refresh_news():
    """
    手动刷新新闻
    """
    try:
        result = await news_aggregator.aggregate(force_refresh=True)
        return {
            "status": "success",
            "message": f"已刷新 {result.total} 条新闻",
            "sources": result.sources,
            "total": result.total
        }

    except Exception as e:
        logger.error("Failed to refresh news", error=str(e))
        raise HTTPException(status_code=500, detail=f"刷新失败: {str(e)}")


@router.get("/sources")
async def get_news_sources():
    """
    获取所有新闻源信息
    """
    from services.news_aggregator import RSS_FEEDS

    sources = []
    for feed_id, config in RSS_FEEDS.items():
        sources.append({
            "id": feed_id,
            "name": config["name"],
            "category": config.get("category", "general"),
            "enabled": config.get("enabled", True)
        })

    stats = news_aggregator.get_stats()

    return {
        "rss_feeds": sources,
        "finnhub_enabled": stats["finnhub_available"],
        "total_sources": len([s for s in sources if s["enabled"]]) + (1 if stats["finnhub_available"] else 0)
    }
