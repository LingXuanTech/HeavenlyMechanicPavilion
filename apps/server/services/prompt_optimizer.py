"""Prompt 自动优化服务

基于 Agent 历史表现自动调优 Prompt。
"""

import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlmodel import Session, select
import structlog

from db.models import (
    AgentPrompt,
    PromptVersion,
    AgentPerformance,
    PredictionOutcome,
    AgentCategory,
    engine,
)
from services.accuracy_tracker import AccuracyTracker

logger = structlog.get_logger(__name__)


class PromptOptimizer:
    """Prompt 自动优化器

    基于 Agent 历史表现数据，自动生成 Prompt 改进建议并应用。
    """

    # 性能阈值
    MIN_WIN_RATE = 0.55  # 低于此胜率触发优化
    MAX_OVERCONFIDENCE = 0.15  # 过度自信偏差超过此值触发优化
    MIN_PREDICTIONS_FOR_OPTIMIZATION = 10  # 最少预测数才能触发优化

    def __init__(self, accuracy_tracker: Optional[AccuracyTracker] = None):
        self.accuracy_tracker = accuracy_tracker or AccuracyTracker()

    def analyze_agent_weaknesses(
        self,
        agent_key: str,
        recent_days: int = 30,
    ) -> Dict[str, Any]:
        """分析 Agent 的弱点

        Args:
            agent_key: Agent 标识
            recent_days: 分析的最近天数

        Returns:
            弱点分析报告
        """
        period_start = (datetime.now() - timedelta(days=recent_days)).strftime("%Y-%m-%d")
        period_end = datetime.now().strftime("%Y-%m-%d")

        with Session(engine) as session:
            # 获取该 Agent 的预测
            statement = (
                select(PredictionOutcome)
                .where(PredictionOutcome.agent_key == agent_key)
                .where(PredictionOutcome.prediction_date >= period_start)
                .where(PredictionOutcome.outcome.is_not(None))
            )
            predictions = list(session.exec(statement).all())

            if len(predictions) < self.MIN_PREDICTIONS_FOR_OPTIMIZATION:
                return {
                    "status": "insufficient_data",
                    "predictions_count": len(predictions),
                    "required": self.MIN_PREDICTIONS_FOR_OPTIMIZATION,
                }

            # 基础统计
            total = len(predictions)
            correct = sum(1 for p in predictions if p.is_correct)
            win_rate = correct / total

            avg_confidence = sum(p.confidence for p in predictions) / total
            overconfidence_bias = (avg_confidence / 100) - win_rate

            # 按信号分析
            signal_stats = {}
            for signal in ["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"]:
                signal_preds = [p for p in predictions if p.signal == signal]
                if signal_preds:
                    signal_correct = sum(1 for p in signal_preds if p.is_correct)
                    signal_stats[signal] = {
                        "count": len(signal_preds),
                        "accuracy": signal_correct / len(signal_preds),
                        "avg_confidence": sum(p.confidence for p in signal_preds) / len(signal_preds),
                    }

            # 识别弱点
            weaknesses = []

            # 1. 整体胜率低
            if win_rate < self.MIN_WIN_RATE:
                weaknesses.append({
                    "type": "low_win_rate",
                    "severity": "high" if win_rate < 0.45 else "medium",
                    "detail": f"胜率 {win_rate:.1%} 低于阈值 {self.MIN_WIN_RATE:.1%}",
                    "suggestion": "增加分析深度，引入更多反向验证",
                })

            # 2. 过度自信
            if overconfidence_bias > self.MAX_OVERCONFIDENCE:
                weaknesses.append({
                    "type": "overconfidence",
                    "severity": "high" if overconfidence_bias > 0.25 else "medium",
                    "detail": f"过度自信偏差 {overconfidence_bias:.2f}（置信度 {avg_confidence:.1f}% vs 胜率 {win_rate:.1%}）",
                    "suggestion": "降低基础置信度，对不确定因素更敏感",
                })

            # 3. 特定信号准确率低
            for signal, stats in signal_stats.items():
                if stats["count"] >= 3 and stats["accuracy"] < 0.4:
                    weaknesses.append({
                        "type": f"weak_signal_{signal.lower().replace(' ', '_')}",
                        "severity": "medium",
                        "detail": f"{signal} 信号准确率仅 {stats['accuracy']:.1%}（样本 {stats['count']}）",
                        "suggestion": f"提高 {signal} 信号的判断标准",
                    })

            # 4. 方向偏差
            bullish_preds = [p for p in predictions if p.signal in ["Strong Buy", "Buy"]]
            bearish_preds = [p for p in predictions if p.signal in ["Strong Sell", "Sell"]]
            if bullish_preds and bearish_preds:
                bullish_accuracy = sum(1 for p in bullish_preds if p.is_correct) / len(bullish_preds)
                bearish_accuracy = sum(1 for p in bearish_preds if p.is_correct) / len(bearish_preds)

                if bullish_accuracy < 0.4 and len(bullish_preds) >= 3:
                    weaknesses.append({
                        "type": "bullish_bias",
                        "severity": "medium",
                        "detail": f"多头准确率 {bullish_accuracy:.1%} 偏低",
                        "suggestion": "多头判断时增加风险因素权重",
                    })
                if bearish_accuracy < 0.4 and len(bearish_preds) >= 3:
                    weaknesses.append({
                        "type": "bearish_bias",
                        "severity": "medium",
                        "detail": f"空头准确率 {bearish_accuracy:.1%} 偏低",
                        "suggestion": "空头判断时考虑更多支撑因素",
                    })

            return {
                "status": "analyzed",
                "agent_key": agent_key,
                "period": f"{period_start} ~ {period_end}",
                "statistics": {
                    "total_predictions": total,
                    "win_rate": win_rate,
                    "avg_confidence": avg_confidence,
                    "overconfidence_bias": overconfidence_bias,
                },
                "signal_breakdown": signal_stats,
                "weaknesses": weaknesses,
                "needs_optimization": len(weaknesses) > 0,
            }

    def generate_prompt_improvement(
        self,
        agent_key: str,
        weaknesses: List[Dict[str, Any]],
    ) -> Optional[str]:
        """基于弱点分析生成 Prompt 改进片段

        Args:
            agent_key: Agent 标识
            weaknesses: 弱点列表

        Returns:
            改进的 Prompt 片段
        """
        if not weaknesses:
            return None

        improvements = ["## 基于历史表现的改进要求\n"]

        for i, weakness in enumerate(weaknesses, 1):
            severity_icon = "⚠️" if weakness["severity"] == "high" else "📊"
            improvements.append(
                f"{i}. {severity_icon} **{weakness['type']}**: {weakness['suggestion']}"
            )

        # 通用改进建议
        improvements.append("\n### 通用改进措施：")

        if any(w["type"] == "overconfidence" for w in weaknesses):
            improvements.append("- 置信度评估：仅在有强有力证据支撑时给出 >70% 的置信度")
            improvements.append("- 不确定性表达：明确列出可能导致判断失误的因素")

        if any(w["type"] == "low_win_rate" for w in weaknesses):
            improvements.append("- 反向验证：主动寻找与当前判断相反的证据")
            improvements.append("- 保守策略：在证据不充分时倾向于给出 Hold 信号")

        if any("bias" in w["type"] for w in weaknesses):
            improvements.append("- 均衡分析：多空双方观点需同等权重考虑")

        return "\n".join(improvements)

    def apply_prompt_optimization(
        self,
        agent_key: str,
        improvement_text: str,
        change_note: str = "Auto-optimization based on performance",
        created_by: str = "system",
    ) -> Optional[AgentPrompt]:
        """应用 Prompt 优化

        将改进文本追加到现有 Prompt，并保存版本历史。

        Args:
            agent_key: Agent 标识
            improvement_text: 改进文本
            change_note: 变更说明
            created_by: 修改人

        Returns:
            更新后的 AgentPrompt
        """
        with Session(engine) as session:
            # 获取当前激活的 Prompt
            statement = (
                select(AgentPrompt)
                .where(AgentPrompt.agent_key == agent_key)
                .where(AgentPrompt.is_active == True)
            )
            current_prompt = session.exec(statement).first()

            if not current_prompt:
                logger.warning("No active prompt found", agent_key=agent_key)
                return None

            # 保存当前版本到历史
            version_record = PromptVersion(
                prompt_id=current_prompt.id,
                version=current_prompt.version,
                system_prompt=current_prompt.system_prompt,
                user_prompt_template=current_prompt.user_prompt_template,
                change_note=f"Before optimization: {change_note}",
                created_by=created_by,
            )
            session.add(version_record)

            # 更新 Prompt（将改进文本追加到 system_prompt 末尾）
            if improvement_text not in current_prompt.system_prompt:
                # 避免重复追加
                separator = "\n\n---\n\n"
                current_prompt.system_prompt = (
                    current_prompt.system_prompt + separator + improvement_text
                )
                current_prompt.version += 1
                current_prompt.updated_at = datetime.now()

                session.add(current_prompt)
                session.commit()
                session.refresh(current_prompt)

                logger.info(
                    "Prompt optimized",
                    agent_key=agent_key,
                    new_version=current_prompt.version,
                    change_note=change_note,
                )
                return current_prompt

            logger.debug("Improvement already applied", agent_key=agent_key)
            return current_prompt

    def rollback_prompt(
        self,
        agent_key: str,
        target_version: Optional[int] = None,
    ) -> Optional[AgentPrompt]:
        """回滚 Prompt 到指定版本

        Args:
            agent_key: Agent 标识
            target_version: 目标版本号（None 表示回滚到上一版本）

        Returns:
            回滚后的 AgentPrompt
        """
        with Session(engine) as session:
            # 获取当前 Prompt
            current = session.exec(
                select(AgentPrompt)
                .where(AgentPrompt.agent_key == agent_key)
                .where(AgentPrompt.is_active == True)
            ).first()

            if not current:
                return None

            # 获取目标版本
            statement = (
                select(PromptVersion)
                .where(PromptVersion.prompt_id == current.id)
            )
            if target_version:
                statement = statement.where(PromptVersion.version == target_version)
            else:
                # 获取最近的版本
                statement = statement.order_by(PromptVersion.created_at.desc())

            version_record = session.exec(statement).first()

            if not version_record:
                logger.warning("No version found for rollback", agent_key=agent_key)
                return None

            # 保存当前状态
            current_version_record = PromptVersion(
                prompt_id=current.id,
                version=current.version,
                system_prompt=current.system_prompt,
                user_prompt_template=current.user_prompt_template,
                change_note=f"Before rollback to v{version_record.version}",
                created_by="system",
            )
            session.add(current_version_record)

            # 回滚
            current.system_prompt = version_record.system_prompt
            current.user_prompt_template = version_record.user_prompt_template
            current.version = version_record.version
            current.updated_at = datetime.now()

            session.add(current)
            session.commit()
            session.refresh(current)

            logger.info(
                "Prompt rolled back",
                agent_key=agent_key,
                rolled_back_to=version_record.version,
            )
            return current

    def auto_optimize_all_agents(
        self,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """自动优化所有 Agent 的 Prompt

        Args:
            dry_run: True 只分析不应用，False 实际应用

        Returns:
            优化报告
        """
        with Session(engine) as session:
            # 获取所有激活的 Agent Prompt
            agents = session.exec(
                select(AgentPrompt).where(AgentPrompt.is_active == True)
            ).all()

        results = {
            "analyzed": 0,
            "needs_optimization": 0,
            "optimized": 0,
            "details": [],
        }

        for agent in agents:
            analysis = self.analyze_agent_weaknesses(agent.agent_key)
            results["analyzed"] += 1

            detail = {
                "agent_key": agent.agent_key,
                "status": analysis.get("status"),
            }

            if analysis.get("needs_optimization"):
                results["needs_optimization"] += 1
                weaknesses = analysis.get("weaknesses", [])
                improvement = self.generate_prompt_improvement(agent.agent_key, weaknesses)

                detail["weaknesses"] = weaknesses
                detail["improvement_preview"] = improvement[:500] if improvement else None

                if not dry_run and improvement:
                    self.apply_prompt_optimization(
                        agent.agent_key,
                        improvement,
                        change_note=f"Auto-optimization: {len(weaknesses)} weaknesses detected",
                    )
                    results["optimized"] += 1
                    detail["optimized"] = True

            results["details"].append(detail)

        logger.info(
            "Auto-optimization completed",
            dry_run=dry_run,
            analyzed=results["analyzed"],
            needs_optimization=results["needs_optimization"],
            optimized=results["optimized"],
        )
        return results

    def get_prompt_versions(
        self,
        agent_key: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """获取 Prompt 版本历史

        Args:
            agent_key: Agent 标识
            limit: 返回记录数

        Returns:
            版本历史列表
        """
        with Session(engine) as session:
            # 获取当前 Prompt ID
            current = session.exec(
                select(AgentPrompt)
                .where(AgentPrompt.agent_key == agent_key)
                .where(AgentPrompt.is_active == True)
            ).first()

            if not current:
                return []

            # 获取版本历史
            versions = session.exec(
                select(PromptVersion)
                .where(PromptVersion.prompt_id == current.id)
                .order_by(PromptVersion.created_at.desc())
                .limit(limit)
            ).all()

            return [
                {
                    "version": v.version,
                    "change_note": v.change_note,
                    "created_by": v.created_by,
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                    "system_prompt_preview": v.system_prompt[:200] + "..." if len(v.system_prompt) > 200 else v.system_prompt,
                }
                for v in versions
            ]


# 单例实例
prompt_optimizer = PromptOptimizer()
