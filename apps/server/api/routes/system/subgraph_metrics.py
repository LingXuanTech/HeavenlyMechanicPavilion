"""SubGraph A/B 指标路由

提供 SubGraph vs Monolith 的对比数据和灰度控制端点。
"""

import structlog
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from services.subgraph_metrics_service import subgraph_metrics_service

router = APIRouter(prefix="/subgraph-metrics", tags=["SubGraph Metrics"])
logger = structlog.get_logger()


class RolloutUpdateRequest(BaseModel):
    """灰度比例更新请求"""
    percentage: int = Field(..., ge=0, le=100, description="灰度比例 (0-100)")


@router.get("/comparison")
async def get_comparison(days: int = Query(default=7, ge=1, le=90)):
    """获取 SubGraph vs Monolith 的 A/B 对比数据

    返回两种架构模式在指定时间段内的统计指标：
    - count: 分析任务总数
    - avg_elapsed_seconds: 平均耗时
    - success_rate: 成功率
    - avg_confidence: 平均置信度
    - recommendation: 灰度推荐（needs_more_data / subgraph_ready / monolith_better）
    """
    try:
        return subgraph_metrics_service.get_comparison(days=days)
    except Exception as e:
        logger.error("Failed to get subgraph comparison", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rollout")
async def update_rollout(body: RolloutUpdateRequest):
    """更新 SubGraph 灰度比例

    修改运行时灰度比例（0-100%），重启后恢复为环境变量值。
    """
    try:
        return subgraph_metrics_service.update_rollout_percentage(body.percentage)
    except Exception as e:
        logger.error("Failed to update rollout", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
