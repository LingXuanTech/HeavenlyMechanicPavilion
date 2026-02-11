"""Backtest API 集成测试。"""

from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.trading.backtest import router as backtest_router
from services.backtest_service import BacktestResult


def _create_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(backtest_router, prefix="/api")
    return TestClient(app)


def _build_mock_backtest_result(symbol: str) -> BacktestResult:
    return BacktestResult(
        symbol=symbol,
        start_date="2026-02-01",
        end_date="2026-02-11",
        initial_capital=100000,
        final_capital=103200,
        total_return_pct=3.2,
        annualized_return_pct=14.6,
        max_drawdown_pct=-2.1,
        sharpe_ratio=1.28,
        win_rate=0.6,
        total_trades=5,
        winning_trades=3,
        losing_trades=2,
        avg_win_pct=2.1,
        avg_loss_pct=-1.3,
        profit_factor=1.65,
        benchmark_return_pct=1.1,
        alpha=2.1,
        trades=[],
        error=None,
    )


class TestBacktestRunRoute:
    """校验回测入口对 hint 信号的兼容性。"""

    def test_run_backtest_normalizes_hint_signal_and_date(self):
        client = _create_test_client()

        mock_run = AsyncMock(return_value=_build_mock_backtest_result("AAPL"))
        with (
            patch("api.routes.trading.backtest.backtest_engine.run_signal_backtest", new=mock_run),
            patch("api.routes.trading.backtest._save_backtest_result"),
        ):
            response = client.post(
                "/api/backtest/run",
                json={
                    "symbol": "AAPL",
                    "signals": [
                        {
                            "date": "2026-02-11T10:30:00Z",
                            "signal": "bullish",
                            "confidence": 0.82,
                        }
                    ],
                    "use_historical_signals": False,
                },
            )

        assert response.status_code == 200
        assert response.json()["status"] == "success"

        called_signals = mock_run.await_args.kwargs["signals"]
        assert called_signals == [
            {
                "date": "2026-02-11",
                "signal": "Buy",
                "confidence": 82,
            }
        ]

    def test_run_backtest_normalizes_historical_signal_payload(self):
        client = _create_test_client()

        mock_run = AsyncMock(return_value=_build_mock_backtest_result("MSFT"))
        mock_history = [
            {
                "date": "2026-01-30",
                "signal": "strong_buy",
                "confidence": "65",
            },
            {
                "date": "2026-02-03T09:00:00",
                "signal": "neutral",
                "confidence": 0.4,
            },
        ]

        with (
            patch("api.routes.trading.backtest.backtest_engine.run_signal_backtest", new=mock_run),
            patch("api.routes.trading.backtest._save_backtest_result"),
            patch("api.routes.trading.backtest._get_historical_signals", return_value=mock_history) as mock_get_history,
        ):
            response = client.post(
                "/api/backtest/run",
                json={
                    "symbol": "MSFT",
                    "use_historical_signals": True,
                    "days_back": 120,
                },
            )

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        mock_get_history.assert_called_once_with("MSFT", 120)

        called_signals = mock_run.await_args.kwargs["signals"]
        assert called_signals == [
            {
                "date": "2026-01-30",
                "signal": "Strong Buy",
                "confidence": 65,
            },
            {
                "date": "2026-02-03",
                "signal": "Hold",
                "confidence": 40,
            },
        ]
