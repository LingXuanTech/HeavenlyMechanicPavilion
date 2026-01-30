"""央行 NLP 分析 API 路由

提供央行报告和讲话的语义分析接口
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Optional
from pydantic import BaseModel, Field
import structlog

from services.central_bank_nlp_service import (
    central_bank_nlp_service,
    PolicySentiment,
    CentralBankStatement,
    CentralBankAnalysisResult,
    PolicyKeyword,
    PolicyChangeSignal,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/central-bank", tags=["央行 NLP 分析"])


class TextAnalysisRequest(BaseModel):
    """文本分析请求"""
    text: str = Field(..., min_length=10, description="要分析的文本")
    source: Optional[str] = Field("PBOC", description="来源: PBOC/FED/ECB/BOJ")
    title: Optional[str] = Field("", description="标题")


class CompareRequest(BaseModel):
    """对比分析请求"""
    current_text: str = Field(..., min_length=10, description="当前声明文本")
    previous_text: str = Field(..., min_length=10, description="上次声明文本")


@router.post("/analyze-sentiment", response_model=PolicySentiment)
async def analyze_sentiment(request: TextAnalysisRequest):
    """分析文本的政策情绪

    识别文本的鹰派/鸽派倾向，返回：
    - 政策立场（hawkish/dovish/neutral）
    - 置信度
    - 情绪评分（-1 到 1）
    - 鹰派/鸽派信号列表
    """
    try:
        result = central_bank_nlp_service.analyze_sentiment(request.text)
        logger.info(
            "Sentiment analyzed",
            stance=result.stance,
            score=result.score,
        )
        return result
    except Exception as e:
        logger.error("Failed to analyze sentiment", error=str(e))
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/extract-keywords", response_model=list[PolicyKeyword])
async def extract_keywords(request: TextAnalysisRequest):
    """提取政策关键词

    从文本中提取与货币政策相关的关键词，包括：
    - 关键词及出现次数
    - 情绪倾向
    - 重要性等级
    """
    try:
        result = central_bank_nlp_service.extract_keywords(request.text)
        logger.info("Keywords extracted", count=len(result))
        return result
    except Exception as e:
        logger.error("Failed to extract keywords", error=str(e))
        raise HTTPException(status_code=500, detail=f"提取关键词失败: {str(e)}")


@router.post("/analyze-statement", response_model=CentralBankStatement)
async def analyze_statement(request: TextAnalysisRequest):
    """分析央行声明

    对央行声明进行完整分析，返回：
    - 情绪分析
    - 关键表述
    - 政策信号
    - 市场含义
    """
    try:
        result = central_bank_nlp_service.analyze_statement(
            text=request.text,
            source=request.source,
            title=request.title,
        )
        logger.info(
            "Statement analyzed",
            source=request.source,
            stance=result.sentiment.stance,
        )
        return result
    except Exception as e:
        logger.error("Failed to analyze statement", error=str(e))
        raise HTTPException(status_code=500, detail=f"分析声明失败: {str(e)}")


@router.post("/predict-policy-change", response_model=list[PolicyChangeSignal])
async def predict_policy_change(request: TextAnalysisRequest):
    """预测政策变化

    基于文本内容预测可能的政策变化：
    - 加息/降息预期
    - QE/QT 预期
    - 变化时间线
    - 市场影响
    """
    try:
        result = central_bank_nlp_service.predict_policy_change(request.text)
        logger.info("Policy change predicted", signals=len(result))
        return result
    except Exception as e:
        logger.error("Failed to predict policy change", error=str(e))
        raise HTTPException(status_code=500, detail=f"预测失败: {str(e)}")


@router.post("/compare-statements")
async def compare_statements(request: CompareRequest):
    """对比两次声明的变化

    分析两次声明之间的政策立场变化：
    - 立场变化方向
    - 评分变化
    - 新增/删除的关键词
    - 变化解读
    """
    try:
        result = central_bank_nlp_service.compare_statements(
            current_text=request.current_text,
            previous_text=request.previous_text,
        )
        logger.info(
            "Statements compared",
            stance_change=result["stance_change"],
        )
        return result
    except Exception as e:
        logger.error("Failed to compare statements", error=str(e))
        raise HTTPException(status_code=500, detail=f"对比分析失败: {str(e)}")


@router.post("/full-analysis", response_model=CentralBankAnalysisResult)
async def get_full_analysis(
    request: TextAnalysisRequest,
    previous_text: Optional[str] = Body(None, description="上次声明（可选）")
):
    """获取完整的央行分析

    综合分析央行声明，返回：
    - 声明分析详情
    - 整体政策立场
    - 立场变化趋势
    - 政策展望
    - 变化信号预测
    - 关键词分析
    """
    try:
        result = central_bank_nlp_service.get_full_analysis(
            text=request.text,
            source=request.source,
            title=request.title,
            previous_text=previous_text,
        )
        logger.info(
            "Full analysis completed",
            stance=result.overall_stance,
            signals=len(result.change_signals),
        )
        return result
    except Exception as e:
        logger.error("Failed to get full analysis", error=str(e))
        raise HTTPException(status_code=500, detail=f"完整分析失败: {str(e)}")
