"""跨资产联动分析 API 路由

提供股、债、汇、商品之间的联动分析接口
"""

from fastapi import APIRouter, HTTPException
from typing import List
import structlog

from services.cross_asset_service import (
    cross_asset_service,
    AssetPrice,
    AssetCorrelation,
    RiskAppetiteSignal,
    CrossAssetDivergence,
    CrossAssetAnalysisResult,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/cross-asset", tags=["跨资产联动分析"])


@router.get("/prices", response_model=List[AssetPrice])
async def get_asset_prices():
    """获取核心资产价格快照

    返回全球主要资产的当前价格和涨跌幅：
    - 股指：标普500、纳斯达克、上证、深证、恒生
    - 债券：美债10Y/2Y、中债10Y
    - 汇率：美元指数、美元/人民币、美元/日元
    - 商品：黄金、铜、原油
    - 波动率：VIX
    """
    try:
        result = await cross_asset_service.get_asset_prices()
        logger.info("Asset prices fetched", count=len(result))
        return result
    except Exception as e:
        logger.error("Failed to fetch asset prices", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取资产价格失败: {str(e)}")


@router.get("/risk-appetite", response_model=RiskAppetiteSignal)
async def get_risk_appetite():
    """获取市场风险偏好信号

    基于多资产表现判断市场 Risk-On/Risk-Off 状态：
    - risk_on: 风险偏好上升，资金流向风险资产
    - risk_off: 避险情绪主导，资金流向避险资产
    - neutral: 市场情绪中性

    评分范围：-100（极度避险）到 100（极度冒险）
    """
    try:
        result = await cross_asset_service.calculate_risk_appetite()
        logger.info(
            "Risk appetite calculated",
            regime=result.regime,
            score=result.score,
        )
        return result
    except Exception as e:
        logger.error("Failed to calculate risk appetite", error=str(e))
        raise HTTPException(status_code=500, detail=f"计算风险偏好失败: {str(e)}")


@router.get("/divergences", response_model=List[CrossAssetDivergence])
async def get_divergences():
    """检测跨资产背离信号

    识别资产间的异常背离：
    - stock_bond: 股债背离
    - stock_fx: 股汇背离
    - commodity_equity: 商品与股票背离
    - gold_fx: 黄金与美元背离

    背离通常预示市场即将发生调整
    """
    try:
        result = await cross_asset_service.detect_divergences()
        logger.info("Divergences detected", count=len(result))
        return result
    except Exception as e:
        logger.error("Failed to detect divergences", error=str(e))
        raise HTTPException(status_code=500, detail=f"检测背离失败: {str(e)}")


@router.get("/correlations", response_model=List[AssetCorrelation])
async def get_correlations():
    """获取关键资产相关性

    返回主要资产对的短期相关性：
    - 股债相关性
    - 股波相关性（SPX vs VIX）
    - 股金相关性
    - 金美相关性（黄金 vs 美元）
    - A股汇率相关性
    - 铜股相关性
    """
    try:
        prices = await cross_asset_service.get_asset_prices()
        result = cross_asset_service.calculate_correlations(prices)
        logger.info("Correlations calculated", count=len(result))
        return result
    except Exception as e:
        logger.error("Failed to calculate correlations", error=str(e))
        raise HTTPException(status_code=500, detail=f"计算相关性失败: {str(e)}")


@router.get("/analysis", response_model=CrossAssetAnalysisResult)
async def get_full_analysis():
    """获取完整跨资产分析

    综合分析返回：
    - 资产价格快照
    - 风险偏好信号
    - 关键相关性
    - 背离信号
    - 市场叙事
    - 可操作建议
    """
    try:
        result = await cross_asset_service.get_full_analysis()
        logger.info(
            "Full cross-asset analysis completed",
            regime=result.risk_appetite.regime,
            divergences=len(result.divergences),
        )
        return result
    except Exception as e:
        logger.error("Failed to get full analysis", error=str(e))
        raise HTTPException(status_code=500, detail=f"完整分析失败: {str(e)}")
