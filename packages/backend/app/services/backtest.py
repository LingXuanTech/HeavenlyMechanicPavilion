"""Backtesting service orchestrating historical replays and persistence."""

from __future__ import annotations

import asyncio
import json
import logging
import math
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.dataflows.local import get_YFin_data

from ..db import get_db_manager
from ..db.models import (
    BacktestArtifact,
    BacktestEquityCurvePoint,
    BacktestMetrics,
    BacktestRun,
)
from ..repositories import (
    BacktestArtifactRepository,
    BacktestEquityCurveRepository,
    BacktestMetricsRepository,
    BacktestRunRepository,
)
from ..schemas.backtest import BacktestParameters, StartBacktestRequest

logger = logging.getLogger(__name__)

DEFAULT_ANALYSTS = ["market", "social", "news", "fundamentals"]

ARTIFACT_DECISION_LOG = "decision_log"
ARTIFACT_TRADE_LOG = "trade_log"
ARTIFACT_SUMMARY = "summary"


@dataclass
class EquityPoint:
    timestamp: datetime
    price: float
    equity: float
    cash: float
    position: float
    daily_return: float


@dataclass
class TradeLog:
    timestamp: datetime
    action: str
    quantity: float
    price: float
    cash: float
    equity: float
    position: float


@dataclass
class DecisionLog:
    timestamp: datetime
    processed_signal: str
    raw_decision: Optional[str]
    equity: float
    price: float
    position: float


@dataclass
class PerformanceMetrics:
    total_return: float
    annualized_return: Optional[float]
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]
    volatility: Optional[float]
    max_drawdown: Optional[float]
    max_drawdown_duration: Optional[int]
    win_rate: Optional[float]
    best_trade_return: Optional[float]
    worst_trade_return: Optional[float]
    trades_executed: int
    holding_period_days: int


@dataclass
class BacktestResult:
    metrics: PerformanceMetrics
    equity_curve: List[EquityPoint]
    trades: List[TradeLog]
    decisions: List[DecisionLog]


class HistoricalReplayEngine:
    """Replay engine that drives the TradingAgents graph over historical data."""

    def __init__(
        self,
        *,
        symbol: str,
        parameters: BacktestParameters,
        config: Dict[str, Any],
    ) -> None:
        self.symbol = symbol
        self.parameters = parameters
        self.config = config
        self.selected_analysts = parameters.selected_analysts or DEFAULT_ANALYSTS
        self.graph = TradingAgentsGraph(
            selected_analysts=self.selected_analysts,
            config=deepcopy(config),
        )

    def run(self) -> BacktestResult:
        start = self.parameters.start_date
        end = self.parameters.end_date
        if end < start:
            raise ValueError("end_date must be after start_date")

        price_df = get_YFin_data(
            self.symbol,
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
        )
        if price_df.empty:
            raise ValueError(
                f"No market data found for {self.symbol} between {start} and {end}."
            )

        if "Date" not in price_df.columns:
            raise ValueError("Recorded market data missing 'Date' column")
        if "Close" not in price_df.columns:
            raise ValueError("Recorded market data missing 'Close' column")

        price_df = price_df.copy()
        price_df["Date"] = pd.to_datetime(price_df["Date"]).dt.tz_localize(None)
        price_df.sort_values("Date", inplace=True)

        equity_points: List[EquityPoint] = []
        trades: List[TradeLog] = []
        decisions: List[DecisionLog] = []
        trade_returns: List[float] = []
        daily_returns: List[float] = []

        cash = float(self.parameters.initial_capital)
        position = 0.0
        entry_price: Optional[float] = None

        prev_equity = cash
        peak_equity = cash
        max_drawdown = 0.0
        max_drawdown_duration = 0
        current_drawdown_duration = 0
        holding_period_days = 0

        risk_free_daily = self.parameters.risk_free_rate / 252.0

        for _, row in price_df.iterrows():
            price = float(row["Close"])
            timestamp = row["Date"].to_pydatetime()

            final_state, processed_signal = self.graph.propagate(
                self.symbol,
                timestamp.date().isoformat(),
            )

            signal = (processed_signal or "").strip().upper()
            if signal not in {"BUY", "SELL", "HOLD"}:
                logger.debug("Unrecognised signal '%s', defaulting to HOLD", signal)
                signal = "HOLD"

            target_position = 0.0
            if signal == "BUY":
                target_position = self.parameters.position_size
            elif signal == "SELL":
                target_position = -self.parameters.position_size

            # Close existing position if direction changes or flatten requested
            if position != 0.0 and target_position != position:
                if (
                    target_position == 0.0
                    or (position > 0 and target_position < position)
                    or (position < 0 and target_position > position)
                ):
                    closing_quantity = -position
                    cash -= closing_quantity * price
                    trades.append(
                        TradeLog(
                            timestamp=timestamp,
                            action="BUY" if closing_quantity > 0 else "SELL",
                            quantity=abs(closing_quantity),
                            price=price,
                            cash=cash,
                            equity=cash,
                            position=0.0,
                        )
                    )
                    if entry_price is not None:
                        if position > 0:
                            trade_returns.append((price - entry_price) / entry_price)
                        else:
                            trade_returns.append((entry_price - price) / entry_price)
                    position = 0.0
                    entry_price = None

            # Open / adjust towards target position
            if target_position != position:
                delta = target_position - position
                if delta != 0.0:
                    cash -= delta * price
                    new_position = position + delta
                    trades.append(
                        TradeLog(
                            timestamp=timestamp,
                            action="BUY" if delta > 0 else "SELL",
                            quantity=abs(delta),
                            price=price,
                            cash=cash,
                            equity=cash + new_position * price,
                            position=new_position,
                        )
                    )
                    position = new_position
                    entry_price = price if position != 0.0 else None

            equity = cash + position * price
            daily_return = (equity - prev_equity) / prev_equity if prev_equity else 0.0
            daily_returns.append(daily_return)
            prev_equity = equity

            if position != 0.0:
                holding_period_days += 1

            if equity > peak_equity:
                peak_equity = equity
                current_drawdown_duration = 0
            else:
                drawdown = (peak_equity - equity) / peak_equity if peak_equity else 0.0
                current_drawdown_duration += 1
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    max_drawdown_duration = current_drawdown_duration

            decisions.append(
                DecisionLog(
                    timestamp=timestamp,
                    processed_signal=signal,
                    raw_decision=str(final_state.get("final_trade_decision")),
                    equity=equity,
                    price=price,
                    position=position,
                )
            )

            equity_points.append(
                EquityPoint(
                    timestamp=timestamp,
                    price=price,
                    equity=equity,
                    cash=cash,
                    position=position,
                    daily_return=daily_return,
                )
            )

        # Close any remaining position at the final price for reporting metrics
        if equity_points and position != 0.0:
            last_point = equity_points[-1]
            price = last_point.price
            timestamp = last_point.timestamp
            closing_quantity = -position
            cash -= closing_quantity * price
            trades.append(
                TradeLog(
                    timestamp=timestamp,
                    action="BUY" if closing_quantity > 0 else "SELL",
                    quantity=abs(closing_quantity),
                    price=price,
                    cash=cash,
                    equity=cash,
                    position=0.0,
                )
            )
            if entry_price is not None:
                if position > 0:
                    trade_returns.append((price - entry_price) / entry_price)
                else:
                    trade_returns.append((entry_price - price) / entry_price)
            position = 0.0
            entry_price = None
            equity_points[-1] = EquityPoint(
                timestamp=timestamp,
                price=price,
                equity=cash,
                cash=cash,
                position=0.0,
                daily_return=equity_points[-1].daily_return,
            )
            decisions[-1] = DecisionLog(
                timestamp=timestamp,
                processed_signal=decisions[-1].processed_signal,
                raw_decision=decisions[-1].raw_decision,
                equity=cash,
                price=price,
                position=0.0,
            )

        total_return = (
            (equity_points[-1].equity / self.parameters.initial_capital) - 1.0
            if equity_points
            else 0.0
        )

        num_periods = max(len(equity_points), 1)
        annualized_return = None
        if num_periods > 1 and total_return != -1.0:
            years = num_periods / 252.0
            if years > 0:
                annualized_return = (1.0 + total_return) ** (1.0 / years) - 1.0

        volatility = None
        sharpe_ratio = None
        sortino_ratio = None

        if len(daily_returns) > 1:
            mean_return = sum(daily_returns) / len(daily_returns)
            variance = sum((r - mean_return) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
            std_dev = math.sqrt(variance) if variance > 0 else 0.0
            volatility = std_dev * math.sqrt(252.0)
            if std_dev > 0:
                sharpe_ratio = ((mean_return - risk_free_daily) / std_dev) * math.sqrt(252.0)

            downside = [min(0.0, r - risk_free_daily) for r in daily_returns]
            negative_downside = [abs(x) for x in downside if x < 0]
            if negative_downside:
                downside_variance = sum(x ** 2 for x in negative_downside) / len(negative_downside)
                downside_dev = math.sqrt(downside_variance)
                if downside_dev > 0:
                    sortino_ratio = ((mean_return - risk_free_daily) / downside_dev) * math.sqrt(252.0)

        win_rate = None
        best_trade_return = None
        worst_trade_return = None
        trades_executed = len(trade_returns)
        if trade_returns:
            positives = [r for r in trade_returns if r > 0]
            win_rate = len(positives) / len(trade_returns)
            best_trade_return = max(trade_returns)
            worst_trade_return = min(trade_returns)

        metrics = PerformanceMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            volatility=volatility,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_drawdown_duration,
            win_rate=win_rate,
            best_trade_return=best_trade_return,
            worst_trade_return=worst_trade_return,
            trades_executed=trades_executed,
            holding_period_days=holding_period_days,
        )

        return BacktestResult(
            metrics=metrics,
            equity_curve=equity_points,
            trades=trades,
            decisions=decisions,
        )


class BacktestService:
    """Coordinates asynchronous backtest execution and persistence."""

    def __init__(
        self,
        *,
        config_overrides: Optional[Dict[str, Any]] = None,
        max_workers: int = 2,
    ) -> None:
        self._base_config = deepcopy(DEFAULT_CONFIG)
        if config_overrides:
            self._base_config.update(config_overrides)
        self._tasks: Dict[str, asyncio.Task[Any]] = {}
        self._semaphore = asyncio.Semaphore(max_workers)

    async def start_backtest(
        self,
        *,
        session: BacktestRunRepository,
        request: StartBacktestRequest,
    ) -> BacktestRun:
        params = request.parameters
        if not params.symbols:
            raise ValueError("At least one symbol must be provided for backtesting")
        if params.end_date < params.start_date:
            raise ValueError("end_date must be after start_date")

        symbol = params.symbols[0]
        config = self._compose_config(params, request.config_overrides)

        run = BacktestRun(
            run_id=self._generate_run_id(),
            name=request.name,
            description=request.description,
            symbols=",".join(params.symbols),
            start_date=params.start_date,
            end_date=params.end_date,
            initial_capital=params.initial_capital,
            position_size=params.position_size,
            risk_free_rate=params.risk_free_rate,
            status="PENDING",
            parameters_json=json.dumps(request.parameters.model_dump(mode="json"), default=str),
            config_snapshot=json.dumps(config, default=str),
        )
        created_run = await session.create(run)

        loop = asyncio.get_running_loop()
        task = loop.create_task(
            self._execute_backtest(
                run_db_id=created_run.id,
                run_identifier=created_run.run_id,
                symbol=symbol,
                params=params,
                overrides=request.config_overrides or {},
            )
        )
        self._tasks[created_run.run_id] = task
        task.add_done_callback(lambda _: self._tasks.pop(created_run.run_id, None))
        return created_run

    async def _execute_backtest(
        self,
        *,
        run_db_id: int,
        run_identifier: str,
        symbol: str,
        params: BacktestParameters,
        overrides: Dict[str, Any],
    ) -> None:
        async with self._semaphore:
            db_manager = get_db_manager()
            async with db_manager.session_factory() as session:  # type: ignore[attr-defined]
                run_repo = BacktestRunRepository(session)
                metrics_repo = BacktestMetricsRepository(session)
                equity_repo = BacktestEquityCurveRepository(session)
                artifact_repo = BacktestArtifactRepository(session)

                run = await run_repo.get(run_db_id)
                if not run:
                    logger.error("Backtest run %s not found", run_identifier)
                    return

                start_ts = datetime.utcnow()
                await run_repo.update(
                    db_obj=run,
                    obj_in={
                        "status": "RUNNING",
                        "started_at": start_ts,
                        "error_message": None,
                    },
                )

                config = self._compose_config(params, overrides)

                try:
                    engine = HistoricalReplayEngine(
                        symbol=symbol,
                        parameters=params,
                        config=config,
                    )
                    result = await asyncio.to_thread(engine.run)
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.exception("Backtest %s failed: %s", run_identifier, exc)
                    await run_repo.update(
                        db_obj=run,
                        obj_in={
                            "status": "FAILED",
                            "completed_at": datetime.utcnow(),
                            "duration_seconds": None,
                            "error_message": str(exc),
                        },
                    )
                    return

                end_ts = datetime.utcnow()
                duration_seconds = (end_ts - start_ts).total_seconds()

                await metrics_repo.delete_for_run(run_db_id)
                await equity_repo.delete_for_run(run_db_id)
                await artifact_repo.delete_for_run(run_db_id)

                metrics = result.metrics
                metrics_model = BacktestMetrics(
                    run_id=run_db_id,
                    total_return=metrics.total_return,
                    annualized_return=metrics.annualized_return,
                    sharpe_ratio=metrics.sharpe_ratio,
                    sortino_ratio=metrics.sortino_ratio,
                    volatility=metrics.volatility,
                    max_drawdown=metrics.max_drawdown,
                    max_drawdown_duration=metrics.max_drawdown_duration,
                    win_rate=metrics.win_rate,
                    best_trade_return=metrics.best_trade_return,
                    worst_trade_return=metrics.worst_trade_return,
                    trades_executed=metrics.trades_executed,
                    holding_period_days=metrics.holding_period_days,
                    metadata_json=json.dumps(
                        {
                            "risk_free_rate": params.risk_free_rate,
                            "position_size": params.position_size,
                        }
                    ),
                )
                await metrics_repo.create(metrics_model)

                equity_points = [
                    BacktestEquityCurvePoint(
                        run_id=run_db_id,
                        timestamp=point.timestamp,
                        price=point.price,
                        equity=point.equity,
                        cash=point.cash,
                        position=point.position,
                        daily_return=point.daily_return,
                    )
                    for point in result.equity_curve
                ]
                if equity_points:
                    await equity_repo.create_many(equity_points)

                artifacts: List[BacktestArtifact] = []
                artifacts.append(
                    BacktestArtifact(
                        run_id=run_db_id,
                        artifact_type=ARTIFACT_DECISION_LOG,
                        content=json.dumps([asdict(d) for d in result.decisions], default=str),
                        description="Per-bar decision log",
                    )
                )
                artifacts.append(
                    BacktestArtifact(
                        run_id=run_db_id,
                        artifact_type=ARTIFACT_TRADE_LOG,
                        content=json.dumps([asdict(t) for t in result.trades], default=str),
                        description="Executed trade log",
                    )
                )
                summary_payload = {
                    "metrics": asdict(metrics),
                    "parameters": params.model_dump(mode="json"),
                }
                artifacts.append(
                    BacktestArtifact(
                        run_id=run_db_id,
                        artifact_type=ARTIFACT_SUMMARY,
                        content=json.dumps(summary_payload, default=str),
                        description="Summary metrics payload",
                    )
                )
                await artifact_repo.create_many(artifacts)

                sharpe_text = (
                    f"{metrics.sharpe_ratio:.2f}" if metrics.sharpe_ratio is not None else "n/a"
                )
                max_dd_text = (
                    f"{metrics.max_drawdown:.2%}" if metrics.max_drawdown is not None else "n/a"
                )
                summary_text = (
                    f"Total return {metrics.total_return:.2%}, "
                    f"Sharpe {sharpe_text}, "
                    f"Max DD {max_dd_text}"
                )

                await run_repo.update(
                    db_obj=run,
                    obj_in={
                        "status": "COMPLETED",
                        "completed_at": end_ts,
                        "duration_seconds": duration_seconds,
                        "result_summary": summary_text,
                        "error_message": None,
                    },
                )

    async def list_runs(
        self,
        *,
        session: BacktestRunRepository,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[BacktestRun]:
        if status:
            return await session.list_by_status(status=status, skip=skip, limit=limit)
        return await session.list_recent(skip=skip, limit=limit)

    async def get_run(
        self,
        *,
        session: BacktestRunRepository,
        run_id: str,
    ) -> Optional[BacktestRun]:
        return await session.get_by_run_id(run_id)

    async def get_run_details(
        self,
        *,
        session: BacktestRunRepository,
        run_id: str,
    ) -> Optional[Dict[str, Any]]:
        run = await session.get_by_run_id(run_id)
        if not run:
            return None

        metrics_repo = BacktestMetricsRepository(session.session)
        equity_repo = BacktestEquityCurveRepository(session.session)
        artifact_repo = BacktestArtifactRepository(session.session)

        metrics = await metrics_repo.get_by_run_id(run.id)
        equity_curve = await equity_repo.get_points(run.id)
        artifacts = await artifact_repo.list_for_run(run.id)

        return {
            "run": run,
            "metrics": metrics,
            "equity_curve": equity_curve,
            "artifacts": artifacts,
        }

    async def compare_runs(
        self,
        *,
        session: BacktestRunRepository,
        run_ids: Iterable[str],
    ) -> List[Dict[str, Any]]:
        comparisons: List[Dict[str, Any]] = []
        metrics_repo = BacktestMetricsRepository(session.session)
        for run_id in run_ids:
            run = await session.get_by_run_id(run_id)
            if not run:
                continue
            metrics = await metrics_repo.get_by_run_id(run.id)
            comparisons.append({"run": run, "metrics": metrics})
        return comparisons

    async def export_run(
        self,
        *,
        session: BacktestRunRepository,
        run_id: str,
    ) -> Optional[Dict[str, Any]]:
        details = await self.get_run_details(session=session, run_id=run_id)
        if not details:
            return None

        artifacts_repo = BacktestArtifactRepository(session.session)
        decision_artifact = await artifacts_repo.get_by_type(details["run"].id, ARTIFACT_DECISION_LOG)
        trade_artifact = await artifacts_repo.get_by_type(details["run"].id, ARTIFACT_TRADE_LOG)

        decisions = json.loads(decision_artifact.content) if decision_artifact and decision_artifact.content else []
        trades = json.loads(trade_artifact.content) if trade_artifact and trade_artifact.content else []

        return {
            "run": details["run"],
            "metrics": details["metrics"],
            "equity_curve": details["equity_curve"],
            "artifacts": details["artifacts"],
            "decisions": decisions,
            "trades": trades,
        }

    def _compose_config(
        self,
        params: BacktestParameters,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        config = deepcopy(self._base_config)
        if overrides:
            config.update(overrides)

        config.setdefault("data_vendors", {})
        data_vendor = params.data_vendor or config["data_vendors"].get("core_stock_apis")
        if data_vendor:
            config["data_vendors"]["core_stock_apis"] = data_vendor
            config["data_vendors"]["technical_indicators"] = data_vendor
            if data_vendor == "local":
                config["data_vendors"]["fundamental_data"] = "local"
                config["data_vendors"]["news_data"] = "local"

        if params.data_dir:
            config["data_dir"] = params.data_dir

        return config

    @staticmethod
    def _generate_run_id() -> str:
        return datetime.utcnow().strftime("bt-%Y%m%d%H%M%S%f")
