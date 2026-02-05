"""回测 API 路由

提供策略回测、历史胜率统计等功能。
"""

import json
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select
import structlog

from services.backtest_service import backtest_engine, BacktestResult
from db.models import BacktestResultRecord, PredictionOutcome, AnalysisResult, engine

router = APIRouter(prefix="/backtest", tags=["Backtest"])
logger = structlog.get_logger(__name__)


# ============ Request/Response Models ============


class BacktestRequest(BaseModel):
    """回测请求"""
    symbol: str
    signals: Optional[List[dict]] = None  # 手动提供信号，若无则从历史分析获取
    initial_capital: float = 100000
    holding_days: int = 5
    stop_loss_pct: float = -5.0
    take_profit_pct: float = 10.0
    use_historical_signals: bool = True  # 使用历史分析记录的信号
    days_back: int = 180  # 回溯天数


class BacktestResponse(BaseModel):
    """回测响应"""
    symbol: str
    total_return_pct: float
    annualized_return_pct: float
    win_rate: float
    total_trades: int
    max_drawdown_pct: float
    sharpe_ratio: Optional[float]
    profit_factor: Optional[float]
    benchmark_return_pct: Optional[float]
    alpha: Optional[float]


class WinRateResponse(BaseModel):
    """胜率统计响应"""
    symbol: str
    period: str
    total_predictions: int
    evaluated_predictions: int
    correct_predictions: int
    win_rate: float
    avg_confidence: float
    avg_return: float
    signal_breakdown: dict


# ============ 回测端点 ============


@router.post("/run")
async def run_backtest(request: BacktestRequest):
    """运行策略回测

    可以使用手动提供的信号，或自动从历史分析记录获取。
    """
    try:
        signals = request.signals or []

        # 从历史分析获取信号
        if request.use_historical_signals and not signals:
            signals = _get_historical_signals(request.symbol, request.days_back)

        if not signals:
            raise HTTPException(
                status_code=400,
                detail="No signals provided and no historical signals found",
            )

        # 运行回测
        result = await backtest_engine.run_signal_backtest(
            symbol=request.symbol,
            signals=signals,
            initial_capital=request.initial_capital,
            holding_days=request.holding_days,
            stop_loss_pct=request.stop_loss_pct,
            take_profit_pct=request.take_profit_pct,
        )

        if result.error:
            raise HTTPException(status_code=400, detail=result.error)

        # 保存结果
        _save_backtest_result(result, request)

        return {
            "status": "success",
            "result": result.to_dict(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Backtest failed", error=str(e), symbol=request.symbol)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/background")
async def run_backtest_background(
    background_tasks: BackgroundTasks,
    request: BacktestRequest,
):
    """后台运行回测"""

    async def _run():
        try:
            signals = request.signals or []
            if request.use_historical_signals and not signals:
                signals = _get_historical_signals(request.symbol, request.days_back)

            if signals:
                result = await backtest_engine.run_signal_backtest(
                    symbol=request.symbol,
                    signals=signals,
                    initial_capital=request.initial_capital,
                    holding_days=request.holding_days,
                    stop_loss_pct=request.stop_loss_pct,
                    take_profit_pct=request.take_profit_pct,
                )
                _save_backtest_result(result, request)
                logger.info("Background backtest completed", symbol=request.symbol)
        except Exception as e:
            logger.error("Background backtest failed", error=str(e))

    background_tasks.add_task(_run)

    return {
        "status": "accepted",
        "symbol": request.symbol,
        "message": "Backtest started in background",
    }


def _get_historical_signals(symbol: str, days_back: int) -> List[dict]:
    """从历史分析记录获取信号"""
    cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    with Session(engine) as session:
        statement = (
            select(AnalysisResult)
            .where(AnalysisResult.symbol == symbol)
            .where(AnalysisResult.status == "completed")
            .where(AnalysisResult.date >= cutoff_date)
            .order_by(AnalysisResult.date.asc())
        )
        results = session.exec(statement).all()

        return [
            {
                "date": r.date,
                "signal": r.signal,
                "confidence": r.confidence,
            }
            for r in results
        ]


def _save_backtest_result(result: BacktestResult, request: BacktestRequest):
    """保存回测结果到数据库"""
    with Session(engine) as session:
        record = BacktestResultRecord(
            symbol=result.symbol,
            start_date=result.start_date,
            end_date=result.end_date,
            initial_capital=result.initial_capital,
            final_capital=result.final_capital,
            total_return_pct=result.total_return_pct,
            annualized_return_pct=result.annualized_return_pct,
            max_drawdown_pct=result.max_drawdown_pct,
            sharpe_ratio=result.sharpe_ratio,
            total_trades=result.total_trades,
            winning_trades=result.winning_trades,
            losing_trades=result.losing_trades,
            win_rate=result.win_rate,
            avg_win_pct=result.avg_win_pct,
            avg_loss_pct=result.avg_loss_pct,
            profit_factor=result.profit_factor,
            benchmark_return_pct=result.benchmark_return_pct,
            alpha=result.alpha,
            trades_json=json.dumps([t.to_dict() for t in result.trades], ensure_ascii=False),
            holding_days=request.holding_days,
            stop_loss_pct=request.stop_loss_pct,
            take_profit_pct=request.take_profit_pct,
        )
        session.add(record)
        session.commit()


# ============ 历史记录端点 ============


@router.get("/history/{symbol}")
async def get_backtest_history(
    symbol: str,
    limit: int = Query(default=10, ge=1, le=50),
):
    """获取股票的回测历史"""
    with Session(engine) as session:
        statement = (
            select(BacktestResultRecord)
            .where(BacktestResultRecord.symbol == symbol)
            .order_by(BacktestResultRecord.created_at.desc())
            .limit(limit)
        )
        records = session.exec(statement).all()

        return {
            "status": "success",
            "symbol": symbol,
            "count": len(records),
            "history": [
                {
                    "id": r.id,
                    "period": f"{r.start_date} ~ {r.end_date}",
                    "total_return_pct": r.total_return_pct,
                    "win_rate": f"{r.win_rate:.1%}",
                    "total_trades": r.total_trades,
                    "max_drawdown_pct": r.max_drawdown_pct,
                    "sharpe_ratio": r.sharpe_ratio,
                    "alpha": r.alpha,
                    "created_at": r.created_at.isoformat(),
                }
                for r in records
            ],
        }


@router.get("/history/{symbol}/{record_id}")
async def get_backtest_detail(symbol: str, record_id: int):
    """获取回测详情"""
    with Session(engine) as session:
        record = session.get(BacktestResultRecord, record_id)

        if not record or record.symbol != symbol:
            raise HTTPException(status_code=404, detail="Record not found")

        return {
            "status": "success",
            "symbol": record.symbol,
            "period": f"{record.start_date} ~ {record.end_date}",
            "initial_capital": record.initial_capital,
            "final_capital": record.final_capital,
            "total_return_pct": record.total_return_pct,
            "annualized_return_pct": record.annualized_return_pct,
            "max_drawdown_pct": record.max_drawdown_pct,
            "sharpe_ratio": record.sharpe_ratio,
            "win_rate": record.win_rate,
            "total_trades": record.total_trades,
            "winning_trades": record.winning_trades,
            "losing_trades": record.losing_trades,
            "avg_win_pct": record.avg_win_pct,
            "avg_loss_pct": record.avg_loss_pct,
            "profit_factor": record.profit_factor,
            "benchmark_return_pct": record.benchmark_return_pct,
            "alpha": record.alpha,
            "trades": json.loads(record.trades_json),
            "config": {
                "holding_days": record.holding_days,
                "stop_loss_pct": record.stop_loss_pct,
                "take_profit_pct": record.take_profit_pct,
            },
            "created_at": record.created_at.isoformat(),
        }


# ============ 胜率统计端点 ============


@router.get("/win-rate/{symbol}")
async def get_win_rate(
    symbol: str,
    days: int = Query(default=90, ge=7, le=365),
):
    """获取股票的预测胜率统计

    基于已评估的历史预测计算。
    """
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    with Session(engine) as session:
        statement = (
            select(PredictionOutcome)
            .where(PredictionOutcome.symbol == symbol)
            .where(PredictionOutcome.prediction_date >= cutoff_date)
        )
        predictions = session.exec(statement).all()

        total = len(predictions)
        evaluated = [p for p in predictions if p.outcome is not None]
        correct = [p for p in evaluated if p.is_correct]

        if not evaluated:
            return {
                "status": "success",
                "symbol": symbol,
                "period": f"Last {days} days",
                "total_predictions": total,
                "evaluated_predictions": 0,
                "win_rate": None,
                "message": "No evaluated predictions yet",
            }

        # 按信号类型统计
        signal_stats = {}
        for signal in ["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"]:
            signal_preds = [p for p in evaluated if p.signal == signal]
            if signal_preds:
                signal_correct = sum(1 for p in signal_preds if p.is_correct)
                signal_stats[signal] = {
                    "count": len(signal_preds),
                    "correct": signal_correct,
                    "accuracy": signal_correct / len(signal_preds),
                }

        avg_confidence = sum(p.confidence for p in evaluated) / len(evaluated)
        returns = [p.actual_return for p in evaluated if p.actual_return is not None]
        avg_return = sum(returns) / len(returns) if returns else 0

        return {
            "status": "success",
            "symbol": symbol,
            "period": f"Last {days} days",
            "total_predictions": total,
            "evaluated_predictions": len(evaluated),
            "correct_predictions": len(correct),
            "win_rate": len(correct) / len(evaluated),
            "avg_confidence": avg_confidence,
            "avg_return": avg_return,
            "signal_breakdown": signal_stats,
        }


@router.get("/win-rate/compare")
async def compare_win_rates(
    symbols: str = Query(..., description="Comma-separated symbols"),
    days: int = Query(default=90, ge=7, le=365),
):
    """比较多个股票的预测胜率"""
    symbol_list = [s.strip() for s in symbols.split(",")]
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    results = []
    with Session(engine) as session:
        for symbol in symbol_list:
            statement = (
                select(PredictionOutcome)
                .where(PredictionOutcome.symbol == symbol)
                .where(PredictionOutcome.prediction_date >= cutoff_date)
                .where(PredictionOutcome.outcome.is_not(None))
            )
            predictions = session.exec(statement).all()

            if predictions:
                correct = sum(1 for p in predictions if p.is_correct)
                results.append({
                    "symbol": symbol,
                    "total_predictions": len(predictions),
                    "win_rate": correct / len(predictions),
                    "avg_confidence": sum(p.confidence for p in predictions) / len(predictions),
                })
            else:
                results.append({
                    "symbol": symbol,
                    "total_predictions": 0,
                    "win_rate": None,
                    "avg_confidence": None,
                })

    # 按胜率排序
    results.sort(key=lambda x: x["win_rate"] or 0, reverse=True)

    return {
        "status": "success",
        "period": f"Last {days} days",
        "comparison": results,
    }


# ============ 综合看板端点 ============


@router.get("/dashboard")
async def get_backtest_dashboard():
    """获取回测综合看板"""
    with Session(engine) as session:
        # 最近的回测
        recent_backtests = session.exec(
            select(BacktestResultRecord)
            .order_by(BacktestResultRecord.created_at.desc())
            .limit(5)
        ).all()

        # 统计摘要
        all_backtests = session.exec(select(BacktestResultRecord)).all()

        avg_win_rate = 0
        avg_return = 0
        if all_backtests:
            avg_win_rate = sum(b.win_rate for b in all_backtests) / len(all_backtests)
            avg_return = sum(b.total_return_pct for b in all_backtests) / len(all_backtests)

        # 最佳/最差回测
        best_backtest = max(all_backtests, key=lambda x: x.total_return_pct) if all_backtests else None
        worst_backtest = min(all_backtests, key=lambda x: x.total_return_pct) if all_backtests else None

        return {
            "status": "success",
            "summary": {
                "total_backtests": len(all_backtests),
                "avg_win_rate": f"{avg_win_rate:.1%}",
                "avg_return": f"{avg_return:.1f}%",
            },
            "highlights": {
                "best_return": {
                    "symbol": best_backtest.symbol if best_backtest else None,
                    "return": best_backtest.total_return_pct if best_backtest else None,
                },
                "worst_return": {
                    "symbol": worst_backtest.symbol if worst_backtest else None,
                    "return": worst_backtest.total_return_pct if worst_backtest else None,
                },
            },
            "recent_backtests": [
                {
                    "symbol": b.symbol,
                    "total_return_pct": b.total_return_pct,
                    "win_rate": f"{b.win_rate:.1%}",
                    "total_trades": b.total_trades,
                    "created_at": b.created_at.isoformat(),
                }
                for b in recent_backtests
            ],
        }
