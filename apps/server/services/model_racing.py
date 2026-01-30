"""多模型赛马服务

支持多个 LLM 并行分析同一股票，通过共识引擎综合结果。
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from sqlmodel import Session, select
import structlog

from db.models import engine
from services.synthesizer import synthesizer, SynthesisContext
from services.ai_config_service import ai_config_service
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

logger = structlog.get_logger(__name__)


class ConsensusMethod(str, Enum):
    """共识方法"""
    MAJORITY_VOTE = "majority_vote"       # 简单多数投票
    WEIGHTED_VOTE = "weighted_vote"       # 加权投票（根据历史准确率）
    CONFIDENCE_WEIGHTED = "confidence_weighted"  # 置信度加权
    UNANIMOUS = "unanimous"               # 全票一致才采纳


@dataclass
class ModelResult:
    """单个模型的分析结果"""
    model_id: str
    model_name: str
    provider: str
    signal: str
    confidence: int
    reasoning: str
    elapsed_seconds: float
    raw_output: Dict[str, Any]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConsensusResult:
    """共识结果"""
    final_signal: str
    final_confidence: int
    consensus_method: str
    agreement_rate: float
    model_results: List[ModelResult]
    dissenting_models: List[str]
    analysis_summary: str

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["model_results"] = [m.to_dict() for m in self.model_results]
        return result


class ModelRacing:
    """多模型赛马服务

    功能：
    1. 并行调用多个 LLM 分析同一股票
    2. 收集各模型的信号、置信度、推理
    3. 通过共识引擎综合结果
    4. 追踪各模型历史表现
    """

    # 支持的模型配置键
    RACING_MODELS = ["deep_think", "quick_think", "synthesis"]

    # 信号权重映射
    SIGNAL_SCORES = {
        "Strong Buy": 2,
        "Buy": 1,
        "Hold": 0,
        "Sell": -1,
        "Strong Sell": -2,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or DEFAULT_CONFIG

    async def run_parallel_analysis(
        self,
        symbol: str,
        market: str = "US",
        selected_analysts: Optional[List[str]] = None,
        models: Optional[List[str]] = None,
        timeout: int = 300,
    ) -> Dict[str, ModelResult]:
        """并行运行多模型分析

        Args:
            symbol: 股票代码
            market: 市场标识
            selected_analysts: 选用的分析师
            models: 要使用的模型配置键列表，默认使用所有配置的模型
            timeout: 超时时间（秒）

        Returns:
            模型 ID -> ModelResult 的映射
        """
        models = models or self.RACING_MODELS
        results: Dict[str, ModelResult] = {}

        # 创建并行任务
        tasks = []
        for model_key in models:
            task = asyncio.create_task(
                self._run_single_model_analysis(
                    symbol=symbol,
                    market=market,
                    selected_analysts=selected_analysts,
                    model_key=model_key,
                )
            )
            tasks.append((model_key, task))

        # 等待所有任务完成（带超时）
        for model_key, task in tasks:
            try:
                result = await asyncio.wait_for(task, timeout=timeout)
                results[model_key] = result
            except asyncio.TimeoutError:
                results[model_key] = ModelResult(
                    model_id=model_key,
                    model_name=model_key,
                    provider="unknown",
                    signal="Hold",
                    confidence=0,
                    reasoning="Analysis timed out",
                    elapsed_seconds=timeout,
                    raw_output={},
                    error=f"Timeout after {timeout}s",
                )
                logger.warning(
                    "Model analysis timed out",
                    model=model_key,
                    symbol=symbol,
                    timeout=timeout,
                )
            except Exception as e:
                results[model_key] = ModelResult(
                    model_id=model_key,
                    model_name=model_key,
                    provider="unknown",
                    signal="Hold",
                    confidence=0,
                    reasoning=f"Analysis failed: {str(e)}",
                    elapsed_seconds=0,
                    raw_output={},
                    error=str(e),
                )
                logger.error(
                    "Model analysis failed",
                    model=model_key,
                    symbol=symbol,
                    error=str(e),
                )

        logger.info(
            "Parallel analysis completed",
            symbol=symbol,
            models_count=len(models),
            successful=sum(1 for r in results.values() if r.error is None),
        )
        return results

    async def _run_single_model_analysis(
        self,
        symbol: str,
        market: str,
        selected_analysts: Optional[List[str]],
        model_key: str,
    ) -> ModelResult:
        """运行单个模型的分析"""
        import time
        start_time = time.time()

        try:
            # 获取模型信息
            llm = ai_config_service.get_llm(model_key)
            model_name = getattr(llm, "model_name", None) or getattr(llm, "model", model_key)
            provider = self._get_provider_name(llm)

            # 创建图并运行分析
            graph = TradingAgentsGraph(
                selected_analysts=selected_analysts,
                debug=False,
                config=self.config,
                market=market,
            )

            # 运行分析
            final_state, agent_reports = graph.propagate(symbol)

            # 构建合成上下文
            elapsed = round(time.time() - start_time, 2)
            synthesis_context = SynthesisContext(
                analysis_level="L2",
                elapsed_seconds=elapsed,
                analysts_used=selected_analysts or ["market", "news", "fundamentals"],
                market=market,
            )

            # 合成结果
            final_json = await synthesizer.synthesize(symbol, agent_reports, synthesis_context)

            elapsed = round(time.time() - start_time, 2)

            return ModelResult(
                model_id=model_key,
                model_name=model_name,
                provider=provider,
                signal=final_json.get("signal", "Hold"),
                confidence=final_json.get("confidence", 50),
                reasoning=final_json.get("recommendation", {}).get("reasoning", "")[:500],
                elapsed_seconds=elapsed,
                raw_output=final_json,
            )

        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            logger.error("Single model analysis failed", model=model_key, error=str(e))
            raise

    def _get_provider_name(self, llm) -> str:
        """从 LLM 实例获取提供商名称"""
        class_name = llm.__class__.__name__.lower()
        if "openai" in class_name:
            return "openai"
        elif "anthropic" in class_name or "claude" in class_name:
            return "anthropic"
        elif "google" in class_name or "gemini" in class_name:
            return "google"
        else:
            return "unknown"

    def calculate_consensus(
        self,
        results: Dict[str, ModelResult],
        method: ConsensusMethod = ConsensusMethod.CONFIDENCE_WEIGHTED,
        model_weights: Optional[Dict[str, float]] = None,
    ) -> ConsensusResult:
        """计算共识结果

        Args:
            results: 各模型的分析结果
            method: 共识方法
            model_weights: 模型权重（用于加权投票）

        Returns:
            共识结果
        """
        valid_results = [r for r in results.values() if r.error is None]

        if not valid_results:
            return ConsensusResult(
                final_signal="Hold",
                final_confidence=0,
                consensus_method=method.value,
                agreement_rate=0,
                model_results=list(results.values()),
                dissenting_models=[],
                analysis_summary="No valid model results available",
            )

        if method == ConsensusMethod.MAJORITY_VOTE:
            return self._majority_vote(valid_results, results)
        elif method == ConsensusMethod.WEIGHTED_VOTE:
            return self._weighted_vote(valid_results, results, model_weights or {})
        elif method == ConsensusMethod.CONFIDENCE_WEIGHTED:
            return self._confidence_weighted(valid_results, results)
        elif method == ConsensusMethod.UNANIMOUS:
            return self._unanimous(valid_results, results)
        else:
            return self._confidence_weighted(valid_results, results)

    def _majority_vote(
        self,
        valid_results: List[ModelResult],
        all_results: Dict[str, ModelResult],
    ) -> ConsensusResult:
        """简单多数投票"""
        signal_counts: Dict[str, int] = {}
        for r in valid_results:
            signal_counts[r.signal] = signal_counts.get(r.signal, 0) + 1

        # 找出票数最多的信号
        final_signal = max(signal_counts.keys(), key=lambda s: signal_counts[s])
        max_votes = signal_counts[final_signal]
        agreement_rate = max_votes / len(valid_results)

        # 计算平均置信度
        matching_results = [r for r in valid_results if r.signal == final_signal]
        final_confidence = int(sum(r.confidence for r in matching_results) / len(matching_results))

        # 找出持不同意见的模型
        dissenting = [r.model_id for r in valid_results if r.signal != final_signal]

        return ConsensusResult(
            final_signal=final_signal,
            final_confidence=final_confidence,
            consensus_method=ConsensusMethod.MAJORITY_VOTE.value,
            agreement_rate=agreement_rate,
            model_results=list(all_results.values()),
            dissenting_models=dissenting,
            analysis_summary=self._generate_summary(valid_results, final_signal, agreement_rate),
        )

    def _weighted_vote(
        self,
        valid_results: List[ModelResult],
        all_results: Dict[str, ModelResult],
        model_weights: Dict[str, float],
    ) -> ConsensusResult:
        """加权投票（根据历史准确率）"""
        # 如果没有权重，默认都是 1
        default_weight = 1.0

        signal_scores: Dict[str, float] = {}
        total_weight = 0

        for r in valid_results:
            weight = model_weights.get(r.model_id, default_weight)
            signal_scores[r.signal] = signal_scores.get(r.signal, 0) + weight
            total_weight += weight

        # 找出加权票数最多的信号
        final_signal = max(signal_scores.keys(), key=lambda s: signal_scores[s])
        agreement_rate = signal_scores[final_signal] / total_weight if total_weight > 0 else 0

        # 计算加权平均置信度
        matching_results = [r for r in valid_results if r.signal == final_signal]
        weights_sum = sum(model_weights.get(r.model_id, default_weight) for r in matching_results)
        if weights_sum > 0:
            final_confidence = int(
                sum(
                    r.confidence * model_weights.get(r.model_id, default_weight)
                    for r in matching_results
                )
                / weights_sum
            )
        else:
            final_confidence = int(sum(r.confidence for r in matching_results) / len(matching_results))

        dissenting = [r.model_id for r in valid_results if r.signal != final_signal]

        return ConsensusResult(
            final_signal=final_signal,
            final_confidence=final_confidence,
            consensus_method=ConsensusMethod.WEIGHTED_VOTE.value,
            agreement_rate=agreement_rate,
            model_results=list(all_results.values()),
            dissenting_models=dissenting,
            analysis_summary=self._generate_summary(valid_results, final_signal, agreement_rate),
        )

    def _confidence_weighted(
        self,
        valid_results: List[ModelResult],
        all_results: Dict[str, ModelResult],
    ) -> ConsensusResult:
        """置信度加权"""
        # 计算加权平均分数
        total_confidence = sum(r.confidence for r in valid_results)
        if total_confidence == 0:
            total_confidence = 1  # 避免除零

        weighted_score = sum(
            self.SIGNAL_SCORES.get(r.signal, 0) * r.confidence
            for r in valid_results
        ) / total_confidence

        # 根据加权分数确定信号
        if weighted_score >= 1.5:
            final_signal = "Strong Buy"
        elif weighted_score >= 0.5:
            final_signal = "Buy"
        elif weighted_score >= -0.5:
            final_signal = "Hold"
        elif weighted_score >= -1.5:
            final_signal = "Sell"
        else:
            final_signal = "Strong Sell"

        # 计算置信度（基于分散程度）
        avg_confidence = int(total_confidence / len(valid_results))
        signals = [r.signal for r in valid_results]
        unique_signals = len(set(signals))
        # 信号越一致，置信度越高
        consistency_factor = 1 - (unique_signals - 1) * 0.1
        final_confidence = int(avg_confidence * max(0.5, consistency_factor))

        # 计算一致率
        matching_count = sum(1 for r in valid_results if r.signal == final_signal)
        agreement_rate = matching_count / len(valid_results)

        dissenting = [r.model_id for r in valid_results if r.signal != final_signal]

        return ConsensusResult(
            final_signal=final_signal,
            final_confidence=final_confidence,
            consensus_method=ConsensusMethod.CONFIDENCE_WEIGHTED.value,
            agreement_rate=agreement_rate,
            model_results=list(all_results.values()),
            dissenting_models=dissenting,
            analysis_summary=self._generate_summary(valid_results, final_signal, agreement_rate),
        )

    def _unanimous(
        self,
        valid_results: List[ModelResult],
        all_results: Dict[str, ModelResult],
    ) -> ConsensusResult:
        """全票一致"""
        signals = set(r.signal for r in valid_results)

        if len(signals) == 1:
            # 全票一致
            final_signal = signals.pop()
            agreement_rate = 1.0
            dissenting = []
        else:
            # 不一致时返回 Hold
            final_signal = "Hold"
            agreement_rate = 0
            dissenting = [r.model_id for r in valid_results]

        final_confidence = int(sum(r.confidence for r in valid_results) / len(valid_results))

        return ConsensusResult(
            final_signal=final_signal,
            final_confidence=final_confidence if agreement_rate == 1.0 else 30,
            consensus_method=ConsensusMethod.UNANIMOUS.value,
            agreement_rate=agreement_rate,
            model_results=list(all_results.values()),
            dissenting_models=dissenting,
            analysis_summary=self._generate_summary(valid_results, final_signal, agreement_rate),
        )

    def _generate_summary(
        self,
        results: List[ModelResult],
        final_signal: str,
        agreement_rate: float,
    ) -> str:
        """生成分析摘要"""
        model_count = len(results)
        agreeing_count = sum(1 for r in results if r.signal == final_signal)

        lines = [
            f"多模型共识分析结果：{final_signal}",
            f"参与模型数：{model_count}",
            f"一致率：{agreement_rate:.0%} ({agreeing_count}/{model_count})",
            "",
            "各模型详情：",
        ]

        for r in results:
            status = "✓" if r.signal == final_signal else "✗"
            lines.append(
                f"  {status} {r.model_name}: {r.signal} (置信度 {r.confidence}%)"
            )

        return "\n".join(lines)

    async def run_racing_analysis(
        self,
        symbol: str,
        market: str = "US",
        selected_analysts: Optional[List[str]] = None,
        consensus_method: ConsensusMethod = ConsensusMethod.CONFIDENCE_WEIGHTED,
        timeout: int = 300,
    ) -> ConsensusResult:
        """运行完整的赛马分析流程

        Args:
            symbol: 股票代码
            market: 市场
            selected_analysts: 分析师列表
            consensus_method: 共识方法
            timeout: 超时时间

        Returns:
            共识结果
        """
        # 并行分析
        results = await self.run_parallel_analysis(
            symbol=symbol,
            market=market,
            selected_analysts=selected_analysts,
            timeout=timeout,
        )

        # 计算共识
        consensus = self.calculate_consensus(results, method=consensus_method)

        logger.info(
            "Racing analysis completed",
            symbol=symbol,
            final_signal=consensus.final_signal,
            agreement_rate=consensus.agreement_rate,
            consensus_method=consensus_method.value,
        )

        return consensus


# 单例实例
model_racing = ModelRacing()
