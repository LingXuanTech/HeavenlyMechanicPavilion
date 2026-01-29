"""预测准确率追踪服务

追踪 Agent 预测结果，评估准确率，支持反思闭环。
"""

import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlmodel import Session, select, func
import structlog

from db.models import (
    AnalysisResult,
    PredictionOutcome,
    AgentPerformance,
    engine,
)
from services.data_router import MarketRouter

logger = structlog.get_logger(__name__)


class AccuracyTracker:
    """预测准确率追踪器"""

    # 信号到数值的映射（用于方向判断）
    SIGNAL_DIRECTION = {
        "Strong Buy": 2,
        "Buy": 1,
        "Hold": 0,
        "Sell": -1,
        "Strong Sell": -2,
    }

    # 评估周期（天数）
    DEFAULT_EVALUATION_DAYS = 5

    def __init__(self, market_router: Optional[MarketRouter] = None):
        self.market_router = market_router or MarketRouter()

    async def record_prediction(
        self,
        analysis_id: int,
        symbol: str,
        signal: str,
        confidence: int,
        target_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        entry_price: Optional[float] = None,
        agent_key: str = "overall",
    ) -> PredictionOutcome:
        """记录一条预测

        Args:
            analysis_id: 关联的分析结果 ID
            symbol: 股票代码
            signal: 预测信号
            confidence: 置信度 (0-100)
            target_price: 目标价
            stop_loss: 止损价
            entry_price: 入场价（若无则取当前价）
            agent_key: Agent 标识

        Returns:
            创建的 PredictionOutcome 记录
        """
        # 获取当前价格作为入场价
        if entry_price is None:
            try:
                price_data = await self.market_router.get_price(symbol)
                entry_price = price_data.get("current_price")
            except Exception as e:
                logger.warning("Failed to get entry price", symbol=symbol, error=str(e))

        prediction = PredictionOutcome(
            analysis_id=analysis_id,
            symbol=symbol,
            prediction_date=datetime.now().strftime("%Y-%m-%d"),
            signal=signal,
            confidence=confidence,
            target_price=target_price,
            stop_loss=stop_loss,
            entry_price=entry_price,
            agent_key=agent_key,
        )

        with Session(engine) as session:
            session.add(prediction)
            session.commit()
            session.refresh(prediction)
            logger.info(
                "Prediction recorded",
                prediction_id=prediction.id,
                symbol=symbol,
                signal=signal,
                confidence=confidence,
            )
            return prediction

    async def record_predictions_from_analysis(
        self,
        analysis_result: AnalysisResult,
    ) -> List[PredictionOutcome]:
        """从分析结果中提取并记录所有预测

        Args:
            analysis_result: 分析结果记录

        Returns:
            创建的所有 PredictionOutcome 记录
        """
        predictions = []

        # 解析报告 JSON
        try:
            report = json.loads(analysis_result.full_report_json)
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                "Failed to parse report JSON",
                analysis_id=analysis_result.id,
            )
            return predictions

        # 记录总体预测
        overall_pred = await self.record_prediction(
            analysis_id=analysis_result.id,
            symbol=analysis_result.symbol,
            signal=analysis_result.signal,
            confidence=analysis_result.confidence,
            target_price=report.get("target_price"),
            stop_loss=report.get("stop_loss"),
            agent_key="overall",
        )
        predictions.append(overall_pred)

        # 记录各 Agent 的独立预测（如果有）
        agents_data = report.get("agents", {})
        for agent_key, agent_report in agents_data.items():
            if isinstance(agent_report, dict):
                agent_signal = agent_report.get("signal")
                agent_confidence = agent_report.get("confidence")
                if agent_signal and agent_confidence is not None:
                    pred = await self.record_prediction(
                        analysis_id=analysis_result.id,
                        symbol=analysis_result.symbol,
                        signal=agent_signal,
                        confidence=agent_confidence,
                        agent_key=agent_key,
                    )
                    predictions.append(pred)

        return predictions

    async def evaluate_prediction(
        self,
        prediction_id: int,
        evaluation_days: int = DEFAULT_EVALUATION_DAYS,
    ) -> Optional[PredictionOutcome]:
        """评估单条预测的准确性

        Args:
            prediction_id: 预测记录 ID
            evaluation_days: 评估周期（天数）

        Returns:
            更新后的 PredictionOutcome，若评估失败返回 None
        """
        with Session(engine) as session:
            prediction = session.get(PredictionOutcome, prediction_id)
            if not prediction:
                logger.warning("Prediction not found", prediction_id=prediction_id)
                return None

            # 检查是否已评估
            if prediction.outcome is not None:
                logger.debug("Prediction already evaluated", prediction_id=prediction_id)
                return prediction

            # 检查是否到达评估时间
            prediction_date = datetime.strptime(prediction.prediction_date, "%Y-%m-%d")
            evaluation_date = prediction_date + timedelta(days=evaluation_days)
            if datetime.now() < evaluation_date:
                logger.debug(
                    "Not yet time to evaluate",
                    prediction_id=prediction_id,
                    evaluation_date=evaluation_date.isoformat(),
                )
                return None

            # 获取当前价格
            try:
                price_data = await self.market_router.get_price(prediction.symbol)
                actual_price = price_data.get("current_price")
            except Exception as e:
                logger.warning(
                    "Failed to get actual price",
                    symbol=prediction.symbol,
                    error=str(e),
                )
                return None

            if actual_price is None or prediction.entry_price is None:
                logger.warning(
                    "Missing price data for evaluation",
                    prediction_id=prediction_id,
                    actual_price=actual_price,
                    entry_price=prediction.entry_price,
                )
                return None

            # 计算收益率
            actual_return = (actual_price - prediction.entry_price) / prediction.entry_price * 100

            # 判断方向是否正确
            signal_direction = self.SIGNAL_DIRECTION.get(prediction.signal, 0)
            if signal_direction > 0:  # 看多
                is_correct = actual_return > 0
            elif signal_direction < 0:  # 看空
                is_correct = actual_return < 0
            else:  # Hold
                is_correct = abs(actual_return) < 5  # 波动 < 5% 视为正确

            # 判断结果
            if prediction.target_price and actual_price >= prediction.target_price:
                outcome = "Win"
            elif prediction.stop_loss and actual_price <= prediction.stop_loss:
                outcome = "Loss"
            elif is_correct:
                outcome = "Partial"  # 方向对但未触及目标价
            else:
                outcome = "Loss"

            # 更新记录
            prediction.outcome_date = datetime.now().strftime("%Y-%m-%d")
            prediction.actual_price = actual_price
            prediction.actual_return = actual_return
            prediction.outcome = outcome
            prediction.is_correct = is_correct
            prediction.evaluated_at = datetime.now()

            session.add(prediction)
            session.commit()
            session.refresh(prediction)

            logger.info(
                "Prediction evaluated",
                prediction_id=prediction_id,
                symbol=prediction.symbol,
                outcome=outcome,
                is_correct=is_correct,
                actual_return=f"{actual_return:.2f}%",
            )
            return prediction

    async def evaluate_pending_predictions(
        self,
        evaluation_days: int = DEFAULT_EVALUATION_DAYS,
        limit: int = 100,
    ) -> List[PredictionOutcome]:
        """批量评估待处理的预测

        Args:
            evaluation_days: 评估周期
            limit: 最大评估数量

        Returns:
            已评估的预测列表
        """
        cutoff_date = (datetime.now() - timedelta(days=evaluation_days)).strftime("%Y-%m-%d")

        with Session(engine) as session:
            # 查询待评估的预测
            statement = (
                select(PredictionOutcome)
                .where(PredictionOutcome.outcome.is_(None))
                .where(PredictionOutcome.prediction_date <= cutoff_date)
                .limit(limit)
            )
            pending = session.exec(statement).all()

        evaluated = []
        for prediction in pending:
            result = await self.evaluate_prediction(prediction.id, evaluation_days)
            if result:
                evaluated.append(result)

        logger.info(
            "Batch evaluation completed",
            total_pending=len(pending),
            evaluated=len(evaluated),
        )
        return evaluated

    def calculate_agent_performance(
        self,
        agent_key: str,
        period_start: str,
        period_end: str,
    ) -> Optional[AgentPerformance]:
        """计算指定 Agent 在指定周期的表现

        Args:
            agent_key: Agent 标识
            period_start: 周期开始日期 (YYYY-MM-DD)
            period_end: 周期结束日期 (YYYY-MM-DD)

        Returns:
            AgentPerformance 记录
        """
        with Session(engine) as session:
            # 查询该周期内该 Agent 的所有已评估预测
            statement = (
                select(PredictionOutcome)
                .where(PredictionOutcome.agent_key == agent_key)
                .where(PredictionOutcome.prediction_date >= period_start)
                .where(PredictionOutcome.prediction_date <= period_end)
                .where(PredictionOutcome.outcome.is_not(None))
            )
            predictions = list(session.exec(statement).all())

            if not predictions:
                logger.debug(
                    "No predictions found for agent",
                    agent_key=agent_key,
                    period_start=period_start,
                    period_end=period_end,
                )
                return None

            # 计算基础指标
            total = len(predictions)
            correct = sum(1 for p in predictions if p.is_correct)
            win_rate = correct / total if total > 0 else 0

            returns = [p.actual_return for p in predictions if p.actual_return is not None]
            avg_return = sum(returns) / len(returns) if returns else 0

            confidences = [p.confidence for p in predictions if p.confidence is not None]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            # 按信号类型计算准确率
            signal_accuracy = {}
            for signal in self.SIGNAL_DIRECTION.keys():
                signal_preds = [p for p in predictions if p.signal == signal]
                if signal_preds:
                    signal_correct = sum(1 for p in signal_preds if p.is_correct)
                    signal_accuracy[signal] = signal_correct / len(signal_preds)

            # 计算过度自信偏差
            # 偏差 = 平均置信度 - 实际胜率（正数表示过度自信）
            overconfidence_bias = (avg_confidence / 100) - win_rate if avg_confidence else None

            # 判断方向偏差
            bullish_count = sum(
                1 for p in predictions if self.SIGNAL_DIRECTION.get(p.signal, 0) > 0
            )
            bearish_count = sum(
                1 for p in predictions if self.SIGNAL_DIRECTION.get(p.signal, 0) < 0
            )
            if bullish_count > bearish_count * 1.5:
                direction_bias = "bullish"
            elif bearish_count > bullish_count * 1.5:
                direction_bias = "bearish"
            else:
                direction_bias = "neutral"

            # 创建或更新 AgentPerformance 记录
            existing = session.exec(
                select(AgentPerformance)
                .where(AgentPerformance.agent_key == agent_key)
                .where(AgentPerformance.period_start == period_start)
                .where(AgentPerformance.period_end == period_end)
            ).first()

            if existing:
                perf = existing
            else:
                perf = AgentPerformance(
                    agent_key=agent_key,
                    period_start=period_start,
                    period_end=period_end,
                )

            perf.total_predictions = total
            perf.correct_predictions = correct
            perf.win_rate = win_rate
            perf.avg_return = avg_return
            perf.avg_confidence = avg_confidence
            perf.strong_buy_accuracy = signal_accuracy.get("Strong Buy")
            perf.buy_accuracy = signal_accuracy.get("Buy")
            perf.hold_accuracy = signal_accuracy.get("Hold")
            perf.sell_accuracy = signal_accuracy.get("Sell")
            perf.strong_sell_accuracy = signal_accuracy.get("Strong Sell")
            perf.overconfidence_bias = overconfidence_bias
            perf.direction_bias = direction_bias
            perf.calculated_at = datetime.now()

            session.add(perf)
            session.commit()
            session.refresh(perf)

            logger.info(
                "Agent performance calculated",
                agent_key=agent_key,
                period=f"{period_start} to {period_end}",
                total_predictions=total,
                win_rate=f"{win_rate:.2%}",
                avg_return=f"{avg_return:.2f}%",
                direction_bias=direction_bias,
            )
            return perf

    def get_agent_performance_summary(
        self,
        agent_key: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """获取 Agent 表现摘要

        Args:
            agent_key: 指定 Agent（None 表示所有 Agent）
            limit: 返回记录数

        Returns:
            表现摘要列表
        """
        with Session(engine) as session:
            statement = select(AgentPerformance).order_by(
                AgentPerformance.calculated_at.desc()
            )
            if agent_key:
                statement = statement.where(AgentPerformance.agent_key == agent_key)
            statement = statement.limit(limit)

            records = session.exec(statement).all()

            return [
                {
                    "agent_key": r.agent_key,
                    "period": f"{r.period_start} ~ {r.period_end}",
                    "total_predictions": r.total_predictions,
                    "win_rate": f"{r.win_rate:.2%}" if r.win_rate else "N/A",
                    "avg_return": f"{r.avg_return:.2f}%" if r.avg_return else "N/A",
                    "avg_confidence": f"{r.avg_confidence:.1f}" if r.avg_confidence else "N/A",
                    "overconfidence_bias": (
                        f"{r.overconfidence_bias:+.2f}" if r.overconfidence_bias else "N/A"
                    ),
                    "direction_bias": r.direction_bias or "N/A",
                    "calculated_at": r.calculated_at.isoformat() if r.calculated_at else None,
                }
                for r in records
            ]

    def get_prediction_history(
        self,
        symbol: Optional[str] = None,
        agent_key: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """获取预测历史

        Args:
            symbol: 指定股票（None 表示所有）
            agent_key: 指定 Agent（None 表示所有）
            limit: 返回记录数

        Returns:
            预测历史列表
        """
        with Session(engine) as session:
            statement = select(PredictionOutcome).order_by(
                PredictionOutcome.created_at.desc()
            )
            if symbol:
                statement = statement.where(PredictionOutcome.symbol == symbol)
            if agent_key:
                statement = statement.where(PredictionOutcome.agent_key == agent_key)
            statement = statement.limit(limit)

            records = session.exec(statement).all()

            return [
                {
                    "id": r.id,
                    "symbol": r.symbol,
                    "agent_key": r.agent_key,
                    "prediction_date": r.prediction_date,
                    "signal": r.signal,
                    "confidence": r.confidence,
                    "entry_price": r.entry_price,
                    "target_price": r.target_price,
                    "outcome": r.outcome,
                    "actual_return": f"{r.actual_return:.2f}%" if r.actual_return else None,
                    "is_correct": r.is_correct,
                }
                for r in records
            ]

    def generate_reflection_prompt(
        self,
        agent_key: str,
        recent_days: int = 30,
    ) -> Optional[str]:
        """为指定 Agent 生成反思提示词

        基于历史表现数据生成改进建议，注入到 Agent 的系统提示词中。

        Args:
            agent_key: Agent 标识
            recent_days: 考察的最近天数

        Returns:
            反思提示词片段，若无足够数据返回 None
        """
        period_start = (datetime.now() - timedelta(days=recent_days)).strftime("%Y-%m-%d")
        period_end = datetime.now().strftime("%Y-%m-%d")

        with Session(engine) as session:
            # 获取该 Agent 的最近预测
            statement = (
                select(PredictionOutcome)
                .where(PredictionOutcome.agent_key == agent_key)
                .where(PredictionOutcome.prediction_date >= period_start)
                .where(PredictionOutcome.outcome.is_not(None))
                .order_by(PredictionOutcome.created_at.desc())
                .limit(20)
            )
            predictions = list(session.exec(statement).all())

            if len(predictions) < 5:
                return None  # 样本不足

            # 计算指标
            total = len(predictions)
            correct = sum(1 for p in predictions if p.is_correct)
            win_rate = correct / total

            # 分析错误案例
            wrong_predictions = [p for p in predictions if not p.is_correct]
            error_patterns = []

            # 检测过度自信
            avg_confidence = sum(p.confidence for p in predictions) / total
            if avg_confidence > 70 and win_rate < 0.6:
                error_patterns.append(
                    f"过度自信：平均置信度 {avg_confidence:.0f}%，但胜率仅 {win_rate:.0%}"
                )

            # 检测方向偏差
            bullish_wrong = sum(
                1
                for p in wrong_predictions
                if self.SIGNAL_DIRECTION.get(p.signal, 0) > 0
            )
            bearish_wrong = sum(
                1
                for p in wrong_predictions
                if self.SIGNAL_DIRECTION.get(p.signal, 0) < 0
            )
            if bullish_wrong > bearish_wrong * 2:
                error_patterns.append("看多偏差：多头判断错误率偏高，需谨慎评估利多因素")
            elif bearish_wrong > bullish_wrong * 2:
                error_patterns.append("看空偏差：空头判断错误率偏高，需谨慎评估利空因素")

            # 检测高置信度错误
            high_conf_wrong = [p for p in wrong_predictions if p.confidence >= 80]
            if len(high_conf_wrong) >= 2:
                symbols = [p.symbol for p in high_conf_wrong[:3]]
                error_patterns.append(
                    f"高置信度失误：{', '.join(symbols)} 等预测置信度 ≥80% 但结果错误"
                )

            if not error_patterns:
                return None

            # 生成反思提示词
            reflection = f"""
## 历史表现反思 ({period_start} ~ {period_end})

近期胜率：{win_rate:.0%} ({correct}/{total})

### 需要改进的问题：
"""
            for i, pattern in enumerate(error_patterns, 1):
                reflection += f"{i}. {pattern}\n"

            reflection += """
### 改进建议：
- 对于高置信度预测，请额外验证核心假设
- 考虑更多反向因素，避免确认偏差
- 在不确定时适当降低置信度
"""
            return reflection


# 单例实例
accuracy_tracker = AccuracyTracker()
