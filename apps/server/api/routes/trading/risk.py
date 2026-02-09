"""风控建模 API 路由

提供 VaR/CVaR 计算、压力测试和综合风险指标端点。
"""

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from services.risk_modeling_service import risk_modeling_service

router = APIRouter(prefix="/risk", tags=["Risk Modeling"])
logger = structlog.get_logger()


class VaRRequest(BaseModel):
    """VaR 计算请求"""
    symbols: List[str] = Field(..., min_length=1, max_length=20, description="股票代码列表")
    weights: Optional[List[float]] = Field(None, description="权重列表（默认等权）")
    confidence: float = Field(default=0.95, ge=0.9, le=0.99, description="置信水平")
    days: int = Field(default=1, ge=1, le=30, description="持有期（天）")
    simulations: int = Field(default=10000, ge=1000, le=100000, description="模拟次数")


class StressTestRequest(BaseModel):
    """压力测试请求"""
    symbols: List[str] = Field(..., min_length=1, max_length=20)
    weights: Optional[List[float]] = None
    scenario: Optional[str] = Field(None, description="场景 ID（为空则运行所有场景）")


class RiskMetricsRequest(BaseModel):
    """综合风险指标请求"""
    symbols: List[str] = Field(..., min_length=1, max_length=20)
    weights: Optional[List[float]] = None
    lookback_days: int = Field(default=252, ge=30, le=756, description="历史回看天数")


@router.post("/var")
async def calculate_var(body: VaRRequest):
    """计算组合 VaR/CVaR（蒙特卡洛模拟）

    返回 VaR/CVaR 值和模拟分布直方图数据，用于前端可视化。
    """
    try:
        result = await risk_modeling_service.calculate_var(
            symbols=body.symbols,
            weights=body.weights,
            confidence=body.confidence,
            days=body.days,
            simulations=body.simulations,
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("VaR calculation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stress-test")
async def run_stress_test(body: StressTestRequest):
    """运行压力测试

    预设场景：2008金融危机、2020疫情、利率骤升、中美贸易战。
    返回每个场景下的组合预期损失。
    """
    try:
        result = await risk_modeling_service.run_stress_test(
            symbols=body.symbols,
            weights=body.weights,
            scenario=body.scenario,
        )
        return result
    except Exception as e:
        logger.error("Stress test failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/metrics")
async def get_risk_metrics(body: RiskMetricsRequest):
    """获取综合风险指标

    返回波动率、夏普比率、最大回撤、Beta、Sortino 比率等。
    """
    try:
        result = await risk_modeling_service.get_risk_metrics(
            symbols=body.symbols,
            weights=body.weights,
            lookback_days=body.lookback_days,
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Risk metrics calculation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
