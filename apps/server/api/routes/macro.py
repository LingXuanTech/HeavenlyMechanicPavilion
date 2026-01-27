"""宏观经济数据 API 路由"""
import structlog
from fastapi import APIRouter, HTTPException
from typing import List, Optional

from services.macro_service import (
    MacroDataService,
    MacroOverview,
    MacroIndicator,
    MacroImpact,
    MacroAnalysisResult
)

router = APIRouter(prefix="/macro", tags=["Macro"])
logger = structlog.get_logger()


@router.get("/overview", response_model=MacroOverview)
async def get_macro_overview():
    """
    获取宏观经济概览

    返回主要宏观经济指标：
    - 联邦基金利率
    - GDP 增长率
    - CPI
    - 失业率
    - 10年期国债收益率
    - VIX 恐慌指数
    - 美元指数 (DXY)
    """
    try:
        overview = await MacroDataService.get_macro_overview()
        return overview
    except Exception as e:
        logger.error("Failed to get macro overview", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取宏观数据失败: {str(e)}")


@router.get("/indicator/{indicator_name}")
async def get_indicator(indicator_name: str):
    """
    获取单个宏观指标

    支持的指标：
    - fed_rate: 联邦基金利率
    - gdp_growth: GDP增长率
    - cpi: 消费者价格指数
    - unemployment: 失业率
    - treasury_10y: 10年期国债
    - vix: 恐慌指数
    - dxy: 美元指数
    """
    overview = await MacroDataService.get_macro_overview()

    indicator = getattr(overview, indicator_name, None)
    if not indicator:
        raise HTTPException(
            status_code=404,
            detail=f"指标 '{indicator_name}' 不存在或数据不可用"
        )

    return indicator


@router.get("/impact-analysis")
async def get_macro_impact_analysis(market: str = "US"):
    """
    获取宏观因素对市场的影响分析

    分析当前宏观环境对不同市场的潜在影响。
    """
    overview = await MacroDataService.get_macro_overview()

    impacts: List[MacroImpact] = []

    # 分析利率影响
    if overview.fed_rate:
        rate = overview.fed_rate.value
        if rate > 5:
            impacts.append(MacroImpact(
                indicator="联邦基金利率",
                impact_level="High",
                direction="Bearish",
                reasoning=f"高利率环境 ({rate}%) 增加企业融资成本，压制股票估值，资金流向债券市场"
            ))
        elif rate < 2:
            impacts.append(MacroImpact(
                indicator="联邦基金利率",
                impact_level="High",
                direction="Bullish",
                reasoning=f"低利率环境 ({rate}%) 降低融资成本，推动风险资产估值扩张"
            ))
        else:
            impacts.append(MacroImpact(
                indicator="联邦基金利率",
                impact_level="Medium",
                direction="Neutral",
                reasoning=f"利率处于中性区间 ({rate}%)，对市场影响有限"
            ))

    # 分析 VIX 影响
    if overview.vix:
        vix = overview.vix.value
        if vix > 25:
            impacts.append(MacroImpact(
                indicator="VIX 恐慌指数",
                impact_level="High",
                direction="Bearish",
                reasoning=f"VIX 高企 ({vix})，市场恐慌情绪浓厚，波动风险加大"
            ))
        elif vix < 15:
            impacts.append(MacroImpact(
                indicator="VIX 恐慌指数",
                impact_level="Low",
                direction="Bullish",
                reasoning=f"VIX 处于低位 ({vix})，市场情绪稳定，利于风险资产"
            ))

    # 分析失业率影响
    if overview.unemployment:
        unemp = overview.unemployment.value
        if unemp > 5:
            impacts.append(MacroImpact(
                indicator="失业率",
                impact_level="Medium",
                direction="Bearish",
                reasoning=f"失业率偏高 ({unemp}%)，消费能力下降，经济衰退风险"
            ))
        elif unemp < 4:
            impacts.append(MacroImpact(
                indicator="失业率",
                impact_level="Medium",
                direction="Bullish",
                reasoning=f"就业市场强劲 ({unemp}%)，消费支撑经济增长"
            ))

    # 分析美元影响
    if overview.dxy:
        dxy_trend = overview.dxy.trend
        if market in ["CN", "HK"] and dxy_trend == "up":
            impacts.append(MacroImpact(
                indicator="美元指数",
                impact_level="Medium",
                direction="Bearish",
                reasoning="美元走强，新兴市场资金外流压力增加"
            ))
        elif market == "US" and dxy_trend == "up":
            impacts.append(MacroImpact(
                indicator="美元指数",
                impact_level="Low",
                direction="Neutral",
                reasoning="美元走强利好进口，但压制跨国企业海外收益"
            ))

    # 生成风险因素和机会
    risk_factors = []
    opportunities = []

    for impact in impacts:
        if impact.direction == "Bearish" and impact.impact_level in ["High", "Medium"]:
            risk_factors.append(f"{impact.indicator}: {impact.reasoning}")
        elif impact.direction == "Bullish" and impact.impact_level in ["High", "Medium"]:
            opportunities.append(f"{impact.indicator}: {impact.reasoning}")

    # 市场展望
    bullish_count = sum(1 for i in impacts if i.direction == "Bullish")
    bearish_count = sum(1 for i in impacts if i.direction == "Bearish")

    if bullish_count > bearish_count + 1:
        market_outlook = "宏观环境整体偏利好，可适度增加风险敞口"
    elif bearish_count > bullish_count + 1:
        market_outlook = "宏观环境存在压力，建议保持谨慎，控制仓位"
    else:
        market_outlook = "宏观环境中性，建议维持现有配置，关注边际变化"

    return MacroAnalysisResult(
        overview=overview,
        impacts=impacts,
        market_outlook=market_outlook,
        risk_factors=risk_factors,
        opportunities=opportunities
    )


@router.post("/refresh")
async def refresh_macro_data():
    """强制刷新宏观数据缓存"""
    MacroDataService.clear_cache()
    overview = await MacroDataService.get_macro_overview()

    return {
        "status": "success",
        "message": "宏观数据已刷新",
        "sentiment": overview.sentiment,
        "last_updated": overview.last_updated
    }
