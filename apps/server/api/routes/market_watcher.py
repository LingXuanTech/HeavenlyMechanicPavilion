"""市场指数监控 API 路由"""
import structlog
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from services.market_watcher import (
    market_watcher,
    MarketIndex,
    MarketOverview,
    MarketRegion
)

router = APIRouter(prefix="/market-watcher", tags=["Market Watcher"])
logger = structlog.get_logger()


@router.get("/status")
async def get_watcher_status():
    """
    获取市场监控服务状态

    返回数据源可用性和缓存状态。
    """
    return market_watcher.get_stats()


@router.get("/overview", response_model=MarketOverview)
async def get_market_overview(force_refresh: bool = Query(False)):
    """
    获取全球市场概览

    返回所有主要指数、市场情绪和风险等级。
    """
    try:
        if force_refresh:
            # 强制刷新
            await market_watcher.get_all_indices(force_refresh=True)

        overview = await market_watcher.get_market_overview()
        return overview

    except Exception as e:
        logger.error("Failed to get market overview", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取市场概览失败: {str(e)}")


@router.get("/indices", response_model=List[MarketIndex])
async def get_all_indices(
    region: Optional[MarketRegion] = Query(None, description="筛选市场区域"),
    force_refresh: bool = Query(False)
):
    """
    获取所有市场指数

    可按区域筛选：CN（中国大陆）、HK（香港）、US（美国）
    """
    try:
        if region:
            indices = await market_watcher.get_indices_by_region(region)
        else:
            indices = await market_watcher.get_all_indices(force_refresh=force_refresh)

        return indices

    except Exception as e:
        logger.error("Failed to get indices", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取指数失败: {str(e)}")


@router.get("/index/{code}", response_model=MarketIndex)
async def get_single_index(code: str):
    """
    获取单个指数详情

    示例代码：
    - 上证指数: 000001.SS
    - 恒生指数: ^HSI
    - 标普500: ^GSPC
    """
    index = await market_watcher.get_index(code)

    if not index:
        raise HTTPException(
            status_code=404,
            detail=f"未找到指数: {code}"
        )

    return index


@router.post("/refresh")
async def refresh_indices():
    """
    手动刷新所有指数数据
    """
    try:
        indices = await market_watcher.get_all_indices(force_refresh=True)
        return {
            "status": "success",
            "message": f"已刷新 {len(indices)} 个指数",
            "count": len(indices)
        }

    except Exception as e:
        logger.error("Failed to refresh indices", error=str(e))
        raise HTTPException(status_code=500, detail=f"刷新失败: {str(e)}")


@router.get("/sentiment")
async def get_market_sentiment():
    """
    获取市场情绪分析

    返回全球市场情绪和各区域详细情况。
    """
    try:
        overview = await market_watcher.get_market_overview()

        # 按区域分组计算情绪
        regions_data = {}
        for region in MarketRegion:
            region_indices = [idx for idx in overview.indices if idx.region == region]
            if region_indices:
                avg_change = sum(idx.change_percent for idx in region_indices) / len(region_indices)
                regions_data[region.value] = {
                    "indices_count": len(region_indices),
                    "avg_change_percent": round(avg_change, 2),
                    "sentiment": "Bullish" if avg_change > 0.5 else ("Bearish" if avg_change < -0.5 else "Neutral")
                }

        return {
            "global_sentiment": overview.global_sentiment,
            "risk_level": overview.risk_level,
            "regions": regions_data,
            "updated_at": overview.updated_at.isoformat()
        }

    except Exception as e:
        logger.error("Failed to get sentiment", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取市场情绪失败: {str(e)}")
