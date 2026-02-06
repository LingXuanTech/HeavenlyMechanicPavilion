"""另类数据路由

提供 AH 溢价和专利监控的 API 端点。
"""

import structlog
from fastapi import APIRouter, Query
from typing import Optional

from api.schemas.alternative import (
    AHPremiumListResponse,
    AHPremiumDetailResponse,
    PatentAnalysisResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/alternative", tags=["Alternative Data"])


# ============ AH 溢价 API ============

@router.get("/ah-premium", response_model=AHPremiumListResponse)
async def get_ah_premium_list(
    sort_by: str = Query("premium_rate", description="排序字段: premium_rate / a_price / h_price"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
):
    """获取 AH 溢价排行榜

    返回所有 AH 股的溢价率排行，包含统计数据。
    """
    from services.alternative_data_service import ah_premium_service

    result = ah_premium_service.get_ah_premium_list(sort_by=sort_by, limit=limit)
    if "error" in result and not result.get("stocks"):
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=result["error"])
    return result


@router.get("/ah-premium/{symbol}", response_model=AHPremiumDetailResponse)
async def get_ah_premium_detail(symbol: str):
    """获取个股 AH 溢价详情

    返回指定股票的 AH 溢价详情，包含历史数据和套利信号。

    Args:
        symbol: A 股代码（如 600036.SH 或 600036）
    """
    from services.alternative_data_service import ah_premium_service

    result = ah_premium_service.get_ah_premium_detail(symbol)
    if not result.get("found") and "error" in result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ============ 专利监控 API ============

@router.get("/patents/{symbol}", response_model=PatentAnalysisResponse)
async def get_patent_analysis(
    symbol: str,
    company_name: Optional[str] = Query(None, description="公司名称（可选，用于搜索）"),
):
    """获取公司专利分析

    通过搜索引擎获取公司专利信息和技术趋势。

    Args:
        symbol: 股票代码
        company_name: 公司名称（可选）
    """
    from services.alternative_data_service import patent_service

    result = patent_service.get_patent_analysis(symbol, company_name or "")
    if "error" in result and not result.get("patent_news"):
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=result["error"])
    return result
