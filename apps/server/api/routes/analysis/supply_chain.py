"""产业链分析路由

提供产业链知识图谱查询和分析的 API 端点。
"""

import structlog
from fastapi import APIRouter, HTTPException
from typing import Optional

from api.schemas.supply_chain import (
    ChainListResponse,
    ChainGraphResponse,
    StockChainPositionResponse,
    SupplyChainImpactResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/supply-chain", tags=["Supply Chain"])


@router.get("/chains", response_model=ChainListResponse)
async def get_chain_list():
    """获取所有产业链列表

    返回预定义的 A 股核心产业链概览。
    """
    from services.supply_chain_service import supply_chain_service

    return supply_chain_service.get_chain_list()


@router.get("/graph/{chain_id}", response_model=ChainGraphResponse)
async def get_chain_graph(chain_id: str):
    """获取产业链图谱数据

    返回指定产业链的节点和边数据，用于前端可视化。

    Args:
        chain_id: 产业链 ID（如 semiconductor, ev, photovoltaic）
    """
    from services.supply_chain_service import supply_chain_service

    result = supply_chain_service.get_chain_graph(chain_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/stock/{symbol}", response_model=StockChainPositionResponse)
async def get_stock_chain_position(symbol: str):
    """获取个股在产业链中的位置

    查找指定股票所属的产业链及其上下游位置。

    Args:
        symbol: 股票代码（如 300750, 002594.SZ）
    """
    from services.supply_chain_service import supply_chain_service

    return supply_chain_service.get_stock_chain_position(symbol)


@router.get("/impact/{symbol}", response_model=SupplyChainImpactResponse)
async def analyze_supply_chain_impact(symbol: str):
    """分析产业链传导效应

    分析指定股票的上下游传导关系和供应链风险。

    Args:
        symbol: 股票代码
    """
    from services.supply_chain_service import supply_chain_service

    return supply_chain_service.analyze_supply_chain_impact(symbol)
