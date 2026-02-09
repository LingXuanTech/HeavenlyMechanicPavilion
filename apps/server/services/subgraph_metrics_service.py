"""SubGraph A/B 指标服务

聚合 AnalysisResult 表按 architecture_mode 分组统计，
提供 monolith vs subgraph 的对比数据和灰度推荐。
"""

import structlog
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Literal
from sqlmodel import Session, select, func, col
from db.models import AnalysisResult, engine
from config.settings import settings

logger = structlog.get_logger()


class SubgraphMetricsService:
    """SubGraph A/B 对比指标服务"""

    def get_comparison(self, days: int = 7) -> Dict[str, Any]:
        """获取 monolith vs subgraph 的对比数据

        Args:
            days: 统计天数（默认 7 天）

        Returns:
            包含两种架构模式的统计数据和推荐结论
        """
        cutoff = datetime.now() - timedelta(days=days)

        with Session(engine) as session:
            monolith_stats = self._get_mode_stats(session, "monolith", cutoff)
            subgraph_stats = self._get_mode_stats(session, "subgraph", cutoff)

        recommendation = self._compute_recommendation(monolith_stats, subgraph_stats)

        return {
            "period_days": days,
            "cutoff": cutoff.isoformat(),
            "monolith": monolith_stats,
            "subgraph": subgraph_stats,
            "recommendation": recommendation,
            "current_rollout_percentage": settings.SUBGRAPH_ROLLOUT_PERCENTAGE,
        }

    def _get_mode_stats(
        self, session: Session, mode: str, cutoff: datetime
    ) -> Dict[str, Any]:
        """获取指定架构模式的统计数据"""
        base_filter = (
            col(AnalysisResult.architecture_mode) == mode,
            col(AnalysisResult.created_at) >= cutoff,
        )

        # 总数
        total_stmt = (
            select(func.count())
            .select_from(AnalysisResult)
            .where(*base_filter)
        )
        total = session.exec(total_stmt).one()

        if total == 0:
            return {
                "count": 0,
                "avg_elapsed_seconds": None,
                "success_rate": None,
                "avg_confidence": None,
                "failed_count": 0,
                "completed_count": 0,
            }

        # 成功数
        completed_stmt = (
            select(func.count())
            .select_from(AnalysisResult)
            .where(*base_filter, AnalysisResult.status == "completed")
        )
        completed = session.exec(completed_stmt).one()

        # 失败数
        failed = total - completed

        # 平均耗时（仅成功的）
        avg_elapsed_stmt = (
            select(func.avg(AnalysisResult.elapsed_seconds))
            .where(*base_filter, AnalysisResult.status == "completed")
        )
        avg_elapsed = session.exec(avg_elapsed_stmt).one()

        # 平均置信度（仅成功的）
        avg_confidence_stmt = (
            select(func.avg(AnalysisResult.confidence))
            .where(*base_filter, AnalysisResult.status == "completed")
        )
        avg_confidence = session.exec(avg_confidence_stmt).one()

        success_rate = round(completed / total * 100, 2) if total > 0 else 0

        return {
            "count": total,
            "avg_elapsed_seconds": round(avg_elapsed, 2) if avg_elapsed else None,
            "success_rate": success_rate,
            "avg_confidence": round(avg_confidence, 1) if avg_confidence else None,
            "failed_count": failed,
            "completed_count": completed,
        }

    def _compute_recommendation(
        self,
        monolith: Dict[str, Any],
        subgraph: Dict[str, Any],
    ) -> Dict[str, Any]:
        """计算灰度推荐

        规则：
        - subgraph 样本 ≥ 30 且成功率 ≥ monolith 且耗时 ≤ monolith×1.1 → subgraph_ready
        - subgraph 样本 < 30 → needs_more_data
        - 否则 → monolith_better
        """
        sub_count = subgraph["count"]
        sub_rate = subgraph["success_rate"]
        sub_elapsed = subgraph["avg_elapsed_seconds"]
        mono_rate = monolith["success_rate"]
        mono_elapsed = monolith["avg_elapsed_seconds"]

        if sub_count < 30:
            return {
                "action": "needs_more_data",
                "reason": f"SubGraph 样本数不足（{sub_count}/30），需要更多数据",
                "suggested_rollout": min(settings.SUBGRAPH_ROLLOUT_PERCENTAGE + 10, 30),
            }

        # 两者都有足够数据时比较
        if sub_rate is None or mono_rate is None:
            return {
                "action": "needs_more_data",
                "reason": "缺少成功率数据",
                "suggested_rollout": settings.SUBGRAPH_ROLLOUT_PERCENTAGE,
            }

        rate_ok = sub_rate >= mono_rate
        elapsed_ok = (
            sub_elapsed is not None
            and mono_elapsed is not None
            and sub_elapsed <= mono_elapsed * 1.1
        )

        if rate_ok and elapsed_ok:
            return {
                "action": "subgraph_ready",
                "reason": (
                    f"SubGraph 成功率 {sub_rate}% ≥ Monolith {mono_rate}%，"
                    f"耗时 {sub_elapsed}s ≤ {mono_elapsed}s × 1.1"
                ),
                "suggested_rollout": min(settings.SUBGRAPH_ROLLOUT_PERCENTAGE + 20, 100),
            }

        reasons = []
        if not rate_ok:
            reasons.append(f"成功率 {sub_rate}% < {mono_rate}%")
        if not elapsed_ok:
            reasons.append(
                f"耗时 {sub_elapsed}s > {mono_elapsed}s × 1.1"
                if sub_elapsed and mono_elapsed
                else "耗时数据缺失"
            )

        return {
            "action": "monolith_better",
            "reason": f"Monolith 表现更优: {'; '.join(reasons)}",
            "suggested_rollout": max(settings.SUBGRAPH_ROLLOUT_PERCENTAGE - 10, 0),
        }

    def update_rollout_percentage(self, percentage: int) -> Dict[str, Any]:
        """更新灰度比例

        注意：此方法仅修改运行时配置，不持久化到 .env 文件。
        重启后会恢复为环境变量中的值。

        Args:
            percentage: 新的灰度比例 (0-100)

        Returns:
            更新结果
        """
        old_value = settings.SUBGRAPH_ROLLOUT_PERCENTAGE
        percentage = max(0, min(100, percentage))
        settings.SUBGRAPH_ROLLOUT_PERCENTAGE = percentage

        logger.info(
            "SubGraph rollout percentage updated",
            old_value=old_value,
            new_value=percentage,
        )

        return {
            "previous": old_value,
            "current": percentage,
            "message": f"灰度比例已从 {old_value}% 更新为 {percentage}%（运行时生效，重启后恢复）",
        }


# 全局单例
subgraph_metrics_service = SubgraphMetricsService()
