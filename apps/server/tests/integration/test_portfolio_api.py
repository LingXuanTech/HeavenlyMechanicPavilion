"""Portfolio API 集成测试。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.trading.portfolio import router as portfolio_router


def _create_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(portfolio_router, prefix="/api")
    return TestClient(app)


class TestPortfolioQuickCheckRoute:
    """校验 quick-check 路由契约与错误映射行为。"""

    def test_quick_check_returns_schema_when_symbols_insufficient(self):
        client = _create_test_client()

        response = client.get("/api/portfolio/quick-check", params={"symbols": "AAPL"})

        assert response.status_code == 200
        data = response.json()
        assert data["diversification_score"] == 0.0
        assert data["risk_clusters_count"] == 0
        assert data["top_recommendation"] is None
        assert data["message"] == "至少需要 2 个股票"

    def test_quick_check_returns_schema_when_success(self):
        client = _create_test_client()

        mocked_analysis = SimpleNamespace(
            diversification_score=61.5,
            risk_clusters=[{"stocks": ["AAPL", "MSFT"], "avg_correlation": 0.81, "risk_level": "High"}],
            recommendations=["✅ 组合分散度良好，风险分布较为均衡"],
        )

        mocked_analyze = AsyncMock(return_value=mocked_analysis)
        with patch("api.routes.trading.portfolio.analyze_portfolio", new=mocked_analyze):
            response = client.get(
                "/api/portfolio/quick-check",
                params={
                    "symbols": "AAPL,MSFT",
                    "period": "3mo",
                    "cluster_threshold": "0.82",
                    "weights": "70,30",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["diversification_score"] == 61.5
        assert data["risk_clusters_count"] == 1
        assert data["top_recommendation"] == "✅ 组合分散度良好，风险分布较为均衡"
        assert data["message"] is None

        assert mocked_analyze.await_count == 1
        request_obj = mocked_analyze.await_args.args[0]
        assert request_obj.symbols == ["AAPL", "MSFT"]
        assert request_obj.period == "3mo"
        assert request_obj.cluster_threshold == 0.82
        assert request_obj.weights == [70.0, 30.0]

    def test_quick_check_rejects_non_numeric_weights(self):
        client = _create_test_client()

        response = client.get(
            "/api/portfolio/quick-check",
            params={"symbols": "AAPL,MSFT", "weights": "70,abc"},
        )

        assert response.status_code == 400
        assert "weights" in response.json()["detail"]

    def test_quick_check_rejects_mismatched_weights_length(self):
        client = _create_test_client()

        response = client.get(
            "/api/portfolio/quick-check",
            params={"symbols": "AAPL,MSFT", "weights": "100"},
        )

        assert response.status_code == 400
        assert "weights" in response.json()["detail"]

    def test_quick_check_rejects_negative_weights(self):
        client = _create_test_client()

        response = client.get(
            "/api/portfolio/quick-check",
            params={"symbols": "AAPL,MSFT", "weights": "50,-10"},
        )

        assert response.status_code == 400
        assert "weights" in response.json()["detail"]

    def test_quick_check_rejects_invalid_cluster_threshold(self):
        client = _create_test_client()

        response = client.get(
            "/api/portfolio/quick-check",
            params={"symbols": "AAPL,MSFT", "cluster_threshold": "1.2"},
        )

        assert response.status_code == 422

    def test_quick_check_rejects_invalid_period(self):
        client = _create_test_client()

        response = client.get(
            "/api/portfolio/quick-check",
            params={"symbols": "AAPL,MSFT", "period": "2y"},
        )

        assert response.status_code == 422

    def test_quick_check_maps_unexpected_error_to_http_500(self):
        client = _create_test_client()

        with patch(
            "api.routes.trading.portfolio.analyze_portfolio",
            new=AsyncMock(side_effect=Exception("boom")),
        ):
            response = client.get("/api/portfolio/quick-check", params={"symbols": "AAPL,MSFT"})

        assert response.status_code == 500
        assert "快速检查失败" in response.json()["detail"]


class TestPortfolioAnalyzeRoute:
    """校验 analyze 路由新增再平衡建议字段。"""

    @staticmethod
    def _build_history(prices: list[float]) -> list[SimpleNamespace]:
        return [SimpleNamespace(close=price) for price in prices]

    def test_analyze_returns_rebalance_suggestions(self):
        client = _create_test_client()

        history_map = {
            "AAPL": self._build_history([100, 102, 105, 108, 111, 114]),
            "MSFT": self._build_history([100, 100.8, 101.6, 102.4, 103.1, 103.8]),
            "TSLA": self._build_history([100, 97, 94, 95, 91, 89]),
        }

        async def mocked_get_history(symbol: str, period: str):
            return history_map[symbol]

        with patch("api.routes.trading.portfolio.MarketRouter.get_history", new=AsyncMock(side_effect=mocked_get_history)):
            response = client.post(
                "/api/portfolio/analyze",
                json={
                    "symbols": ["AAPL", "MSFT", "TSLA"],
                    "period": "1mo",
                    "cluster_threshold": 0.7,
                    "weights": [60, 25, 15],
                },
            )

        assert response.status_code == 200
        data = response.json()

        suggestions = data["rebalance_suggestions"]
        assert len(suggestions) == len(data["correlation"]["symbols"])
        assert 0 <= data["recommended_turnover"] <= 1
        assert any("再平衡建议" in recommendation for recommendation in data["recommendations"])

        abs_deltas = [abs(item["delta_weight"]) for item in suggestions]
        assert abs_deltas == sorted(abs_deltas, reverse=True)

        current_weight_sum = sum(item["current_weight"] for item in suggestions)
        target_weight_sum = sum(item["target_weight"] for item in suggestions)
        assert abs(current_weight_sum - 1) < 1e-6
        assert abs(target_weight_sum - 1) < 1e-4

        for item in suggestions:
            assert item["action"] in {"increase", "decrease", "hold"}
            assert 0 <= item["confidence"] <= 1
            assert isinstance(item["rationale"], str) and item["rationale"]
            assert "symbol" in item
            assert "volatility" in item
            assert "avg_abs_correlation" in item
            assert "total_return" in item

    def test_analyze_uses_equal_weights_for_rebalance_when_weights_missing(self):
        client = _create_test_client()

        history_map = {
            "AAPL": self._build_history([100, 101, 102, 103, 104, 105]),
            "MSFT": self._build_history([100, 100.5, 101, 101.4, 102.1, 102.8]),
            "TSLA": self._build_history([100, 99, 98, 97, 96, 95]),
        }

        async def mocked_get_history(symbol: str, period: str):
            return history_map[symbol]

        with patch("api.routes.trading.portfolio.MarketRouter.get_history", new=AsyncMock(side_effect=mocked_get_history)):
            response = client.post(
                "/api/portfolio/analyze",
                json={
                    "symbols": ["AAPL", "MSFT", "TSLA"],
                    "period": "1mo",
                    "cluster_threshold": 0.7,
                },
            )

        assert response.status_code == 200
        suggestions = response.json()["rebalance_suggestions"]
        assert len(suggestions) == 3

        expected_equal_weight = 1 / 3
        for item in suggestions:
            assert abs(item["current_weight"] - expected_equal_weight) < 1e-6

    def test_analyze_applies_constraints_and_returns_backtest_hint(self):
        client = _create_test_client()

        history_map = {
            "AAPL": self._build_history([100, 104, 108, 112, 116, 121]),
            "MSFT": self._build_history([100, 102, 103, 104, 106, 107]),
            "TSLA": self._build_history([100, 96, 94, 95, 92, 90]),
            "NVDA": self._build_history([100, 101, 103, 105, 106, 108]),
        }

        async def mocked_get_history(symbol: str, period: str):
            return history_map[symbol]

        with patch("api.routes.trading.portfolio.MarketRouter.get_history", new=AsyncMock(side_effect=mocked_get_history)):
            response = client.post(
                "/api/portfolio/analyze",
                json={
                    "symbols": ["AAPL", "MSFT", "TSLA", "NVDA"],
                    "period": "1mo",
                    "cluster_threshold": 0.7,
                    "weights": [70, 15, 10, 5],
                    "constraints": {
                        "max_single_weight": 0.4,
                        "max_top2_weight": 0.6,
                        "max_turnover": 0.12,
                        "risk_profile": "conservative",
                    },
                    "enable_backtest_hint": True,
                },
            )

        assert response.status_code == 200
        data = response.json()

        suggestions = data["rebalance_suggestions"]
        assert len(suggestions) == 4

        max_single = max(item["target_weight"] for item in suggestions)
        assert max_single <= 0.4 + 1e-4

        sorted_weights = sorted((item["target_weight"] for item in suggestions), reverse=True)
        top2_weight = sorted_weights[0] + sorted_weights[1]

        turnover = sum(abs(item["delta_weight"]) for item in suggestions) / 2

        assert "constraint_violations" in data
        assert isinstance(data["constraint_violations"], list)

        violation_codes = {item["code"] for item in data["constraint_violations"]}
        if top2_weight > 0.6 + 1e-4:
            assert "top2_cap_unmet" in violation_codes
        else:
            assert top2_weight <= 0.6 + 1e-4

        if turnover > 0.12 + 1e-4:
            assert "turnover_unmet" in violation_codes
        else:
            assert turnover <= 0.12 + 1e-4

        backtest_hint = data["backtest_payload_hint"]
        assert backtest_hint is not None
        assert backtest_hint["strategy_name"] == "portfolio_rebalance_conservative"
        assert len(backtest_hint["requests"]) == len(suggestions)
        for request in backtest_hint["requests"]:
            assert "symbol" in request
            assert request["use_historical_signals"] is False
            assert request["holding_days"] == 10
            assert len(request["signals"]) == 1

    def test_analyze_rejects_inconsistent_constraints(self):
        client = _create_test_client()

        response = client.post(
            "/api/portfolio/analyze",
            json={
                "symbols": ["AAPL", "MSFT"],
                "period": "1mo",
                "cluster_threshold": 0.7,
                "constraints": {
                    "max_single_weight": 0.6,
                    "max_top2_weight": 0.5,
                    "max_turnover": 0.3,
                    "risk_profile": "balanced",
                },
            },
        )

        assert response.status_code == 400
        assert "max_top2_weight" in response.json()["detail"]
