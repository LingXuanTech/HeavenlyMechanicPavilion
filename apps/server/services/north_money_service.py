"""北向资金监控服务

提供沪深港通北向资金流向数据，包括：
- 当日资金流向
- 个股北向持仓变化
- 净买入/卖出 TOP 榜单
"""
from datetime import datetime, date as DateType
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import structlog
import akshare as ak
import pandas as pd
from functools import lru_cache
import asyncio

logger = structlog.get_logger(__name__)


# ============ 数据模型 ============

class NorthMoneyFlow(BaseModel):
    """北向资金流向"""
    date: DateType = Field(description="日期")
    sh_connect: float = Field(description="沪股通净流入（亿元）")
    sz_connect: float = Field(description="深股通净流入（亿元）")
    total: float = Field(description="北向资金净流入合计（亿元）")
    sh_buy: Optional[float] = Field(default=None, description="沪股通买入金额")
    sh_sell: Optional[float] = Field(default=None, description="沪股通卖出金额")
    sz_buy: Optional[float] = Field(default=None, description="深股通买入金额")
    sz_sell: Optional[float] = Field(default=None, description="深股通卖出金额")
    market_sentiment: str = Field(description="市场情绪判断")


class StockNorthHolding(BaseModel):
    """个股北向持仓"""
    symbol: str = Field(description="股票代码")
    name: str = Field(description="股票名称")
    holding_shares: int = Field(description="持股数量（股）")
    holding_value: float = Field(description="持股市值（亿元）")
    holding_ratio: float = Field(description="持股占比（%）")
    change_shares: int = Field(description="今日增持股数")
    change_ratio: float = Field(description="增持比例（%）")
    rank: int = Field(description="排名")


class NorthMoneyTopStock(BaseModel):
    """北向资金净买入/卖出 TOP 股票"""
    symbol: str = Field(description="股票代码")
    name: str = Field(description="股票名称")
    net_buy: float = Field(description="净买入金额（亿元）")
    buy_amount: float = Field(description="买入金额（亿元）")
    sell_amount: float = Field(description="卖出金额（亿元）")
    holding_ratio: float = Field(description="持股占比（%）")


class NorthMoneyHistory(BaseModel):
    """北向资金历史数据点"""
    date: DateType
    total: float
    sh_connect: float
    sz_connect: float


class NorthMoneySummary(BaseModel):
    """北向资金概览"""
    today: NorthMoneyFlow
    top_buys: List[NorthMoneyTopStock]
    top_sells: List[NorthMoneyTopStock]
    history_5d: List[NorthMoneyHistory]
    trend: str = Field(description="近期趋势: Inflow / Outflow / Neutral")
    week_total: float = Field(description="本周累计净流入")


# ============ 服务类 ============

class NorthMoneyService:
    """北向资金监控服务"""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = 300  # 5 分钟缓存

    def _is_cache_valid(self, key: str) -> bool:
        """检查缓存是否有效"""
        if key not in self._cache_time:
            return False
        elapsed = (datetime.now() - self._cache_time[key]).total_seconds()
        return elapsed < self._cache_ttl

    def _set_cache(self, key: str, value: Any):
        """设置缓存"""
        self._cache[key] = value
        self._cache_time[key] = datetime.now()

    def _get_cache(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if self._is_cache_valid(key):
            return self._cache.get(key)
        return None

    async def get_north_money_flow(self) -> NorthMoneyFlow:
        """获取当日北向资金流向"""
        cache_key = "north_money_flow"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            # 使用 AkShare 获取北向资金数据
            df = await asyncio.to_thread(ak.stock_hsgt_north_net_flow_in_em)

            if df.empty:
                raise ValueError("No north money data available")

            # 获取最新一行数据
            latest = df.iloc[-1]

            # 计算市场情绪
            total = float(latest.get('北向资金', 0) or latest.get('合计', 0))
            if total > 50:
                sentiment = "Strong Inflow"
            elif total > 0:
                sentiment = "Inflow"
            elif total > -50:
                sentiment = "Outflow"
            else:
                sentiment = "Strong Outflow"

            flow = NorthMoneyFlow(
                date=datetime.now().date(),
                sh_connect=float(latest.get('沪股通', 0) or 0),
                sz_connect=float(latest.get('深股通', 0) or 0),
                total=total,
                market_sentiment=sentiment,
            )

            self._set_cache(cache_key, flow)
            logger.info("Fetched north money flow", total=total, sentiment=sentiment)
            return flow

        except Exception as e:
            logger.error("Failed to fetch north money flow", error=str(e))
            # 返回空数据
            return NorthMoneyFlow(
                date=datetime.now().date(),
                sh_connect=0,
                sz_connect=0,
                total=0,
                market_sentiment="Unknown",
            )

    async def get_north_money_history(self, days: int = 30) -> List[NorthMoneyHistory]:
        """获取北向资金历史数据"""
        cache_key = f"north_money_history_{days}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            df = await asyncio.to_thread(ak.stock_hsgt_north_net_flow_in_em)

            if df.empty:
                return []

            # 取最近 N 天
            df = df.tail(days)

            history = []
            for _, row in df.iterrows():
                try:
                    history.append(NorthMoneyHistory(
                        date=pd.to_datetime(row.get('日期', row.name)).date() if '日期' in row else datetime.now().date(),
                        total=float(row.get('北向资金', 0) or row.get('合计', 0)),
                        sh_connect=float(row.get('沪股通', 0) or 0),
                        sz_connect=float(row.get('深股通', 0) or 0),
                    ))
                except Exception:
                    continue

            self._set_cache(cache_key, history)
            return history

        except Exception as e:
            logger.error("Failed to fetch north money history", error=str(e))
            return []

    async def get_stock_north_holding(self, symbol: str) -> Optional[StockNorthHolding]:
        """获取个股北向持仓变化"""
        try:
            # 提取纯数字代码
            code = symbol.split('.')[0]

            # 获取北向持股数据
            df = await asyncio.to_thread(
                ak.stock_hsgt_hold_stock_em,
                market="北向",
                indicator="今日排行"
            )

            if df.empty:
                return None

            # 查找目标股票
            row = df[df['代码'] == code]
            if row.empty:
                # 尝试模糊匹配
                row = df[df['代码'].str.contains(code)]

            if row.empty:
                logger.debug("Stock not found in north holding", symbol=symbol)
                return None

            row = row.iloc[0]

            return StockNorthHolding(
                symbol=symbol,
                name=str(row.get('名称', '')),
                holding_shares=int(float(row.get('持股数量', 0) or 0)),
                holding_value=float(row.get('持股市值', 0) or 0) / 1e8,  # 转为亿元
                holding_ratio=float(row.get('持股占比', 0) or 0),
                change_shares=int(float(row.get('今日增持股数', 0) or row.get('日增持股数', 0) or 0)),
                change_ratio=float(row.get('今日增持比例', 0) or row.get('日增持比例', 0) or 0),
                rank=int(row.get('排名', 0) or row.name + 1),
            )

        except Exception as e:
            logger.error("Failed to fetch stock north holding", symbol=symbol, error=str(e))
            return None

    async def get_top_north_buys(self, limit: int = 20) -> List[NorthMoneyTopStock]:
        """获取北向资金净买入 TOP"""
        cache_key = f"top_north_buys_{limit}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            df = await asyncio.to_thread(
                ak.stock_hsgt_hold_stock_em,
                market="北向",
                indicator="今日排行"
            )

            if df.empty:
                return []

            # 按净买入排序
            if '净买额' in df.columns:
                df = df.sort_values('净买额', ascending=False)
            elif '今日增持市值' in df.columns:
                df = df.sort_values('今日增持市值', ascending=False)

            df = df.head(limit)

            result = []
            for _, row in df.iterrows():
                try:
                    result.append(NorthMoneyTopStock(
                        symbol=f"{row.get('代码', '')}.SH" if str(row.get('代码', '')).startswith('6') else f"{row.get('代码', '')}.SZ",
                        name=str(row.get('名称', '')),
                        net_buy=float(row.get('净买额', 0) or row.get('今日增持市值', 0) or 0) / 1e8,
                        buy_amount=float(row.get('买入金额', 0) or 0) / 1e8,
                        sell_amount=float(row.get('卖出金额', 0) or 0) / 1e8,
                        holding_ratio=float(row.get('持股占比', 0) or 0),
                    ))
                except Exception:
                    continue

            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            logger.error("Failed to fetch top north buys", error=str(e))
            return []

    async def get_top_north_sells(self, limit: int = 20) -> List[NorthMoneyTopStock]:
        """获取北向资金净卖出 TOP"""
        cache_key = f"top_north_sells_{limit}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            df = await asyncio.to_thread(
                ak.stock_hsgt_hold_stock_em,
                market="北向",
                indicator="今日排行"
            )

            if df.empty:
                return []

            # 按净卖出排序（净买入最小）
            if '净买额' in df.columns:
                df = df.sort_values('净买额', ascending=True)
            elif '今日增持市值' in df.columns:
                df = df.sort_values('今日增持市值', ascending=True)

            df = df.head(limit)

            result = []
            for _, row in df.iterrows():
                try:
                    net_buy = float(row.get('净买额', 0) or row.get('今日增持市值', 0) or 0) / 1e8
                    if net_buy >= 0:
                        continue  # 跳过净买入的

                    result.append(NorthMoneyTopStock(
                        symbol=f"{row.get('代码', '')}.SH" if str(row.get('代码', '')).startswith('6') else f"{row.get('代码', '')}.SZ",
                        name=str(row.get('名称', '')),
                        net_buy=net_buy,
                        buy_amount=float(row.get('买入金额', 0) or 0) / 1e8,
                        sell_amount=float(row.get('卖出金额', 0) or 0) / 1e8,
                        holding_ratio=float(row.get('持股占比', 0) or 0),
                    ))
                except Exception:
                    continue

            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            logger.error("Failed to fetch top north sells", error=str(e))
            return []

    async def get_summary(self) -> NorthMoneySummary:
        """获取北向资金概览"""
        # 并行获取所有数据
        today, history, top_buys, top_sells = await asyncio.gather(
            self.get_north_money_flow(),
            self.get_north_money_history(days=5),
            self.get_top_north_buys(limit=10),
            self.get_top_north_sells(limit=10),
        )

        # 计算本周累计和趋势
        week_total = sum(h.total for h in history[-5:]) if history else 0
        if week_total > 50:
            trend = "Strong Inflow"
        elif week_total > 0:
            trend = "Inflow"
        elif week_total > -50:
            trend = "Outflow"
        else:
            trend = "Strong Outflow"

        return NorthMoneySummary(
            today=today,
            top_buys=top_buys,
            top_sells=top_sells,
            history_5d=history[-5:] if history else [],
            trend=trend,
            week_total=week_total,
        )


# 单例实例
north_money_service = NorthMoneyService()
