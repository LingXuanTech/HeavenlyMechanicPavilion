"""
政策-行业板块映射 API 端点

提供：
- 行业政策状态查询
- 个股政策影响评估
- 政策情绪分析
- 高敏感度行业筛选
"""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field
import structlog

from services.policy_sector_service import (
    policy_sector_service,
    PolicySentiment,
    PolicyStance,
    PolicyEvent,
)

router = APIRouter(prefix="/policy", tags=["Policy"])
logger = structlog.get_logger()


# ============ 响应模型 ============

class SectorPolicyResponse(BaseModel):
    """行业政策响应"""
    sector_code: str
    sector_name: str
    policy_stance: str
    sentiment_score: int
    sensitivity: int
    key_policies: List[str]
    risks: List[str]
    catalysts: List[str]


class StockPolicyImpactResponse(BaseModel):
    """个股政策影响响应"""
    symbol: str
    name: str
    primary_sector: str
    secondary_sectors: List[str]
    policy_impact: str
    sentiment_score: int
    sector_impacts: List[dict]
    key_policies: List[str]
    risks: List[str]
    catalysts: List[str]


class PolicyEventResponse(BaseModel):
    """政策事件响应"""
    id: str
    title: str
    source: str
    publish_date: str
    sectors: List[str]
    sentiment: str
    sentiment_score: int
    summary: str
    keywords: List[str]
    impact_level: str


class PolicyTextAnalysisRequest(BaseModel):
    """政策文本分析请求"""
    text: str = Field(..., min_length=10, max_length=5000, description="政策文本内容")


class PolicyTextAnalysisResponse(BaseModel):
    """政策文本分析响应"""
    sentiment: str
    sentiment_score: int
    related_sectors: List[str]
    interpretation: str


class HighSensitivitySectorResponse(BaseModel):
    """高敏感度行业响应"""
    sector: str
    sensitivity: int
    policy_stance: str
    sentiment_score: int


# ============ API 端点 ============

@router.get("/sectors", response_model=List[SectorPolicyResponse])
async def get_all_sector_policies():
    """获取所有行业政策状态概览

    返回预定义的政策敏感行业列表及其当前政策状态。
    """
    policies = policy_sector_service.get_all_sector_policies()

    return [
        SectorPolicyResponse(
            sector_code=p.sector_code,
            sector_name=p.sector_name,
            policy_stance=p.policy_stance.value,
            sentiment_score=p.sentiment_score,
            sensitivity=p.sensitivity,
            key_policies=p.key_policies,
            risks=p.risks,
            catalysts=p.catalysts,
        )
        for p in policies.values()
    ]


@router.get("/sectors/{sector}", response_model=SectorPolicyResponse)
async def get_sector_policy(sector: str):
    """获取指定行业的政策状态

    Args:
        sector: 行业名称（如：房地产、新能源、半导体）

    支持的行业别名：
    - 房地产：地产、楼市、房产
    - 半导体：芯片、集成电路、IC
    - 新能源：光伏、风电、锂电、储能
    - 医药生物：医药、制药、生物医药、医疗
    """
    policy = policy_sector_service.get_sector_policy(sector)

    if not policy:
        raise HTTPException(
            status_code=404,
            detail=f"未找到行业 '{sector}' 的政策信息。支持的行业：房地产、互联网、新能源、半导体、医药生物、银行、教育、军工、汽车"
        )

    return SectorPolicyResponse(
        sector_code=policy.sector_code,
        sector_name=policy.sector_name,
        policy_stance=policy.policy_stance.value,
        sentiment_score=policy.sentiment_score,
        sensitivity=policy.sensitivity,
        key_policies=policy.key_policies,
        risks=policy.risks,
        catalysts=policy.catalysts,
    )


@router.get("/stock/{symbol}", response_model=StockPolicyImpactResponse)
async def get_stock_policy_impact(symbol: str):
    """获取个股受政策影响的综合评估

    根据股票所属行业板块，评估其受政策影响的程度和方向。

    Args:
        symbol: 股票代码（如 600519.SH, 000001.SZ）

    Returns:
        综合政策影响评估，包括：
        - policy_impact: 政策情绪（strong_bullish/bullish/neutral/bearish/strong_bearish）
        - sentiment_score: 情绪分数（-100 到 +100）
        - sector_impacts: 各关联行业的影响明细
        - key_policies/risks/catalysts: 核心政策、风险、催化剂
    """
    result = policy_sector_service.get_stock_policy_impact(symbol)

    if result.get("policy_impact") == "unknown":
        raise HTTPException(
            status_code=404,
            detail=result.get("message", "无法获取股票信息")
        )

    return StockPolicyImpactResponse(**result)


@router.get("/high-sensitivity", response_model=List[HighSensitivitySectorResponse])
async def get_high_sensitivity_sectors(
    threshold: int = Query(default=80, ge=0, le=100, description="敏感度阈值")
):
    """获取高政策敏感度行业列表

    政策敏感度反映行业受政策影响的程度（0-100）。
    高敏感度行业（>80）包括：教育、房地产、半导体等。

    Args:
        threshold: 敏感度阈值（默认 80）
    """
    sectors = policy_sector_service.get_high_sensitivity_sectors(threshold)
    policies = policy_sector_service.get_all_sector_policies()

    return [
        HighSensitivitySectorResponse(
            sector=sector,
            sensitivity=sensitivity,
            policy_stance=policies[sector].policy_stance.value,
            sentiment_score=policies[sector].sentiment_score,
        )
        for sector, sensitivity in sectors
        if sector in policies
    ]


@router.get("/sentiment/{sentiment}", response_model=List[str])
async def get_sectors_by_sentiment(
    sentiment: str = Path(..., description="政策情绪：strong_bullish/bullish/neutral/bearish/strong_bearish")
):
    """按政策情绪筛选行业

    Args:
        sentiment: 政策情绪分类
            - strong_bullish: 重大利好（分数 >= 50）
            - bullish: 利好（20 <= 分数 < 50）
            - neutral: 中性（-20 <= 分数 < 20）
            - bearish: 利空（-50 <= 分数 < -20）
            - strong_bearish: 重大利空（分数 < -50）

    Returns:
        符合条件的行业列表
    """
    try:
        sentiment_enum = PolicySentiment(sentiment)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"无效的情绪类型: {sentiment}。有效值：strong_bullish, bullish, neutral, bearish, strong_bearish"
        )

    return policy_sector_service.get_sectors_by_sentiment(sentiment_enum)


@router.post("/analyze-text", response_model=PolicyTextAnalysisResponse)
async def analyze_policy_text(request: PolicyTextAnalysisRequest):
    """分析政策文本的情绪

    对输入的政策文本进行情绪分析，识别利好/利空关键词，
    并自动关联影响的行业板块。

    Args:
        text: 政策文本内容（10-5000字）

    Returns:
        - sentiment: 情绪分类
        - sentiment_score: 情绪分数 (-100 到 +100)
        - related_sectors: 关联的行业板块
        - interpretation: 解读说明
    """
    sentiment, score, sectors = policy_sector_service.analyze_policy_text(request.text)

    # 生成解读
    if score >= 50:
        interpretation = "该政策文本呈现明显利好信号，包含多个支持性关键词。"
    elif score >= 20:
        interpretation = "该政策文本整体偏积极，但力度有限。"
    elif score >= -20:
        interpretation = "该政策文本态度中性，无明显政策倾向。"
    elif score >= -50:
        interpretation = "该政策文本包含一定监管信号，需关注执行力度。"
    else:
        interpretation = "该政策文本呈现明显利空信号，包含多个限制性关键词。"

    if sectors:
        interpretation += f" 主要影响行业：{', '.join(sectors)}。"

    return PolicyTextAnalysisResponse(
        sentiment=sentiment.value,
        sentiment_score=score,
        related_sectors=sectors,
        interpretation=interpretation,
    )


@router.get("/events", response_model=List[PolicyEventResponse])
async def get_recent_policy_events(
    sector: Optional[str] = Query(None, description="按行业筛选"),
    days: int = Query(default=30, ge=1, le=365, description="天数范围"),
    limit: int = Query(default=20, ge=1, le=100, description="返回数量"),
):
    """获取近期政策事件

    Args:
        sector: 行业筛选（可选）
        days: 天数范围（默认 30 天）
        limit: 返回数量限制（默认 20 条）
    """
    events = policy_sector_service.get_recent_policy_events(
        sector=sector,
        days=days,
        limit=limit,
    )

    return [
        PolicyEventResponse(
            id=e.id,
            title=e.title,
            source=e.source,
            publish_date=e.publish_date.isoformat(),
            sectors=e.sectors,
            sentiment=e.sentiment.value,
            sentiment_score=e.sentiment_score,
            summary=e.summary,
            keywords=e.keywords,
            impact_level=e.impact_level,
        )
        for e in events
    ]


@router.get("/calendar")
async def get_policy_calendar():
    """获取政策日历

    返回近期重要的政策事件和监管日程。
    """
    from datetime import datetime
    today = datetime.now()
    year = today.year
    month = today.month

    calendar_events = [
        {
            "name": "全国两会",
            "date_range": f"{year}年3月3-15日",
            "importance": "极高",
            "description": "全国人大和政协会议，发布政府工作报告，确定全年经济目标",
            "sectors_affected": ["全行业"],
        },
        {
            "name": "中央经济工作会议",
            "date_range": f"{year}年12月中旬",
            "importance": "极高",
            "description": "总结全年经济工作，部署来年经济政策基调",
            "sectors_affected": ["全行业"],
        },
        {
            "name": "政治局会议",
            "date_range": "每季度末（4/7/10/12月）",
            "importance": "高",
            "description": "分析经济形势，部署下一阶段工作",
            "sectors_affected": ["房地产", "金融", "科技"],
        },
        {
            "name": "MLF 操作",
            "date_range": "每月15日左右",
            "importance": "高",
            "description": "央行中期借贷便利操作，影响市场利率",
            "sectors_affected": ["银行", "房地产"],
        },
        {
            "name": "LPR 报价",
            "date_range": "每月20日",
            "importance": "高",
            "description": "贷款市场报价利率，影响房贷和企业贷款成本",
            "sectors_affected": ["银行", "房地产"],
        },
        {
            "name": "年报披露期",
            "date_range": f"{year}年1-4月",
            "importance": "高",
            "description": "A股年报披露期，关注业绩雷和超预期",
            "sectors_affected": ["全行业"],
        },
    ]

    return {
        "current_date": today.strftime("%Y年%m月%d日"),
        "events": calendar_events,
        "upcoming_politburo": _get_next_politburo_month(month),
    }


def _get_next_politburo_month(current_month: int) -> str:
    """获取下一次政治局会议月份"""
    politburo_months = [4, 7, 10, 12]
    for m in politburo_months:
        if m >= current_month:
            return f"{m}月"
    return "次年4月"
