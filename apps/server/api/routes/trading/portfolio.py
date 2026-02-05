"""组合分析 API 路由"""
import structlog
import numpy as np
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from services.data_router import MarketRouter

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])
logger = structlog.get_logger()


class CorrelationRequest(BaseModel):
    """相关性计算请求"""
    symbols: List[str]
    period: str = "1mo"  # 1d, 5d, 1mo, 3mo, 6mo, 1y


class RiskCluster(BaseModel):
    """风险聚类"""
    stocks: List[str]
    avg_correlation: float
    risk_level: str


class CorrelationResult(BaseModel):
    """相关性矩阵结果"""
    symbols: List[str]
    matrix: List[List[float]]
    returns_summary: Dict[str, Dict[str, float]]


class PortfolioAnalysis(BaseModel):
    """组合分析结果"""
    correlation: CorrelationResult
    diversification_score: float
    risk_clusters: List[RiskCluster]
    recommendations: List[str]


@router.post("/correlation", response_model=CorrelationResult)
async def calculate_correlation(request: CorrelationRequest):
    """
    计算股票组合的相关性矩阵

    基于历史收益率计算皮尔逊相关系数。
    """
    if len(request.symbols) < 2:
        raise HTTPException(status_code=400, detail="至少需要 2 个股票代码")

    if len(request.symbols) > 20:
        raise HTTPException(status_code=400, detail="最多支持 20 个股票")

    try:
        # 获取所有股票的历史数据
        returns_data: Dict[str, List[float]] = {}
        returns_summary: Dict[str, Dict[str, float]] = {}

        for symbol in request.symbols:
            try:
                history = await MarketRouter.get_history(symbol, request.period)
                if len(history) < 5:
                    logger.warning("Insufficient history data", symbol=symbol)
                    continue

                # 计算日收益率
                closes = [h.close for h in history]
                returns = []
                for i in range(1, len(closes)):
                    if closes[i - 1] != 0:
                        ret = (closes[i] - closes[i - 1]) / closes[i - 1]
                        returns.append(ret)

                if len(returns) > 0:
                    returns_data[symbol] = returns
                    returns_summary[symbol] = {
                        "mean_return": float(np.mean(returns) * 100),
                        "volatility": float(np.std(returns) * 100),
                        "total_return": float((closes[-1] / closes[0] - 1) * 100) if closes[0] != 0 else 0,
                        "data_points": len(returns)
                    }

            except Exception as e:
                logger.warning("Failed to get history for symbol", symbol=symbol, error=str(e))
                continue

        # 确保至少有 2 个有效数据
        valid_symbols = list(returns_data.keys())
        if len(valid_symbols) < 2:
            raise HTTPException(
                status_code=400,
                detail=f"无法获取足够的历史数据。有效股票: {valid_symbols}"
            )

        # 对齐数据长度
        min_length = min(len(returns_data[s]) for s in valid_symbols)
        aligned_returns = {s: returns_data[s][-min_length:] for s in valid_symbols}

        # 计算相关性矩阵
        n = len(valid_symbols)
        matrix = np.zeros((n, n))

        for i, s1 in enumerate(valid_symbols):
            for j, s2 in enumerate(valid_symbols):
                if i == j:
                    matrix[i][j] = 1.0
                else:
                    corr = np.corrcoef(aligned_returns[s1], aligned_returns[s2])[0, 1]
                    matrix[i][j] = float(corr) if not np.isnan(corr) else 0.0

        return CorrelationResult(
            symbols=valid_symbols,
            matrix=matrix.tolist(),
            returns_summary=returns_summary
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Correlation calculation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"计算失败: {str(e)}")


@router.post("/analyze", response_model=PortfolioAnalysis)
async def analyze_portfolio(request: CorrelationRequest):
    """
    完整的组合分析

    包括相关性矩阵、分散化评分、风险聚类和建议。
    """
    # 先计算相关性
    correlation = await calculate_correlation(request)

    matrix = np.array(correlation.matrix)
    n = len(correlation.symbols)

    # 1. 计算分散化评分 (0-100)
    # 基于平均相关性：相关性越低，分散化越好
    if n > 1:
        # 获取上三角矩阵（不含对角线）
        upper_triangle = matrix[np.triu_indices(n, k=1)]
        avg_corr = np.mean(np.abs(upper_triangle))
        # 转换为分散化评分：相关性 0 = 100分，相关性 1 = 0分
        diversification_score = float((1 - avg_corr) * 100)
    else:
        diversification_score = 0.0

    # 2. 识别风险聚类（高度相关的股票组）
    risk_clusters = []
    threshold = 0.7  # 相关性阈值

    visited = set()
    for i in range(n):
        if i in visited:
            continue

        cluster = [correlation.symbols[i]]
        visited.add(i)

        for j in range(i + 1, n):
            if j not in visited and matrix[i][j] >= threshold:
                cluster.append(correlation.symbols[j])
                visited.add(j)

        if len(cluster) > 1:
            avg_cluster_corr = np.mean([
                matrix[correlation.symbols.index(s1)][correlation.symbols.index(s2)]
                for s1 in cluster for s2 in cluster if s1 != s2
            ])
            risk_clusters.append({
                "stocks": cluster,
                "avg_correlation": float(avg_cluster_corr),
                "risk_level": "High" if avg_cluster_corr > 0.8 else "Moderate"
            })

    # 3. 生成建议
    recommendations = []

    if diversification_score < 30:
        recommendations.append("⚠️ 组合高度集中，建议增加不同行业或市场的股票以降低系统性风险")
    elif diversification_score < 60:
        recommendations.append("📊 组合分散度中等，可考虑增加负相关或低相关资产")
    else:
        recommendations.append("✅ 组合分散度良好，风险分布较为均衡")

    if risk_clusters:
        cluster_stocks = [", ".join(c["stocks"]) for c in risk_clusters]
        recommendations.append(f"🔗 发现高相关性股票群: {'; '.join(cluster_stocks)}。这些股票可能同涨同跌")

    # 基于收益率数据的建议
    if correlation.returns_summary:
        high_vol = [s for s, data in correlation.returns_summary.items() if data.get("volatility", 0) > 3]
        if high_vol:
            recommendations.append(f"📈 高波动股票: {', '.join(high_vol)}。注意仓位控制")

        negative_return = [s for s, data in correlation.returns_summary.items() if data.get("total_return", 0) < -10]
        if negative_return:
            recommendations.append(f"📉 近期表现不佳: {', '.join(negative_return)}。建议关注基本面变化")

    return PortfolioAnalysis(
        correlation=correlation,
        diversification_score=round(diversification_score, 1),
        risk_clusters=risk_clusters,
        recommendations=recommendations
    )


@router.get("/quick-check")
async def quick_portfolio_check(
    symbols: str = Query(..., description="逗号分隔的股票代码列表")
):
    """
    快速组合检查

    简化版接口，返回基本的分散化评分。
    """
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]

    if len(symbol_list) < 2:
        return {"diversification_score": 0, "message": "至少需要 2 个股票"}

    try:
        request = CorrelationRequest(symbols=symbol_list)
        analysis = await analyze_portfolio(request)

        return {
            "diversification_score": analysis.diversification_score,
            "risk_clusters_count": len(analysis.risk_clusters),
            "top_recommendation": analysis.recommendations[0] if analysis.recommendations else None
        }
    except HTTPException as e:
        return {"error": e.detail}
    except Exception as e:
        return {"error": str(e)}
