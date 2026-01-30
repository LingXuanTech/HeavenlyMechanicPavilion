"""限售解禁监控服务

提供 A 股限售股解禁数据，包括：
- 近期解禁日历
- 个股解禁详情
- 解禁压力评估
- 解禁预警信号
"""

from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import structlog
import akshare as ak
import pandas as pd
import asyncio

logger = structlog.get_logger(__name__)


# ============ 数据模型 ============

class UnlockStock(BaseModel):
    """解禁股票"""
    symbol: str = Field(description="股票代码")
    name: str = Field(description="股票名称")
    unlock_date: date = Field(description="解禁日期")
    unlock_shares: float = Field(description="解禁股数（万股）")
    unlock_value: float = Field(description="解禁市值（亿元）")
    unlock_ratio: float = Field(description="解禁比例（占总股本%）")
    circulating_ratio: float = Field(default=0, description="解禁比例（占流通股%）")
    unlock_type: str = Field(description="解禁类型（首发原股东/定增/股权激励等）")
    current_price: Optional[float] = Field(default=None, description="当前股价")
    cost_price: Optional[float] = Field(default=None, description="解禁成本价")
    profit_ratio: Optional[float] = Field(default=None, description="浮盈比例%")


class UnlockCalendar(BaseModel):
    """解禁日历"""
    date: date = Field(description="日期")
    total_stocks: int = Field(description="解禁股票数量")
    total_value: float = Field(description="解禁市值合计（亿元）")
    stocks: List[UnlockStock] = Field(description="解禁股票列表")


class UnlockPressure(BaseModel):
    """解禁压力评估"""
    symbol: str = Field(description="股票代码")
    name: str = Field(description="股票名称")
    pressure_score: int = Field(description="压力评分 0-100")
    pressure_level: str = Field(description="压力等级: 低/中/高/极高")
    upcoming_unlocks: List[UnlockStock] = Field(description="未来30日解禁计划")
    total_unlock_value: float = Field(description="未来30日解禁市值合计（亿元）")
    total_unlock_ratio: float = Field(description="未来30日解禁占流通比例%")
    risk_factors: List[str] = Field(description="风险因素")
    suggestion: str = Field(description="操作建议")


class MarketUnlockOverview(BaseModel):
    """市场解禁概览"""
    date: date = Field(description="数据日期")
    this_week_value: float = Field(description="本周解禁市值（亿元）")
    next_week_value: float = Field(description="下周解禁市值（亿元）")
    this_month_value: float = Field(description="本月解禁市值（亿元）")
    high_pressure_stocks: List[UnlockStock] = Field(description="高压力解禁股")
    trend: str = Field(description="解禁趋势: 增加/减少/平稳")
    market_impact: str = Field(description="对市场影响评估")


# ============ 服务类 ============

class UnlockService:
    """限售解禁监控服务"""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = 3600  # 1 小时缓存

    def _is_cache_valid(self, key: str) -> bool:
        if key not in self._cache_time:
            return False
        elapsed = (datetime.now() - self._cache_time[key]).total_seconds()
        return elapsed < self._cache_ttl

    def _set_cache(self, key: str, value: Any):
        self._cache[key] = value
        self._cache_time[key] = datetime.now()

    def _get_cache(self, key: str) -> Optional[Any]:
        if self._is_cache_valid(key):
            return self._cache.get(key)
        return None

    async def get_unlock_calendar(self, start_date: date = None, end_date: date = None) -> List[UnlockCalendar]:
        """获取解禁日历

        Args:
            start_date: 开始日期，默认今天
            end_date: 结束日期，默认 30 天后
        """
        if start_date is None:
            start_date = datetime.now().date()
        if end_date is None:
            end_date = start_date + timedelta(days=30)

        cache_key = f"unlock_calendar_{start_date}_{end_date}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            # 获取解禁数据
            df = await asyncio.to_thread(ak.stock_restricted_release_summary_em)

            if df.empty:
                logger.warning("No unlock data available")
                return []

            # 按日期分组
            calendar_data: Dict[date, List[UnlockStock]] = {}

            for _, row in df.iterrows():
                try:
                    unlock_date_str = row.get('解禁日期', row.get('解除限售日期', ''))
                    if not unlock_date_str:
                        continue

                    unlock_date = pd.to_datetime(unlock_date_str).date()

                    # 过滤日期范围
                    if unlock_date < start_date or unlock_date > end_date:
                        continue

                    code = str(row.get('代码', row.get('股票代码', '')))
                    unlock_shares = float(row.get('解禁数量', row.get('解禁股数', 0)) or 0)
                    unlock_value = float(row.get('解禁市值', 0) or 0)

                    # 转换单位
                    if unlock_shares > 1e8:
                        unlock_shares = unlock_shares / 1e4  # 股 -> 万股
                    if unlock_value > 1e12:
                        unlock_value = unlock_value / 1e8  # 元 -> 亿元

                    stock = UnlockStock(
                        symbol=f"{code}.SH" if code.startswith('6') else f"{code}.SZ",
                        name=str(row.get('名称', row.get('股票名称', ''))),
                        unlock_date=unlock_date,
                        unlock_shares=unlock_shares,
                        unlock_value=unlock_value,
                        unlock_ratio=float(row.get('解禁比例', row.get('占总股本比例', 0)) or 0),
                        circulating_ratio=float(row.get('占流通股比例', 0) or 0),
                        unlock_type=str(row.get('限售股类型', row.get('解禁类型', '未知'))),
                    )

                    if unlock_date not in calendar_data:
                        calendar_data[unlock_date] = []
                    calendar_data[unlock_date].append(stock)

                except Exception as e:
                    logger.debug("Failed to parse unlock row", error=str(e))
                    continue

            # 构建日历
            result = []
            for dt in sorted(calendar_data.keys()):
                stocks = calendar_data[dt]
                total_value = sum(s.unlock_value for s in stocks)
                result.append(UnlockCalendar(
                    date=dt,
                    total_stocks=len(stocks),
                    total_value=total_value,
                    stocks=sorted(stocks, key=lambda x: x.unlock_value, reverse=True),
                ))

            self._set_cache(cache_key, result)
            logger.info("Fetched unlock calendar", days=len(result), total_stocks=sum(c.total_stocks for c in result))
            return result

        except Exception as e:
            logger.error("Failed to fetch unlock calendar", error=str(e))
            return []

    async def get_stock_unlock_schedule(self, symbol: str) -> List[UnlockStock]:
        """获取个股解禁计划

        Args:
            symbol: 股票代码
        """
        try:
            code = symbol.split('.')[0]

            # 获取个股解禁数据
            df = await asyncio.to_thread(
                ak.stock_restricted_release_detail_em,
                symbol=code
            )

            if df.empty:
                return []

            result = []
            for _, row in df.iterrows():
                try:
                    unlock_date_str = row.get('解禁日期', '')
                    if not unlock_date_str:
                        continue

                    unlock_date = pd.to_datetime(unlock_date_str).date()

                    # 只返回未来的解禁
                    if unlock_date < datetime.now().date():
                        continue

                    unlock_shares = float(row.get('解禁数量', 0) or 0)
                    if unlock_shares > 1e8:
                        unlock_shares = unlock_shares / 1e4

                    unlock_value = float(row.get('解禁市值', 0) or 0)
                    if unlock_value > 1e12:
                        unlock_value = unlock_value / 1e8

                    result.append(UnlockStock(
                        symbol=symbol,
                        name=str(row.get('股票名称', '')),
                        unlock_date=unlock_date,
                        unlock_shares=unlock_shares,
                        unlock_value=unlock_value,
                        unlock_ratio=float(row.get('占总股本比例', 0) or 0),
                        circulating_ratio=float(row.get('占流通股比例', 0) or 0),
                        unlock_type=str(row.get('限售股类型', '未知')),
                        cost_price=float(row.get('定增价格', row.get('成本价', 0)) or 0) or None,
                    ))
                except Exception:
                    continue

            # 按日期排序
            result.sort(key=lambda x: x.unlock_date)
            return result

        except Exception as e:
            logger.error("Failed to get stock unlock schedule", symbol=symbol, error=str(e))
            return []

    async def get_unlock_pressure(self, symbol: str) -> UnlockPressure:
        """获取个股解禁压力评估

        Args:
            symbol: 股票代码
        """
        try:
            # 获取解禁计划
            unlocks = await self.get_stock_unlock_schedule(symbol)

            # 筛选未来 30 天的解禁
            today = datetime.now().date()
            threshold = today + timedelta(days=30)
            upcoming = [u for u in unlocks if today <= u.unlock_date <= threshold]

            # 计算压力指标
            total_value = sum(u.unlock_value for u in upcoming)
            total_ratio = sum(u.circulating_ratio for u in upcoming)

            # 评分逻辑
            risk_factors = []
            pressure_score = 0

            # 解禁市值因子
            if total_value > 100:
                pressure_score += 40
                risk_factors.append(f"解禁市值巨大（{total_value:.1f}亿元）")
            elif total_value > 50:
                pressure_score += 30
                risk_factors.append(f"解禁市值较大（{total_value:.1f}亿元）")
            elif total_value > 10:
                pressure_score += 20
                risk_factors.append(f"解禁市值中等（{total_value:.1f}亿元）")
            elif total_value > 0:
                pressure_score += 10

            # 流通占比因子
            if total_ratio > 20:
                pressure_score += 30
                risk_factors.append(f"解禁占流通比例高（{total_ratio:.1f}%）")
            elif total_ratio > 10:
                pressure_score += 20
                risk_factors.append(f"解禁占流通比例中等（{total_ratio:.1f}%）")
            elif total_ratio > 5:
                pressure_score += 10

            # 解禁频次因子
            if len(upcoming) >= 3:
                pressure_score += 15
                risk_factors.append(f"30日内多次解禁（{len(upcoming)}次）")
            elif len(upcoming) >= 2:
                pressure_score += 10

            # 检查是否有浮盈较大的解禁
            for u in upcoming:
                if u.profit_ratio and u.profit_ratio > 100:
                    pressure_score += 15
                    risk_factors.append("存在高浮盈解禁（获利超100%）")
                    break

            # 确定压力等级
            if pressure_score >= 70:
                pressure_level = "极高"
                suggestion = "⚠️ 解禁压力极大，建议短期规避，等待解禁落地后再介入"
            elif pressure_score >= 50:
                pressure_level = "高"
                suggestion = "🔶 解禁压力较大，谨慎持仓，注意减仓控制风险"
            elif pressure_score >= 30:
                pressure_level = "中"
                suggestion = "🟡 有一定解禁压力，关注解禁前后的走势变化"
            else:
                pressure_level = "低"
                suggestion = "🟢 解禁压力较小，可正常持有"

            if not upcoming:
                pressure_level = "低"
                pressure_score = 0
                suggestion = "✅ 近30日无解禁计划，解禁压力为零"

            # 获取股票名称
            name = upcoming[0].name if upcoming else symbol

            return UnlockPressure(
                symbol=symbol,
                name=name,
                pressure_score=min(100, pressure_score),
                pressure_level=pressure_level,
                upcoming_unlocks=upcoming,
                total_unlock_value=total_value,
                total_unlock_ratio=total_ratio,
                risk_factors=risk_factors,
                suggestion=suggestion,
            )

        except Exception as e:
            logger.error("Failed to get unlock pressure", symbol=symbol, error=str(e))
            return UnlockPressure(
                symbol=symbol,
                name=symbol,
                pressure_score=0,
                pressure_level="未知",
                upcoming_unlocks=[],
                total_unlock_value=0,
                total_unlock_ratio=0,
                risk_factors=[f"获取数据失败: {str(e)}"],
                suggestion="⚠️ 无法评估解禁压力，请稍后重试",
            )

    async def get_market_unlock_overview(self) -> MarketUnlockOverview:
        """获取市场解禁概览"""
        cache_key = "market_unlock_overview"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            today = datetime.now().date()
            week_end = today + timedelta(days=7)
            next_week_end = today + timedelta(days=14)
            month_end = today + timedelta(days=30)

            # 获取解禁日历
            calendar = await self.get_unlock_calendar(today, month_end)

            # 统计各时段解禁
            this_week_value = 0.0
            next_week_value = 0.0
            this_month_value = 0.0
            high_pressure_stocks = []

            for day in calendar:
                this_month_value += day.total_value
                if day.date <= week_end:
                    this_week_value += day.total_value
                elif day.date <= next_week_end:
                    next_week_value += day.total_value

                # 收集高压力解禁
                for stock in day.stocks:
                    if stock.unlock_value > 10 or stock.unlock_ratio > 5:
                        high_pressure_stocks.append(stock)

            # 排序高压力股票
            high_pressure_stocks.sort(key=lambda x: x.unlock_value, reverse=True)

            # 趋势判断
            if next_week_value > this_week_value * 1.5:
                trend = "增加"
            elif next_week_value < this_week_value * 0.7:
                trend = "减少"
            else:
                trend = "平稳"

            # 市场影响评估
            if this_week_value > 500:
                market_impact = "本周解禁压力巨大，可能对市场形成明显压制，建议控制仓位"
            elif this_week_value > 200:
                market_impact = "本周解禁压力较大，市场可能承压，注意个股风险"
            elif this_week_value > 100:
                market_impact = "本周解禁压力中等，对大盘影响有限，关注个股解禁情况"
            else:
                market_impact = "本周解禁压力较小，对市场影响较弱"

            overview = MarketUnlockOverview(
                date=today,
                this_week_value=this_week_value,
                next_week_value=next_week_value,
                this_month_value=this_month_value,
                high_pressure_stocks=high_pressure_stocks[:20],
                trend=trend,
                market_impact=market_impact,
            )

            self._set_cache(cache_key, overview)
            logger.info(
                "Market unlock overview fetched",
                this_week=f"{this_week_value:.1f}亿",
                this_month=f"{this_month_value:.1f}亿",
            )
            return overview

        except Exception as e:
            logger.error("Failed to get market unlock overview", error=str(e))
            return MarketUnlockOverview(
                date=datetime.now().date(),
                this_week_value=0,
                next_week_value=0,
                this_month_value=0,
                high_pressure_stocks=[],
                trend="未知",
                market_impact=f"获取数据失败: {str(e)}",
            )

    async def get_high_pressure_stocks(self, limit: int = 20) -> List[UnlockPressure]:
        """获取高解禁压力股票列表

        Args:
            limit: 返回数量
        """
        try:
            # 获取本周解禁概览
            overview = await self.get_market_unlock_overview()

            # 为每只高压力股票计算详细压力
            pressure_list = []
            for stock in overview.high_pressure_stocks[:limit * 2]:
                pressure = await self.get_unlock_pressure(stock.symbol)
                if pressure.pressure_score >= 30:  # 只返回中等以上压力
                    pressure_list.append(pressure)

            # 按压力评分排序
            pressure_list.sort(key=lambda x: x.pressure_score, reverse=True)
            return pressure_list[:limit]

        except Exception as e:
            logger.error("Failed to get high pressure stocks", error=str(e))
            return []


# 单例实例
unlock_service = UnlockService()
