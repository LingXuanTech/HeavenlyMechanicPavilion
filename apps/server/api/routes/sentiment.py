"""舆情分析 API 路由

提供社交媒体舆情聚合、情绪分析等功能。
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import structlog

from services.sentiment_aggregator import sentiment_aggregator

router = APIRouter(prefix="/sentiment", tags=["Sentiment"])
logger = structlog.get_logger(__name__)


# ============ Request/Response Models ============


class SentimentRequest(BaseModel):
    """舆情分析请求"""
    symbol: str
    market: str = "US"
    days_back: int = 7
    max_posts_per_source: int = 20


class SentimentResponse(BaseModel):
    """舆情分析响应"""
    symbol: str
    market: str
    overall_sentiment: str
    sentiment_score: float
    confidence: int
    total_posts: int
    bullish_count: int
    bearish_count: int
    neutral_count: int


# ============ 舆情分析端点 ============


@router.post("/analyze")
async def analyze_sentiment(request: SentimentRequest):
    """分析股票舆情

    聚合多个社交媒体和新闻来源，分析市场情绪。
    """
    try:
        summary = await sentiment_aggregator.aggregate_sentiment(
            symbol=request.symbol,
            market=request.market,
            days_back=request.days_back,
            max_posts_per_source=request.max_posts_per_source,
        )

        return {
            "status": "success",
            "data": summary.to_dict(),
        }

    except Exception as e:
        logger.error("Sentiment analysis failed", error=str(e), symbol=request.symbol)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}")
async def get_sentiment(
    symbol: str,
    market: str = Query(default="US"),
    days_back: int = Query(default=7, ge=1, le=30),
):
    """快速获取股票舆情摘要"""
    try:
        summary = await sentiment_aggregator.aggregate_sentiment(
            symbol=symbol,
            market=market,
            days_back=days_back,
            max_posts_per_source=15,
        )

        return {
            "status": "success",
            "symbol": symbol,
            "market": market,
            "overall_sentiment": summary.overall_sentiment,
            "sentiment_score": summary.sentiment_score,
            "confidence": summary.confidence,
            "statistics": {
                "total_posts": summary.total_posts,
                "bullish_count": summary.bullish_count,
                "bearish_count": summary.bearish_count,
                "neutral_count": summary.neutral_count,
            },
            "top_keywords": summary.top_keywords[:10],
            "hot_topics": summary.hot_topics[:5],
            "analysis_time": summary.analysis_time,
        }

    except Exception as e:
        logger.error("Get sentiment failed", error=str(e), symbol=symbol)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/score")
async def get_sentiment_score(
    symbol: str,
    market: str = Query(default="US"),
):
    """获取股票情绪分数（简化接口）"""
    try:
        summary = await sentiment_aggregator.aggregate_sentiment(
            symbol=symbol,
            market=market,
            days_back=7,
            max_posts_per_source=10,
        )

        # 情绪分数解读
        if summary.sentiment_score > 0.4:
            interpretation = "极度乐观"
            signal = "警惕过热"
        elif summary.sentiment_score > 0.2:
            interpretation = "偏向乐观"
            signal = "正面"
        elif summary.sentiment_score > -0.2:
            interpretation = "中性"
            signal = "观望"
        elif summary.sentiment_score > -0.4:
            interpretation = "偏向悲观"
            signal = "谨慎"
        else:
            interpretation = "极度悲观"
            signal = "关注超跌"

        return {
            "status": "success",
            "symbol": symbol,
            "sentiment_score": summary.sentiment_score,
            "sentiment_level": summary.overall_sentiment,
            "interpretation": interpretation,
            "signal": signal,
            "confidence": summary.confidence,
            "sample_size": summary.total_posts,
        }

    except Exception as e:
        logger.error("Get sentiment score failed", error=str(e), symbol=symbol)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compare")
async def compare_sentiments(
    symbols: str = Query(..., description="Comma-separated symbols"),
    market: str = Query(default="US"),
):
    """比较多个股票的舆情"""
    try:
        symbol_list = [s.strip() for s in symbols.split(",")][:10]  # 最多 10 个
        results = []

        for symbol in symbol_list:
            try:
                summary = await sentiment_aggregator.aggregate_sentiment(
                    symbol=symbol,
                    market=market,
                    days_back=7,
                    max_posts_per_source=10,
                )
                results.append({
                    "symbol": symbol,
                    "sentiment_score": summary.sentiment_score,
                    "sentiment_level": summary.overall_sentiment,
                    "confidence": summary.confidence,
                    "total_posts": summary.total_posts,
                    "bullish_ratio": summary.bullish_count / summary.total_posts if summary.total_posts > 0 else 0,
                })
            except Exception as e:
                results.append({
                    "symbol": symbol,
                    "error": str(e),
                })

        # 按情绪分数排序
        valid_results = [r for r in results if "error" not in r]
        valid_results.sort(key=lambda x: x["sentiment_score"], reverse=True)

        return {
            "status": "success",
            "market": market,
            "comparison": results,
            "ranking": [r["symbol"] for r in valid_results],
            "most_bullish": valid_results[0] if valid_results else None,
            "most_bearish": valid_results[-1] if valid_results else None,
        }

    except Exception as e:
        logger.error("Compare sentiments failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/posts")
async def get_sentiment_posts(
    symbol: str,
    market: str = Query(default="US"),
    limit: int = Query(default=20, ge=1, le=50),
):
    """获取股票的舆情帖子样本"""
    try:
        summary = await sentiment_aggregator.aggregate_sentiment(
            symbol=symbol,
            market=market,
            days_back=7,
            max_posts_per_source=limit,
        )

        # 按情绪强度排序
        sorted_posts = sorted(
            summary.sample_posts,
            key=lambda p: abs(p.sentiment_score),
            reverse=True,
        )

        return {
            "status": "success",
            "symbol": symbol,
            "total_posts": summary.total_posts,
            "posts": [
                {
                    "source": p.source,
                    "title": p.title,
                    "content": p.content[:300] + "..." if len(p.content) > 300 else p.content,
                    "url": p.url,
                    "sentiment_score": p.sentiment_score,
                    "sentiment_label": "bullish" if p.sentiment_score > 0.2 else "bearish" if p.sentiment_score < -0.2 else "neutral",
                    "keywords": p.keywords,
                }
                for p in sorted_posts[:limit]
            ],
        }

    except Exception as e:
        logger.error("Get sentiment posts failed", error=str(e), symbol=symbol)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/keywords")
async def get_sentiment_keywords(
    symbol: str,
    market: str = Query(default="US"),
):
    """获取股票舆情热点关键词"""
    try:
        summary = await sentiment_aggregator.aggregate_sentiment(
            symbol=symbol,
            market=market,
            days_back=7,
            max_posts_per_source=20,
        )

        return {
            "status": "success",
            "symbol": symbol,
            "top_keywords": summary.top_keywords,
            "hot_topics": summary.hot_topics,
            "keyword_count": len(summary.top_keywords),
        }

    except Exception as e:
        logger.error("Get sentiment keywords failed", error=str(e), symbol=symbol)
        raise HTTPException(status_code=500, detail=str(e))
