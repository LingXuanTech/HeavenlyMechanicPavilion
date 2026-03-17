"""Notifications API 集成测试。"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_current_user
from api.routes.system.notifications import router as notifications_router
from db.models import get_session


class _ExecResult:
    def __init__(self, value):
        self._value = value

    def all(self):
        return self._value

    def first(self):
        return self._value

    def one(self):
        return self._value


def _create_test_client(mock_session: MagicMock, user_id: int = 1) -> TestClient:
    app = FastAPI()
    app.include_router(notifications_router, prefix="/api")

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id)
    app.dependency_overrides[get_session] = lambda: mock_session

    return TestClient(app)


class TestNotificationRoutes:
    """校验通知路由核心行为。"""

    def test_get_logs_supports_filters_and_pagination(self):
        mock_session = MagicMock()
        mock_session.exec.side_effect = [
            _ExecResult(1),
            _ExecResult(
                [
                    SimpleNamespace(
                        id=10,
                        channel="telegram",
                        title="AAPL 分析完成",
                        body="内容",
                        signal="BUY",
                        symbol="AAPL",
                        sent_at=datetime(2026, 3, 17, 10, 0, 0),
                        delivered=True,
                        error=None,
                    )
                ]
            ),
        ]
        client = _create_test_client(mock_session)

        response = client.get(
            "/api/notifications/logs",
            params={
                "limit": 20,
                "offset": 5,
                "symbol": "AAPL",
                "delivered": "true",
                "sent_after": "2026-03-16T00:00:00",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["limit"] == 20
        assert data["offset"] == 5
        assert len(data["items"]) == 1
        assert data["items"][0]["symbol"] == "AAPL"
        assert data["items"][0]["delivered"] is True

        assert len(mock_session.exec.call_args_list) == 2
        count_query = mock_session.exec.call_args_list[0].args[0]
        logs_query = mock_session.exec.call_args_list[1].args[0]
        count_sql = str(count_query)
        logs_sql = str(logs_query)
        assert "count" in count_sql.lower()
        assert "notification_logs.sent_at" in count_sql
        assert "notification_logs.user_id" in logs_sql
        assert "notification_logs.symbol" in logs_sql
        assert "notification_logs.delivered" in logs_sql

    def test_get_logs_rejects_invalid_time_range(self):
        mock_session = MagicMock()
        client = _create_test_client(mock_session)

        response = client.get(
            "/api/notifications/logs",
            params={
                "sent_after": "2026-03-17T12:00:00",
                "sent_before": "2026-03-16T12:00:00",
            },
        )

        assert response.status_code == 422
        assert "sent_after must be earlier" in response.json()["detail"]
        assert mock_session.exec.call_count == 0

    def test_delete_logs_supports_filters_and_returns_deleted_count(self):
        mock_session = MagicMock()
        mock_session.exec.return_value = _ExecResult(
            [
                SimpleNamespace(id=1, user_id=1, symbol="AAPL", delivered=False),
                SimpleNamespace(id=2, user_id=1, symbol="AAPL", delivered=False),
            ]
        )
        client = _create_test_client(mock_session)

        response = client.delete(
            "/api/notifications/logs",
            params={"symbol": "AAPL", "delivered": "false"},
        )

        assert response.status_code == 200
        assert response.json() == {"ok": True, "deleted": 2}
        assert mock_session.delete.call_count == 2
        mock_session.commit.assert_called_once()

        query = mock_session.exec.call_args.args[0]
        query_sql = str(query)
        assert "notification_logs.user_id" in query_sql
        assert "notification_logs.symbol" in query_sql
        assert "notification_logs.delivered" in query_sql

    def test_get_stats_returns_user_scoped_aggregates(self):
        mock_session = MagicMock()
        mock_session.exec.side_effect = [
            _ExecResult(3),  # total_sent
            _ExecResult(1),  # total_failed
            _ExecResult(2),  # channels_count
            _ExecResult(1),  # enabled_channels_count
            _ExecResult(datetime(2026, 3, 17, 11, 0, 0)),  # last_sent_at
        ]
        client = _create_test_client(mock_session)

        response = client.get("/api/notifications/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_sent"] == 3
        assert data["total_failed"] == 1
        assert data["channels_count"] == 2
        assert data["enabled_channels_count"] == 1
        assert data["success_rate"] == 75.0
        assert data["last_sent_at"] == "2026-03-17T11:00:00"

    def test_test_all_sends_for_each_enabled_config(self):
        mock_session = MagicMock()
        mock_session.exec.return_value = _ExecResult(
            [
                SimpleNamespace(channel="telegram", channel_user_id="10001"),
                SimpleNamespace(channel="telegram", channel_user_id="10002"),
            ]
        )
        client = _create_test_client(mock_session)

        with patch(
            "api.routes.system.notifications.notification_service.send_test",
            new=AsyncMock(side_effect=[True, False]),
        ) as mocked_send_test:
            response = client.post("/api/notifications/test-all")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["delivered"] == 1
        assert len(data["results"]) == 2
        assert data["results"][0]["channel_user_id"] == "10001"
        assert data["results"][0]["delivered"] is True
        assert data["results"][1]["channel_user_id"] == "10002"
        assert data["results"][1]["delivered"] is False
        assert mocked_send_test.await_count == 2

    def test_upsert_rejects_partial_quiet_hours(self):
        mock_session = MagicMock()
        client = _create_test_client(mock_session)

        response = client.put(
            "/api/notifications/config",
            json={
                "channel": "telegram",
                "channel_user_id": "10001",
                "is_enabled": True,
                "signal_threshold": "BUY",
                "quiet_hours_start": 22,
                "quiet_hours_end": None,
            },
        )

        assert response.status_code == 422
        assert "quiet_hours_start and quiet_hours_end" in response.json()["detail"]
        assert mock_session.exec.call_count == 0

    def test_upsert_rejects_unknown_fields(self):
        mock_session = MagicMock()
        client = _create_test_client(mock_session)

        response = client.put(
            "/api/notifications/config",
            json={
                "channel": "telegram",
                "channel_user_id": "10001",
                "is_enabled": True,
                "signal_threshold": "BUY",
                "extra_field": "not-allowed",
            },
        )

        assert response.status_code == 422

    def test_send_test_returns_strict_response_schema(self):
        mock_session = MagicMock()
        client = _create_test_client(mock_session)

        with patch(
            "api.routes.system.notifications.notification_service.send_test",
            new=AsyncMock(return_value=True),
        ) as mocked_send_test:
            response = client.post(
                "/api/notifications/test",
                json={"channel": "telegram", "channel_user_id": "10001"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data == {"ok": True, "message": "测试通知已发送"}
        assert mocked_send_test.await_count == 1
