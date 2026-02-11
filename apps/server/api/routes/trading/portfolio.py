"""组合分析 API 路由"""
import structlog
import numpy as np
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field

from services.data_router import MarketRouter

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])
logger = structlog.get_logger()

PortfolioPeriod = Literal["1d", "5d", "1mo", "3mo", "6mo", "1y"]
DEFAULT_CLUSTER_THRESHOLD = 0.7
DEFAULT_MAX_SINGLE_WEIGHT = 0.45
DEFAULT_MAX_TOP2_WEIGHT = 0.65
DEFAULT_MAX_TURNOVER = 0.35


class RebalanceConstraints(BaseModel):
    """再平衡约束条件。"""

    max_single_weight: float = Field(default=DEFAULT_MAX_SINGLE_WEIGHT, ge=0.1, le=0.9)
    max_top2_weight: float = Field(default=DEFAULT_MAX_TOP2_WEIGHT, ge=0.2, le=1.0)
    max_turnover: float = Field(default=DEFAULT_MAX_TURNOVER, ge=0.0, le=1.0)
    risk_profile: Literal["conservative", "balanced", "aggressive"] = "balanced"


class CorrelationRequest(BaseModel):
    """相关性计算请求"""

    symbols: List[str]
    period: PortfolioPeriod = "1mo"
    cluster_threshold: float = Field(
        default=DEFAULT_CLUSTER_THRESHOLD,
        ge=0.5,
        le=0.95,
        description="风险聚类相关性阈值",
    )
    weights: Optional[List[float]] = Field(
        default=None,
        description="组合权重（与 symbols 顺序一致，可为任意非负数，将自动归一化）",
    )
    constraints: Optional[RebalanceConstraints] = Field(default=None, description="再平衡约束")
    enable_backtest_hint: bool = Field(default=True, description="是否返回回测请求提示")


class RiskCluster(BaseModel):
    """风险聚类"""

    stocks: List[str]
    avg_correlation: float
    risk_level: str


class ConstraintViolation(BaseModel):
    """约束触发说明。"""

    code: str
    message: str
    actual: float
    limit: float
    severity: Literal["warning", "critical"] = "warning"


class RebalanceSuggestion(BaseModel):
    """再平衡建议条目"""

    symbol: str
    current_weight: float = Field(..., ge=0.0, le=1.0)
    target_weight: float = Field(..., ge=0.0, le=1.0)
    delta_weight: float
    action: Literal["increase", "decrease", "hold"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str
    volatility: float
    avg_abs_correlation: float
    total_return: float


class BacktestSignalHint(BaseModel):
    """回测信号提示。"""

    date: str
    signal: Literal["bullish", "bearish", "neutral"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    source: str = "portfolio_rebalance"


class BacktestRequestHint(BaseModel):
    """回测请求提示。"""

    symbol: str
    signals: List[BacktestSignalHint]
    initial_capital: float = 100000
    holding_days: int = 5
    stop_loss_pct: float = -5.0
    take_profit_pct: float = 10.0
    use_historical_signals: bool = False
    days_back: int = 180


class BacktestPayloadHint(BaseModel):
    """组合分析生成的回测入参建议。"""

    strategy_name: str
    generated_at: str
    requests: List[BacktestRequestHint]


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
    rebalance_suggestions: List[RebalanceSuggestion] = Field(default_factory=list)
    recommended_turnover: float = Field(default=0.0, ge=0.0)
    constraint_violations: List[ConstraintViolation] = Field(default_factory=list)
    backtest_payload_hint: Optional[BacktestPayloadHint] = None


class QuickPortfolioCheckResponse(BaseModel):
    """快速组合检查响应"""

    diversification_score: float
    risk_clusters_count: int
    top_recommendation: Optional[str] = None
    message: Optional[str] = None


def _normalize_weights(symbols: List[str], weights: Optional[List[float]]) -> Optional[List[float]]:
    """验证并归一化组合权重。"""
    if weights is None:
        return None

    if len(weights) != len(symbols):
        raise HTTPException(status_code=400, detail="weights 长度必须与 symbols 一致")

    if any(weight < 0 for weight in weights):
        raise HTTPException(status_code=400, detail="weights 不能为负数")

    total_weight = float(sum(weights))
    if total_weight <= 0:
        raise HTTPException(status_code=400, detail="weights 总和必须大于 0")

    return [float(weight) / total_weight for weight in weights]


def _parse_weights_query(weights: Optional[str]) -> Optional[List[float]]:
    """解析 quick-check query 参数中的权重。"""
    if weights is None or not weights.strip():
        return None

    parts = [part.strip() for part in weights.split(",") if part.strip()]
    if not parts:
        return None

    try:
        return [float(part) for part in parts]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="weights 必须为逗号分隔的数字") from exc


def _build_current_weights(
    correlation_symbols: List[str],
    request_symbols: List[str],
    normalized_request_weights: Optional[List[float]],
) -> np.ndarray:
    """构建与有效 symbols 对齐的当前权重向量。"""
    n_symbols = len(correlation_symbols)
    if n_symbols == 0:
        return np.array([], dtype=float)

    if normalized_request_weights is None:
        return np.array([1.0 / n_symbols] * n_symbols, dtype=float)

    weight_map = {
        symbol: normalized_request_weights[index]
        for index, symbol in enumerate(request_symbols)
    }
    aligned_weights = np.array(
        [weight_map.get(symbol, 0.0) for symbol in correlation_symbols],
        dtype=float,
    )
    aligned_sum = float(np.sum(aligned_weights))
    if aligned_sum <= 0:
        return np.array([1.0 / n_symbols] * n_symbols, dtype=float)

    return aligned_weights / aligned_sum


def _normalize_probability_vector(weights: np.ndarray) -> np.ndarray:
    """归一化权重向量，确保总和为 1。"""
    clipped = np.clip(weights, 0.0, None)
    total = float(np.sum(clipped))
    if total <= 0:
        if len(clipped) == 0:
            return clipped
        return np.array([1.0 / len(clipped)] * len(clipped), dtype=float)
    return clipped / total


def _project_with_single_cap(weights: np.ndarray, max_single_weight: float) -> np.ndarray:
    """在上限约束下投影权重。"""
    n = len(weights)
    if n == 0:
        return weights

    result = np.zeros(n, dtype=float)
    active = set(range(n))
    remaining = 1.0
    raw = np.clip(weights, 0.0, None)

    while active and remaining > 1e-12:
        raw_sum = float(np.sum([raw[index] for index in active]))
        distributed = False

        for index in list(active):
            if raw_sum > 0:
                proposed = remaining * (raw[index] / raw_sum)
            else:
                proposed = remaining / len(active)

            if proposed >= max_single_weight - 1e-12:
                result[index] = max_single_weight
                remaining -= max_single_weight
                active.remove(index)
                distributed = True

        if not distributed:
            for index in active:
                if raw_sum > 0:
                    result[index] = remaining * (raw[index] / raw_sum)
                else:
                    result[index] = remaining / len(active)
            remaining = 0.0

    if remaining > 1e-10:
        max_index = int(np.argmax(result)) if len(result) > 0 else 0
        result[max_index] += remaining

    return _normalize_probability_vector(result)


def _apply_rebalance_constraints(
    target_weights: np.ndarray,
    current_weights: np.ndarray,
    constraints: RebalanceConstraints,
) -> tuple[np.ndarray, List[ConstraintViolation]]:
    """应用再平衡约束并返回约束触发信息。"""
    n_symbols = len(target_weights)
    if n_symbols == 0:
        return target_weights, []

    violations: List[ConstraintViolation] = []

    effective_single_cap = constraints.max_single_weight
    if effective_single_cap * n_symbols < 1.0 - 1e-9:
        effective_single_cap = 1.0 / n_symbols
        violations.append(
            ConstraintViolation(
                code="single_cap_infeasible",
                message="单票上限过低，已自动放宽到可行值",
                actual=constraints.max_single_weight,
                limit=effective_single_cap,
                severity="critical",
            )
        )

    adjusted = _normalize_probability_vector(target_weights)

    before_single_max = float(np.max(adjusted))
    if before_single_max > effective_single_cap + 1e-9:
        violations.append(
            ConstraintViolation(
                code="single_cap_applied",
                message="已按单票上限约束调整目标权重",
                actual=before_single_max,
                limit=effective_single_cap,
                severity="warning",
            )
        )
    adjusted = _project_with_single_cap(adjusted, effective_single_cap)

    if n_symbols >= 2:
        top_indices = np.argsort(adjusted)[::-1][:2]
        top2_sum = float(adjusted[top_indices[0]] + adjusted[top_indices[1]])

        if n_symbols <= 2 and constraints.max_top2_weight < 1.0 - 1e-9:
            violations.append(
                ConstraintViolation(
                    code="top2_cap_infeasible",
                    message="当前标的数量无法满足前两大仓位上限，已忽略该约束",
                    actual=top2_sum,
                    limit=constraints.max_top2_weight,
                    severity="critical",
                )
            )
        elif top2_sum > constraints.max_top2_weight + 1e-9:
            violations.append(
                ConstraintViolation(
                    code="top2_cap_applied",
                    message="已按前两大仓位上限调整目标权重",
                    actual=top2_sum,
                    limit=constraints.max_top2_weight,
                    severity="warning",
                )
            )

            excess = top2_sum - constraints.max_top2_weight
            if excess > 0 and n_symbols > 2:
                share_top_0 = adjusted[top_indices[0]] / top2_sum if top2_sum > 0 else 0.5
                reduce_top_0 = excess * share_top_0
                reduce_top_1 = excess - reduce_top_0
                adjusted[top_indices[0]] -= reduce_top_0
                adjusted[top_indices[1]] -= reduce_top_1

                other_indices = [index for index in range(n_symbols) if index not in top_indices]
                if other_indices:
                    capacities = np.array(
                        [max(0.0, effective_single_cap - adjusted[index]) for index in other_indices],
                        dtype=float,
                    )
                    capacity_sum = float(np.sum(capacities))
                    if capacity_sum > 0:
                        distribution = capacities / capacity_sum * excess
                        for offset, index in enumerate(other_indices):
                            adjusted[index] += float(distribution[offset])
                    else:
                        adjusted[top_indices[0]] += reduce_top_0
                        adjusted[top_indices[1]] += reduce_top_1

            adjusted = _project_with_single_cap(_normalize_probability_vector(adjusted), effective_single_cap)

    turnover = float(np.sum(np.abs(adjusted - current_weights)) / 2)
    if turnover > constraints.max_turnover + 1e-9:
        scale = constraints.max_turnover / turnover if turnover > 0 else 0.0
        adjusted = current_weights + (adjusted - current_weights) * scale
        adjusted = _project_with_single_cap(_normalize_probability_vector(adjusted), effective_single_cap)
        violations.append(
            ConstraintViolation(
                code="turnover_capped",
                message="已按最大换手约束收敛目标权重",
                actual=turnover,
                limit=constraints.max_turnover,
                severity="warning",
            )
        )

    final_single = float(np.max(adjusted))
    if final_single > effective_single_cap + 1e-6:
        violations.append(
            ConstraintViolation(
                code="single_cap_unmet",
                message="在当前约束组合下无法完全满足单票上限",
                actual=final_single,
                limit=effective_single_cap,
                severity="critical",
            )
        )

    if n_symbols >= 2:
        final_sorted = np.sort(adjusted)[::-1]
        final_top2 = float(final_sorted[0] + final_sorted[1])
        if final_top2 > constraints.max_top2_weight + 1e-6:
            violations.append(
                ConstraintViolation(
                    code="top2_cap_unmet",
                    message="在当前约束组合下无法完全满足前两大仓位上限",
                    actual=final_top2,
                    limit=constraints.max_top2_weight,
                    severity="critical",
                )
            )

    final_turnover = float(np.sum(np.abs(adjusted - current_weights)) / 2)
    if final_turnover > constraints.max_turnover + 1e-6:
        violations.append(
            ConstraintViolation(
                code="turnover_unmet",
                message="在当前约束组合下无法完全满足最大换手上限",
                actual=final_turnover,
                limit=constraints.max_turnover,
                severity="critical",
            )
        )

    return adjusted, violations


def _build_backtest_payload_hint(
    suggestions: List[RebalanceSuggestion],
    constraints: RebalanceConstraints,
) -> BacktestPayloadHint:
    """根据再平衡建议生成回测参数提示。"""
    profile_to_holding_days = {
        "conservative": 10,
        "balanced": 7,
        "aggressive": 5,
    }

    requests: List[BacktestRequestHint] = []
    now_iso = datetime.utcnow().isoformat() + "Z"

    for suggestion in suggestions:
        signal: Literal["bullish", "bearish", "neutral"]
        if suggestion.action == "increase":
            signal = "bullish"
        elif suggestion.action == "decrease":
            signal = "bearish"
        else:
            signal = "neutral"

        confidence = float(np.clip(0.35 + abs(suggestion.delta_weight) * 4.0, 0.0, 1.0))

        requests.append(
            BacktestRequestHint(
                symbol=suggestion.symbol,
                signals=[
                    BacktestSignalHint(
                        date=now_iso,
                        signal=signal,
                        confidence=round(confidence, 3),
                    )
                ],
                holding_days=profile_to_holding_days[constraints.risk_profile],
                stop_loss_pct=-4.0 if constraints.risk_profile == "conservative" else -5.0 if constraints.risk_profile == "balanced" else -7.0,
                take_profit_pct=8.0 if constraints.risk_profile == "conservative" else 12.0 if constraints.risk_profile == "balanced" else 16.0,
                use_historical_signals=False,
                days_back=180,
            )
        )

    return BacktestPayloadHint(
        strategy_name=f"portfolio_rebalance_{constraints.risk_profile}",
        generated_at=now_iso,
        requests=requests,
    )


def _calculate_rebalance_suggestions(
    correlation: CorrelationResult,
    matrix: np.ndarray,
    current_weights: np.ndarray,
    constraints: RebalanceConstraints,
) -> tuple[List[RebalanceSuggestion], List[ConstraintViolation]]:
    """基于波动、相关性与收益生成再平衡建议。"""
    symbols = correlation.symbols
    n_symbols = len(symbols)

    if n_symbols == 0 or len(current_weights) != n_symbols:
        return [], []

    raw_scores: List[float] = []
    diagnostics: List[Dict[str, float]] = []

    for index, symbol in enumerate(symbols):
        metrics = correlation.returns_summary.get(symbol, {})
        volatility = max(float(metrics.get("volatility", 0.0)), 0.1)
        total_return = float(metrics.get("total_return", 0.0))

        if n_symbols > 1:
            row = matrix[index]
            avg_abs_corr = float(np.mean(np.abs(np.delete(row, index))))
        else:
            avg_abs_corr = 0.0

        if constraints.risk_profile == "conservative":
            momentum_score = float(np.clip((total_return + 18.0) / 45.0, 0.25, 1.15))
            stability_score = 1.0 / (volatility + 0.45)
            decorrelation_power = 1.0
        elif constraints.risk_profile == "aggressive":
            momentum_score = float(np.clip((total_return + 24.0) / 34.0, 0.25, 1.6))
            stability_score = 1.0 / (volatility + 0.85)
            decorrelation_power = 0.65
        else:
            momentum_score = float(np.clip((total_return + 20.0) / 40.0, 0.3, 1.4))
            stability_score = 1.0 / (volatility + 0.6)
            decorrelation_power = 0.8

        decorrelation_score = 1.0 - float(np.clip(avg_abs_corr, 0.0, 0.95))
        score = max(0.01, stability_score * (decorrelation_score ** decorrelation_power) * momentum_score)

        raw_scores.append(score)
        diagnostics.append(
            {
                "volatility": volatility,
                "avg_abs_corr": avg_abs_corr,
                "total_return": total_return,
            }
        )

    raw_scores_np = np.array(raw_scores, dtype=float)
    raw_sum = float(np.sum(raw_scores_np))
    if raw_sum <= 0:
        target_weights = np.array([1.0 / n_symbols] * n_symbols, dtype=float)
    else:
        target_weights = raw_scores_np / raw_sum

    adjusted_targets, constraint_violations = _apply_rebalance_constraints(
        target_weights=target_weights,
        current_weights=current_weights,
        constraints=constraints,
    )

    delta_weights = adjusted_targets - current_weights

    suggestions: List[RebalanceSuggestion] = []
    for index, symbol in enumerate(symbols):
        delta = float(delta_weights[index])
        if delta > 0.03:
            action: Literal["increase", "decrease", "hold"] = "increase"
        elif delta < -0.03:
            action = "decrease"
        else:
            action = "hold"

        metric = diagnostics[index]
        total_return = metric["total_return"]
        avg_abs_corr = metric["avg_abs_corr"]
        volatility = metric["volatility"]

        trend_desc = (
            "收益动能偏强"
            if total_return > 5
            else "近期收益偏弱"
            if total_return < -5
            else "收益表现中性"
        )
        corr_desc = "相关性较低" if avg_abs_corr < 0.35 else "相关性偏高"
        vol_desc = "波动较低" if volatility < 2 else "波动中等" if volatility < 4 else "波动偏高"

        if action == "increase":
            rationale = f"{trend_desc}且{corr_desc}，{vol_desc}，可考虑适度增配"
        elif action == "decrease":
            rationale = f"{corr_desc}或{vol_desc}，建议适当降配并分散风险"
        else:
            rationale = f"{trend_desc}、{corr_desc}，当前权重可维持"

        confidence = float(
            np.clip(0.45 + min(abs(delta) * 5.0, 1.0) * 0.35 + (0.15 if action != "hold" else 0.05), 0.0, 1.0)
        )

        suggestions.append(
            RebalanceSuggestion(
                symbol=symbol,
                current_weight=round(float(current_weights[index]), 6),
                target_weight=round(float(adjusted_targets[index]), 6),
                delta_weight=round(delta, 6),
                action=action,
                confidence=round(confidence, 3),
                rationale=rationale,
                volatility=round(volatility, 4),
                avg_abs_correlation=round(avg_abs_corr, 4),
                total_return=round(total_return, 4),
            )
        )

    suggestions.sort(key=lambda item: abs(item.delta_weight), reverse=True)
    return suggestions, constraint_violations


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

    _normalize_weights(request.symbols, request.weights)

    try:
        returns_data: Dict[str, List[float]] = {}
        returns_summary: Dict[str, Dict[str, float]] = {}

        for symbol in request.symbols:
            try:
                history = await MarketRouter.get_history(symbol, request.period)
                if len(history) < 5:
                    logger.warning("Insufficient history data", symbol=symbol)
                    continue

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

        valid_symbols = list(returns_data.keys())
        if len(valid_symbols) < 2:
            raise HTTPException(
                status_code=400,
                detail=f"无法获取足够的历史数据。有效股票: {valid_symbols}"
            )

        min_length = min(len(returns_data[s]) for s in valid_symbols)
        aligned_returns = {s: returns_data[s][-min_length:] for s in valid_symbols}

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
    normalized_request_weights = _normalize_weights(request.symbols, request.weights)
    constraints = request.constraints or RebalanceConstraints()

    if constraints.max_top2_weight + 1e-9 < constraints.max_single_weight:
        raise HTTPException(
            status_code=400,
            detail="constraints.max_top2_weight 不能小于 constraints.max_single_weight",
        )

    correlation = await calculate_correlation(request)

    matrix = np.array(correlation.matrix)
    n = len(correlation.symbols)

    current_weights = _build_current_weights(
        correlation_symbols=correlation.symbols,
        request_symbols=request.symbols,
        normalized_request_weights=normalized_request_weights,
    )

    weights_used: Optional[np.ndarray] = current_weights if normalized_request_weights is not None else None

    if n > 1:
        upper_triangle = np.abs(matrix[np.triu_indices(n, k=1)])

        if weights_used is None:
            avg_corr = float(np.mean(upper_triangle))
            diversification_score = float((1 - avg_corr) * 100)
        else:
            pairwise_corrs = []
            pairwise_weights = []
            for i in range(n):
                for j in range(i + 1, n):
                    pairwise_corrs.append(abs(float(matrix[i][j])))
                    pairwise_weights.append(float(weights_used[i] * weights_used[j]))

            pairwise_corrs_np = np.array(pairwise_corrs, dtype=float)
            pairwise_weights_np = np.array(pairwise_weights, dtype=float)
            weight_sum = float(np.sum(pairwise_weights_np))

            if weight_sum > 0:
                avg_corr = float(np.dot(pairwise_corrs_np, pairwise_weights_np) / weight_sum)
            else:
                avg_corr = float(np.mean(upper_triangle))

            raw_diversification = float((1 - avg_corr) * 100)
            hhi = float(np.sum(np.square(weights_used)))
            concentration_ratio = max(0.0, (hhi - 1 / n) / (1 - 1 / n))
            concentration_penalty = concentration_ratio * 20.0
            diversification_score = max(0.0, min(100.0, raw_diversification - concentration_penalty))
    else:
        diversification_score = 0.0

    risk_clusters = []
    threshold = request.cluster_threshold

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

    recommendations = []

    if diversification_score < 30:
        recommendations.append("⚠️ 组合高度集中，建议增加不同行业或市场的股票以降低系统性风险")
    elif diversification_score < 60:
        recommendations.append("📊 组合分散度中等，可考虑增加负相关或低相关资产")
    else:
        recommendations.append("✅ 组合分散度良好，风险分布较为均衡")

    if weights_used is not None:
        max_weight_idx = int(np.argmax(weights_used))
        max_weight_symbol = correlation.symbols[max_weight_idx]
        max_weight = float(weights_used[max_weight_idx])

        if max_weight >= 0.45:
            recommendations.append(
                f"⚖️ 权重集中度偏高：{max_weight_symbol} 权重约 {max_weight * 100:.1f}%，建议降低单票暴露"
            )

        top_two_weights = np.sort(weights_used)[-2:]
        top_two_share = float(np.sum(top_two_weights))
        if top_two_share >= 0.65:
            recommendations.append(
                f"📉 前两大持仓占比约 {top_two_share * 100:.1f}%，可考虑引入低相关标的分散风险"
            )

    if risk_clusters:
        cluster_stocks = [", ".join(c["stocks"]) for c in risk_clusters]
        recommendations.append(
            f"🔗 发现相关性高于阈值({threshold:.2f})的股票群: {'; '.join(cluster_stocks)}。这些股票可能同涨同跌"
        )

    if correlation.returns_summary:
        high_vol = [s for s, data in correlation.returns_summary.items() if data.get("volatility", 0) > 3]
        if high_vol:
            recommendations.append(f"📈 高波动股票: {', '.join(high_vol)}。注意仓位控制")

        negative_return = [s for s, data in correlation.returns_summary.items() if data.get("total_return", 0) < -10]
        if negative_return:
            recommendations.append(f"📉 近期表现不佳: {', '.join(negative_return)}。建议关注基本面变化")

    rebalance_suggestions, constraint_violations = _calculate_rebalance_suggestions(
        correlation=correlation,
        matrix=matrix,
        current_weights=current_weights,
        constraints=constraints,
    )
    recommended_turnover = float(
        np.sum([abs(item.delta_weight) for item in rebalance_suggestions]) / 2
    )

    actionable_suggestion = next(
        (item for item in rebalance_suggestions if item.action != "hold"),
        None,
    )
    if actionable_suggestion is not None:
        verb = "增持" if actionable_suggestion.action == "increase" else "减持"
        recommendations.append(
            f"🧭 再平衡建议：{actionable_suggestion.symbol} 可考虑{verb}约 {abs(actionable_suggestion.delta_weight) * 100:.1f}%"
        )

    if constraint_violations:
        recommendations.append(
            f"🛡️ 约束触发 {len(constraint_violations)} 项，目标权重已按上限自动修正"
        )

    backtest_payload_hint = (
        _build_backtest_payload_hint(rebalance_suggestions, constraints)
        if request.enable_backtest_hint and rebalance_suggestions
        else None
    )

    return PortfolioAnalysis(
        correlation=correlation,
        diversification_score=round(diversification_score, 1),
        risk_clusters=risk_clusters,
        recommendations=recommendations,
        rebalance_suggestions=rebalance_suggestions,
        recommended_turnover=round(recommended_turnover, 6),
        constraint_violations=constraint_violations,
        backtest_payload_hint=backtest_payload_hint,
    )


@router.get("/quick-check", response_model=QuickPortfolioCheckResponse)
async def quick_portfolio_check(
    symbols: str = Query(..., description="逗号分隔的股票代码列表"),
    period: PortfolioPeriod = Query("1mo", description="历史数据周期"),
    cluster_threshold: float = Query(
        DEFAULT_CLUSTER_THRESHOLD,
        ge=0.5,
        le=0.95,
        description="风险聚类相关性阈值",
    ),
    weights: Optional[str] = Query(None, description="逗号分隔的权重列表，与 symbols 一一对应"),
):
    """
    快速组合检查

    简化版接口，返回基本的分散化评分。
    """
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]

    if len(symbol_list) < 2:
        return QuickPortfolioCheckResponse(
            diversification_score=0.0,
            risk_clusters_count=0,
            message="至少需要 2 个股票",
        )

    try:
        parsed_weights = _parse_weights_query(weights)
        request = CorrelationRequest(
            symbols=symbol_list,
            period=period,
            cluster_threshold=cluster_threshold,
            weights=parsed_weights,
        )
        analysis = await analyze_portfolio(request)

        return QuickPortfolioCheckResponse(
            diversification_score=analysis.diversification_score,
            risk_clusters_count=len(analysis.risk_clusters),
            top_recommendation=analysis.recommendations[0] if analysis.recommendations else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Quick portfolio check failed", symbols=symbol_list, error=str(e))
        raise HTTPException(status_code=500, detail=f"快速检查失败: {str(e)}")
