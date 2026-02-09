"""机构级风控建模服务

提供蒙特卡洛 VaR/CVaR 计算、压力测试和综合风险指标。
使用 numpy 进行数值计算，yfinance/akshare 获取历史数据。
"""

import numpy as np
import structlog
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from services.data_router import MarketRouter

logger = structlog.get_logger()

# 压力测试预设场景
STRESS_SCENARIOS = {
    "financial_crisis_2008": {
        "name": "2008 金融危机",
        "description": "全球金融危机，信贷紧缩，系统性风险爆发",
        "shocks": {
            "default": -0.45,
            "金融": -0.60,
            "银行": -0.55,
            "消费": -0.30,
            "科技": -0.40,
            "医药": -0.20,
            "能源": -0.50,
        },
    },
    "covid_2020": {
        "name": "2020 疫情冲击",
        "description": "新冠疫情全球蔓延，经济停摆",
        "shocks": {
            "default": -0.25,
            "航空": -0.50,
            "旅游": -0.50,
            "餐饮": -0.40,
            "医药": 0.20,
            "科技": -0.10,
            "消费": -0.15,
        },
    },
    "rate_hike": {
        "name": "利率骤升 200bp",
        "description": "央行大幅加息，流动性收紧",
        "shocks": {
            "default": -0.15,
            "地产": -0.30,
            "银行": 0.05,
            "科技": -0.20,
            "消费": -0.10,
            "公用事业": -0.05,
        },
    },
    "trade_war": {
        "name": "中美贸易战",
        "description": "贸易摩擦升级，关税壁垒提高",
        "shocks": {
            "default": -0.20,
            "科技": -0.35,
            "半导体": -0.40,
            "消费": -0.10,
            "农业": -0.15,
            "军工": 0.05,
        },
    },
}


class RiskModelingService:
    """风控建模服务"""

    async def calculate_var(
        self,
        symbols: List[str],
        weights: Optional[List[float]] = None,
        confidence: float = 0.95,
        days: int = 1,
        simulations: int = 10000,
        lookback_days: int = 252,
    ) -> Dict[str, Any]:
        """蒙特卡洛 VaR/CVaR 计算

        Args:
            symbols: 股票代码列表
            weights: 权重列表（默认等权）
            confidence: 置信水平（默认 95%）
            days: 持有期（天）
            simulations: 模拟次数
            lookback_days: 历史回看天数

        Returns:
            VaR/CVaR 计算结果 + 模拟分布直方图数据
        """
        n_assets = len(symbols)
        if weights is None:
            weights = [1.0 / n_assets] * n_assets
        weights = np.array(weights)

        # 获取历史收益率
        returns_matrix = await self._get_returns_matrix(symbols, lookback_days)

        if returns_matrix is None or returns_matrix.shape[0] < 30:
            return {
                "error": "历史数据不足，至少需要 30 个交易日",
                "symbols": symbols,
            }

        # 计算协方差矩阵（年化）
        cov_matrix = np.cov(returns_matrix, rowvar=False) * 252

        # Cholesky 分解
        try:
            L = np.linalg.cholesky(cov_matrix)
        except np.linalg.LinAlgError:
            # 协方差矩阵非正定，添加微小扰动
            cov_matrix += np.eye(n_assets) * 1e-8
            L = np.linalg.cholesky(cov_matrix)

        # 蒙特卡洛模拟
        mean_returns = returns_matrix.mean(axis=0) * days
        random_normals = np.random.normal(size=(n_assets, simulations))
        simulated_returns = mean_returns.reshape(-1, 1) + np.sqrt(days) * np.dot(L, random_normals)
        portfolio_returns = np.dot(weights, simulated_returns)

        # 计算 VaR 和 CVaR
        var_percentile = (1 - confidence) * 100
        var_value = float(np.percentile(portfolio_returns, var_percentile))
        cvar_value = float(portfolio_returns[portfolio_returns <= var_value].mean()) if np.any(portfolio_returns <= var_value) else var_value

        # 生成直方图数据（50 个桶）
        hist_counts, hist_edges = np.histogram(portfolio_returns, bins=50)
        histogram = [
            {
                "bin_start": round(float(hist_edges[i]), 6),
                "bin_end": round(float(hist_edges[i + 1]), 6),
                "count": int(hist_counts[i]),
                "bin_center": round(float((hist_edges[i] + hist_edges[i + 1]) / 2), 6),
            }
            for i in range(len(hist_counts))
        ]

        return {
            "symbols": symbols,
            "weights": weights.tolist(),
            "confidence": confidence,
            "holding_days": days,
            "simulations": simulations,
            "var": round(var_value * 100, 4),  # 百分比
            "cvar": round(cvar_value * 100, 4),
            "var_interpretation": f"在 {confidence*100:.0f}% 置信水平下，{days} 天内最大预期损失为 {abs(var_value)*100:.2f}%",
            "cvar_interpretation": f"当损失超过 VaR 时，平均损失为 {abs(cvar_value)*100:.2f}%",
            "histogram": histogram,
            "stats": {
                "mean_return": round(float(portfolio_returns.mean()) * 100, 4),
                "std_return": round(float(portfolio_returns.std()) * 100, 4),
                "min_return": round(float(portfolio_returns.min()) * 100, 4),
                "max_return": round(float(portfolio_returns.max()) * 100, 4),
            },
        }

    async def run_stress_test(
        self,
        symbols: List[str],
        weights: Optional[List[float]] = None,
        scenario: Optional[str] = None,
    ) -> Dict[str, Any]:
        """压力测试

        Args:
            symbols: 股票代码列表
            weights: 权重列表
            scenario: 指定场景 ID（为空则运行所有场景）

        Returns:
            压力测试结果
        """
        n_assets = len(symbols)
        if weights is None:
            weights = [1.0 / n_assets] * n_assets
        weights = np.array(weights)

        scenarios_to_run = {}
        if scenario and scenario in STRESS_SCENARIOS:
            scenarios_to_run[scenario] = STRESS_SCENARIOS[scenario]
        else:
            scenarios_to_run = STRESS_SCENARIOS

        results = []
        for scenario_id, scenario_data in scenarios_to_run.items():
            shocks = scenario_data["shocks"]

            # 为每只股票分配冲击幅度（基于行业匹配或默认值）
            asset_shocks = []
            for sym in symbols:
                market = MarketRouter.get_market(sym)
                # 简化：使用默认冲击值
                shock = shocks.get("default", -0.20)
                asset_shocks.append(shock)

            asset_shocks = np.array(asset_shocks)
            portfolio_loss = float(np.dot(weights, asset_shocks))

            results.append({
                "scenario_id": scenario_id,
                "name": scenario_data["name"],
                "description": scenario_data["description"],
                "asset_impacts": [
                    {"symbol": sym, "shock": round(s * 100, 2)}
                    for sym, s in zip(symbols, asset_shocks)
                ],
                "portfolio_loss": round(portfolio_loss * 100, 2),
                "portfolio_loss_interpretation": f"组合预期损失 {abs(portfolio_loss)*100:.1f}%",
            })

        return {
            "symbols": symbols,
            "weights": weights.tolist(),
            "scenarios": results,
        }

    async def get_risk_metrics(
        self,
        symbols: List[str],
        weights: Optional[List[float]] = None,
        lookback_days: int = 252,
    ) -> Dict[str, Any]:
        """综合风险指标

        Args:
            symbols: 股票代码列表
            weights: 权重列表
            lookback_days: 历史回看天数

        Returns:
            波动率、夏普比率、最大回撤、Beta 等指标
        """
        n_assets = len(symbols)
        if weights is None:
            weights = [1.0 / n_assets] * n_assets
        weights = np.array(weights)

        returns_matrix = await self._get_returns_matrix(symbols, lookback_days)

        if returns_matrix is None or returns_matrix.shape[0] < 30:
            return {
                "error": "历史数据不足",
                "symbols": symbols,
            }

        # 组合收益率
        portfolio_returns = np.dot(returns_matrix, weights)

        # 年化波动率
        volatility = float(np.std(portfolio_returns) * np.sqrt(252))

        # 年化收益率
        annual_return = float(np.mean(portfolio_returns) * 252)

        # 夏普比率（假设无风险利率 2%）
        risk_free_rate = 0.02
        sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0

        # 最大回撤
        cumulative = np.cumprod(1 + portfolio_returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max
        max_drawdown = float(np.min(drawdowns))

        # Beta（相对于等权基准）
        market_returns = np.mean(returns_matrix, axis=1)  # 简化：用等权平均作为市场
        if np.var(market_returns) > 0:
            beta = float(np.cov(portfolio_returns, market_returns)[0, 1] / np.var(market_returns))
        else:
            beta = 1.0

        # 个股相关性矩阵
        if n_assets > 1:
            corr_matrix = np.corrcoef(returns_matrix, rowvar=False)
            avg_correlation = float(
                (corr_matrix.sum() - n_assets) / (n_assets * (n_assets - 1))
            ) if n_assets > 1 else 0
        else:
            avg_correlation = 1.0

        # Sortino 比率（仅考虑下行波动）
        downside_returns = portfolio_returns[portfolio_returns < 0]
        downside_std = float(np.std(downside_returns) * np.sqrt(252)) if len(downside_returns) > 0 else volatility
        sortino_ratio = (annual_return - risk_free_rate) / downside_std if downside_std > 0 else 0

        return {
            "symbols": symbols,
            "weights": weights.tolist(),
            "lookback_days": lookback_days,
            "metrics": {
                "annual_return": round(annual_return * 100, 2),
                "volatility": round(volatility * 100, 2),
                "sharpe_ratio": round(sharpe_ratio, 3),
                "sortino_ratio": round(sortino_ratio, 3),
                "max_drawdown": round(max_drawdown * 100, 2),
                "beta": round(beta, 3),
                "avg_correlation": round(avg_correlation, 3),
            },
            "interpretation": {
                "volatility": f"年化波动率 {volatility*100:.1f}%，{'高风险' if volatility > 0.3 else '中等风险' if volatility > 0.15 else '低风险'}",
                "sharpe": f"夏普比率 {sharpe_ratio:.2f}，{'优秀' if sharpe_ratio > 1.5 else '良好' if sharpe_ratio > 1 else '一般' if sharpe_ratio > 0.5 else '较差'}",
                "drawdown": f"最大回撤 {abs(max_drawdown)*100:.1f}%",
                "diversification": f"平均相关性 {avg_correlation:.2f}，{'分散化不足' if avg_correlation > 0.7 else '分散化良好' if avg_correlation < 0.4 else '分散化一般'}",
            },
        }

    async def _get_returns_matrix(
        self, symbols: List[str], lookback_days: int
    ) -> Optional[np.ndarray]:
        """获取多只股票的历史收益率矩阵

        Returns:
            shape (T, N) 的收益率矩阵，T=交易日数，N=股票数
        """
        import yfinance as yf
        import pandas as pd

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=int(lookback_days * 1.5))  # 多取一些以应对非交易日

            all_returns = []
            min_length = None

            for symbol in symbols:
                try:
                    # 尝试 yfinance
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(start=start_date, end=end_date)

                    if hist is None or hist.empty or len(hist) < 30:
                        logger.warning("Insufficient data for symbol", symbol=symbol, rows=len(hist) if hist is not None else 0)
                        return None

                    returns = hist["Close"].pct_change().dropna().values
                    all_returns.append(returns)

                    if min_length is None or len(returns) < min_length:
                        min_length = len(returns)

                except Exception as e:
                    logger.warning("Failed to get data for symbol", symbol=symbol, error=str(e))
                    return None

            if not all_returns or min_length is None or min_length < 30:
                return None

            # 对齐长度（取最短的）
            aligned = np.column_stack([r[-min_length:] for r in all_returns])
            return aligned

        except Exception as e:
            logger.error("Failed to build returns matrix", error=str(e))
            return None


# 全局单例
risk_modeling_service = RiskModelingService()
