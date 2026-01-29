"""回测服务

基于历史数据进行策略回测，计算胜率和收益。
"""

import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import structlog

try:
    import pandas as pd
    import numpy as np
except ImportError:
    pd = None
    np = None

from services.data_router import MarketRouter

logger = structlog.get_logger(__name__)


class SignalType(str, Enum):
    """信号类型"""
    STRONG_BUY = "Strong Buy"
    BUY = "Buy"
    HOLD = "Hold"
    SELL = "Sell"
    STRONG_SELL = "Strong Sell"


@dataclass
class TradeRecord:
    """交易记录"""
    entry_date: str
    entry_price: float
    signal: str
    confidence: int
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    return_pct: Optional[float] = None
    is_winner: Optional[bool] = None
    holding_days: Optional[int] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BacktestResult:
    """回测结果"""
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return_pct: float
    annualized_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: Optional[float]
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win_pct: float
    avg_loss_pct: float
    profit_factor: Optional[float]
    trades: List[TradeRecord] = field(default_factory=list)
    benchmark_return_pct: Optional[float] = None
    alpha: Optional[float] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["trades"] = [t.to_dict() for t in self.trades]
        return result


class BacktestEngine:
    """回测引擎

    功能：
    1. 获取历史数据
    2. 模拟交易执行
    3. 计算绩效指标
    """

    # 默认参数
    DEFAULT_HOLDING_DAYS = 5  # 默认持仓天数
    DEFAULT_STOP_LOSS_PCT = -5.0  # 默认止损百分比
    DEFAULT_TAKE_PROFIT_PCT = 10.0  # 默认止盈百分比
    RISK_FREE_RATE = 0.03  # 无风险利率（年化）

    def __init__(self, market_router: Optional[MarketRouter] = None):
        self.market_router = market_router or MarketRouter()

    async def run_signal_backtest(
        self,
        symbol: str,
        signals: List[Dict[str, Any]],
        initial_capital: float = 100000,
        holding_days: int = DEFAULT_HOLDING_DAYS,
        stop_loss_pct: float = DEFAULT_STOP_LOSS_PCT,
        take_profit_pct: float = DEFAULT_TAKE_PROFIT_PCT,
    ) -> BacktestResult:
        """运行信号回测

        Args:
            symbol: 股票代码
            signals: 信号列表 [{"date": "2024-01-01", "signal": "Buy", "confidence": 75}, ...]
            initial_capital: 初始资金
            holding_days: 持仓天数
            stop_loss_pct: 止损百分比
            take_profit_pct: 止盈百分比

        Returns:
            回测结果
        """
        if not signals:
            return BacktestResult(
                symbol=symbol,
                start_date="",
                end_date="",
                initial_capital=initial_capital,
                final_capital=initial_capital,
                total_return_pct=0,
                annualized_return_pct=0,
                max_drawdown_pct=0,
                sharpe_ratio=None,
                win_rate=0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                avg_win_pct=0,
                avg_loss_pct=0,
                profit_factor=None,
                error="No signals provided",
            )

        # 获取历史数据
        try:
            start_date = min(s["date"] for s in signals)
            end_date = max(s["date"] for s in signals)
            # 扩展结束日期以覆盖持仓期
            extended_end = (
                datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=holding_days + 10)
            ).strftime("%Y-%m-%d")

            price_data = await self._get_historical_prices(symbol, start_date, extended_end)

            if price_data is None or len(price_data) == 0:
                return BacktestResult(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=initial_capital,
                    final_capital=initial_capital,
                    total_return_pct=0,
                    annualized_return_pct=0,
                    max_drawdown_pct=0,
                    sharpe_ratio=None,
                    win_rate=0,
                    total_trades=0,
                    winning_trades=0,
                    losing_trades=0,
                    avg_win_pct=0,
                    avg_loss_pct=0,
                    profit_factor=None,
                    error="Failed to fetch historical price data",
                )

        except Exception as e:
            logger.error("Failed to get historical data", symbol=symbol, error=str(e))
            return BacktestResult(
                symbol=symbol,
                start_date="",
                end_date="",
                initial_capital=initial_capital,
                final_capital=initial_capital,
                total_return_pct=0,
                annualized_return_pct=0,
                max_drawdown_pct=0,
                sharpe_ratio=None,
                win_rate=0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                avg_win_pct=0,
                avg_loss_pct=0,
                profit_factor=None,
                error=str(e),
            )

        # 执行回测
        trades = []
        capital = initial_capital
        capital_history = [capital]

        for signal_data in sorted(signals, key=lambda x: x["date"]):
            signal = signal_data["signal"]
            signal_date = signal_data["date"]
            confidence = signal_data.get("confidence", 50)

            # 只处理买入信号
            if signal not in ["Strong Buy", "Buy"]:
                continue

            # 获取入场价格
            entry_price = self._get_price_on_date(price_data, signal_date)
            if entry_price is None:
                continue

            # 计算出场价格（持仓 N 天后或触发止损/止盈）
            exit_date, exit_price = self._calculate_exit(
                price_data,
                signal_date,
                entry_price,
                holding_days,
                stop_loss_pct,
                take_profit_pct,
            )

            if exit_price is None:
                continue

            # 计算收益
            return_pct = (exit_price - entry_price) / entry_price * 100
            is_winner = return_pct > 0

            # 更新资金
            position_size = capital * 0.1  # 每次用 10% 资金
            capital += position_size * (return_pct / 100)
            capital_history.append(capital)

            # 计算持仓天数
            try:
                entry_dt = datetime.strptime(signal_date, "%Y-%m-%d")
                exit_dt = datetime.strptime(exit_date, "%Y-%m-%d")
                holding = (exit_dt - entry_dt).days
            except:
                holding = holding_days

            trade = TradeRecord(
                entry_date=signal_date,
                entry_price=entry_price,
                signal=signal,
                confidence=confidence,
                exit_date=exit_date,
                exit_price=exit_price,
                return_pct=round(return_pct, 2),
                is_winner=is_winner,
                holding_days=holding,
            )
            trades.append(trade)

        # 计算统计指标
        return self._calculate_statistics(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            final_capital=capital,
            trades=trades,
            capital_history=capital_history,
            price_data=price_data,
        )

    async def _get_historical_prices(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> Optional[Dict[str, float]]:
        """获取历史价格数据

        Returns:
            日期 -> 收盘价的映射
        """
        try:
            # 尝试使用 yfinance 获取历史数据
            import yfinance as yf

            # 转换股票代码
            ticker = self._convert_symbol_for_yfinance(symbol)

            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)

            if hist.empty:
                return None

            return {
                date.strftime("%Y-%m-%d"): float(row["Close"])
                for date, row in hist.iterrows()
            }

        except Exception as e:
            logger.warning("Failed to get historical prices", symbol=symbol, error=str(e))
            return None

    def _convert_symbol_for_yfinance(self, symbol: str) -> str:
        """转换股票代码为 yfinance 格式"""
        if symbol.endswith(".SZ"):
            return symbol.replace(".SZ", ".SZ")
        elif symbol.endswith(".SH"):
            return symbol.replace(".SH", ".SS")
        elif symbol.endswith(".HK"):
            # 港股需要补零
            code = symbol.replace(".HK", "")
            return f"{code.zfill(4)}.HK"
        return symbol

    def _get_price_on_date(
        self,
        price_data: Dict[str, float],
        target_date: str,
    ) -> Optional[float]:
        """获取指定日期的价格（如果当天无数据，取下一个交易日）"""
        if target_date in price_data:
            return price_data[target_date]

        # 尝试找下一个交易日
        sorted_dates = sorted(price_data.keys())
        for date in sorted_dates:
            if date >= target_date:
                return price_data[date]

        return None

    def _calculate_exit(
        self,
        price_data: Dict[str, float],
        entry_date: str,
        entry_price: float,
        holding_days: int,
        stop_loss_pct: float,
        take_profit_pct: float,
    ) -> Tuple[Optional[str], Optional[float]]:
        """计算出场日期和价格"""
        sorted_dates = sorted(d for d in price_data.keys() if d > entry_date)

        for i, date in enumerate(sorted_dates[:holding_days + 5]):
            price = price_data[date]
            return_pct = (price - entry_price) / entry_price * 100

            # 检查止损/止盈
            if return_pct <= stop_loss_pct or return_pct >= take_profit_pct:
                return date, price

            # 达到持仓天数
            if i >= holding_days - 1:
                return date, price

        # 如果没有足够的数据，返回最后可用的价格
        if sorted_dates:
            last_date = sorted_dates[min(len(sorted_dates) - 1, holding_days)]
            return last_date, price_data[last_date]

        return None, None

    def _calculate_statistics(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        initial_capital: float,
        final_capital: float,
        trades: List[TradeRecord],
        capital_history: List[float],
        price_data: Dict[str, float],
    ) -> BacktestResult:
        """计算回测统计指标"""
        total_trades = len(trades)

        if total_trades == 0:
            return BacktestResult(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                final_capital=final_capital,
                total_return_pct=0,
                annualized_return_pct=0,
                max_drawdown_pct=0,
                sharpe_ratio=None,
                win_rate=0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                avg_win_pct=0,
                avg_loss_pct=0,
                profit_factor=None,
                trades=trades,
            )

        # 基础统计
        winning_trades = [t for t in trades if t.is_winner]
        losing_trades = [t for t in trades if not t.is_winner]
        win_count = len(winning_trades)
        loss_count = len(losing_trades)

        win_rate = win_count / total_trades if total_trades > 0 else 0

        avg_win = (
            sum(t.return_pct for t in winning_trades) / win_count
            if win_count > 0 else 0
        )
        avg_loss = (
            sum(t.return_pct for t in losing_trades) / loss_count
            if loss_count > 0 else 0
        )

        # 收益计算
        total_return_pct = (final_capital - initial_capital) / initial_capital * 100

        # 年化收益
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            years = (end_dt - start_dt).days / 365
            if years > 0:
                annualized_return = ((final_capital / initial_capital) ** (1 / years) - 1) * 100
            else:
                annualized_return = total_return_pct
        except:
            annualized_return = total_return_pct

        # 最大回撤
        max_drawdown = self._calculate_max_drawdown(capital_history)

        # 夏普比率
        sharpe = self._calculate_sharpe_ratio(trades)

        # 盈亏比
        total_win = sum(t.return_pct for t in winning_trades) if winning_trades else 0
        total_loss = abs(sum(t.return_pct for t in losing_trades)) if losing_trades else 0
        profit_factor = total_win / total_loss if total_loss > 0 else None

        # 基准收益（买入持有）
        benchmark_return = None
        alpha = None
        if price_data:
            sorted_dates = sorted(price_data.keys())
            if len(sorted_dates) >= 2:
                first_price = price_data[sorted_dates[0]]
                last_price = price_data[sorted_dates[-1]]
                benchmark_return = (last_price - first_price) / first_price * 100
                alpha = total_return_pct - benchmark_return

        return BacktestResult(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            final_capital=round(final_capital, 2),
            total_return_pct=round(total_return_pct, 2),
            annualized_return_pct=round(annualized_return, 2),
            max_drawdown_pct=round(max_drawdown, 2),
            sharpe_ratio=round(sharpe, 2) if sharpe else None,
            win_rate=round(win_rate, 4),
            total_trades=total_trades,
            winning_trades=win_count,
            losing_trades=loss_count,
            avg_win_pct=round(avg_win, 2),
            avg_loss_pct=round(avg_loss, 2),
            profit_factor=round(profit_factor, 2) if profit_factor else None,
            trades=trades,
            benchmark_return_pct=round(benchmark_return, 2) if benchmark_return else None,
            alpha=round(alpha, 2) if alpha else None,
        )

    def _calculate_max_drawdown(self, capital_history: List[float]) -> float:
        """计算最大回撤"""
        if len(capital_history) < 2:
            return 0

        peak = capital_history[0]
        max_drawdown = 0

        for capital in capital_history:
            if capital > peak:
                peak = capital
            drawdown = (peak - capital) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        return max_drawdown

    def _calculate_sharpe_ratio(self, trades: List[TradeRecord]) -> Optional[float]:
        """计算夏普比率"""
        if len(trades) < 2:
            return None

        returns = [t.return_pct for t in trades if t.return_pct is not None]
        if len(returns) < 2:
            return None

        try:
            avg_return = sum(returns) / len(returns)
            std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5

            if std_return == 0:
                return None

            # 假设每笔交易约 5 天，一年约 50 笔交易
            annualized_return = avg_return * 50
            annualized_std = std_return * (50 ** 0.5)

            sharpe = (annualized_return - self.RISK_FREE_RATE * 100) / annualized_std
            return sharpe
        except:
            return None


# 单例实例
backtest_engine = BacktestEngine()
