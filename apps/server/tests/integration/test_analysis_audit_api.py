"""分析任务审计字段 API 集成测试。"""

import asyncio
import json

from db.models import AnalysisResult
from services.cache_service import cache_service


def _minimal_full_report(signal: str = "Hold", confidence: int = 65) -> str:
    """构造满足 FullReport schema 的最小合法 JSON。"""
    return json.dumps(
        {
            "signal": signal,
            "confidence": confidence,
            "reasoning": "test reasoning",
            "debate": {
                "bull": {"thesis": "bull thesis", "points": []},
                "bear": {"thesis": "bear thesis", "points": []},
                "winner": "Neutral",
                "conclusion": "balanced",
            },
            "risk_assessment": {
                "score": 5,
                "volatility_status": "Moderate",
                "liquidity_concerns": False,
                "max_drawdown_risk": "Medium",
                "verdict": "Caution",
            },
            "technical_indicators": {
                "rsi": 50.0,
                "macd": "Neutral",
                "trend": "Neutral",
            },
        },
        ensure_ascii=False,
    )


class TestAnalysisAuditFields:
    """校验分析链路 user_id 审计字段透传。"""

    def test_history_includes_user_id(self, client, db_session):
        record = AnalysisResult(
            symbol="AAPL",
            date="2026-02-11",
            signal="Buy",
            confidence=80,
            full_report_json="{}",
            anchor_script="",
            task_id="task-audit-history",
            user_id=11,
            status="completed",
        )
        db_session.add(record)
        db_session.commit()

        response = client.get("/api/analyze/history/AAPL")

        assert response.status_code == 200
        payload = response.json()
        assert payload["items"]
        assert payload["items"][0]["user_id"] == 11

    def test_detail_includes_user_id(self, client, db_session):
        record = AnalysisResult(
            symbol="MSFT",
            date="2026-02-11",
            signal="Hold",
            confidence=65,
            full_report_json=_minimal_full_report(),
            anchor_script="",
            task_id="task-audit-detail",
            user_id=22,
            status="completed",
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        response = client.get(f"/api/analyze/detail/{record.id}")

        assert response.status_code == 200
        assert response.json()["user_id"] == 22

    def test_status_from_cache_includes_user_id(self, client):
        task_id = "task-audit-cache"
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            cache_service.set_task(
                task_id,
                {
                    "status": "running",
                    "symbol": "TSLA",
                    "progress": 30,
                    "user_id": 33,
                },
            )
        )

        try:
            response = client.get(f"/api/analyze/status/{task_id}")
            assert response.status_code == 200
            assert response.json()["user_id"] == 33
        finally:
            loop.run_until_complete(cache_service.delete_task(task_id))

    def test_status_from_database_includes_user_id(self, client, db_session):
        record = AnalysisResult(
            symbol="NVDA",
            date="2026-02-11",
            signal="Buy",
            confidence=90,
            full_report_json="{}",
            anchor_script="",
            task_id="task-audit-db",
            user_id=44,
            status="completed",
        )
        db_session.add(record)
        db_session.commit()

        response = client.get("/api/analyze/status/task-audit-db")

        assert response.status_code == 200
        assert response.json()["user_id"] == 44
