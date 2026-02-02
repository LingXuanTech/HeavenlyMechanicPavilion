"""限售解禁预警服务

提供 A 股限售股解禁数据，包括：
- 近期解禁日历
- 个股解禁计划
- 解禁市值统计
- 解禁压力评估
"""
from datetime import datetime, date as DateType, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import structlog
import akshare as ak
import pandas as pd
import asyncio

from utils import TTLCache

logger = structlog.get_logger(__name__)


# ============ 数据模型 ============

class JiejinStock(BaseModel):
    """解禁股票"""
    symbol: str = Field(description="股票代码")
    name: str = Field(description="股票名称")
    jiejin_date: DateType = Field(description="解禁日期")
    jiejin_shares: float = Field(description="解禁数量（万股）")
    jiejin_market_value: float = Field(description="解禁市值（亿元）")
    jiejin_ratio: float = Field(description="解禁比例（占流通股%）")
    jiejin_type: str = Field(description="解禁类型")
    current_price: Optional[float] = Field(default=None, description="当前价格")
    total_market_value: Optional[float] = Field(default=None, description="总市值（亿元）")
    pressure_level: str = Field(description="解禁压力等级: 高/中/低")


class JiejinCalendar(BaseModel):
    """解禁日历条目"""
    date: DateType = Field(description="日期")
    stock_count: int = Field(description="解禁股票数量")
    total_shares: float = Field(description="解禁总股数（亿股）")
    total_market_value: float = Field(description="解禁总市值（亿元）")
    stocks: List[JiejinStock] = Field(description="当日解禁股票列表")


class StockJiejinPlan(BaseModel):
    """个股解禁计划"""
    symbol: str
    name: str
    upcoming_jiejin: List[JiejinStock] = Field(description="未来解禁计划")
    past_jiejin: List[JiejinStock] = Field(description="历史解禁记录")
    total_locked_shares: float = Field(description="当前限售股总量（万股）")
    total_locked_ratio: float = Field(description="限售股占比（%）")


class JiejinSummary(BaseModel):
    """解禁概览"""
    date_range: str = Field(description="统计日期范围")
    total_stocks: int = Field(description="涉及股票数")
    total_market_value: float = Field(description="总解禁市值（亿元）")
    daily_average: float = Field(description="日均解禁市值（亿元）")
    high_pressure_stocks: List[JiejinStock] = Field(description="高解禁压力股票")
    calendar: List[JiejinCalendar] = Field(description="解禁日历")


# ============ 服务类 ============

class JiejinService:
    """限售解禁预警服务"""

    def __init__(self):
        self._cache = TTLCache(default_ttl=3600)  # 1 小时缓存（解禁数据变化不频繁）

    def _evaluate_pressure(self, jiejin_ratio: float, jiejin_market_value: float) -> str:
        """评估解禁压力等级

        基于解禁比例和解禁市值综合评估
        """
        # 高压力：解禁比例 > 10% 或 解禁市值 > 50 亿
        if jiejin_ratio > 10 or jiejin_market_value > 50:
            return "高"
        # 中压力：解禁比例 > 5% 或 解禁市值 > 10 亿
        if jiejin_ratio > 5 or jiejin_market_value > 10:
            return "中"
        return "低"

    async def get_upcoming_jiejin(self, days: int = 30) -> List[JiejinStock]:
        """获取近期解禁股票

        Args:
            days: 查询未来天数，默认 30 天
        """
        cache_key = f"upcoming_jiejin_{days}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        try:
            # 使用 akshare 获取解禁数据
            df = await asyncio.to_thread(ak.stock_restricted_release_queue_sina)

            if df.empty:
                logger.warning("No jiejin data available")
                return []

            result = []
            today = DateType.today()
            end_date = today + timedelta(days=days)

            for _, row in df.iterrows():
                try:
                    # 解析日期
                    jiejin_date_str = str(row.get('解禁日期', row.get('上市日期', '')))
                    if not jiejin_date_str:
                        continue

                    jiejin_date = pd.to_datetime(jiejin_date_str).date()

                    # 筛选日期范围
                    if jiejin_date < today or jiejin_date > end_date:
                        continue

                    # 解析数值
                    code = str(row.get('股票代码', row.get('代码', '')))
                    jiejin_shares = float(row.get('解禁数量', row.get('解禁股数', 0)) or 0)
                    jiejin_market_value = float(row.get('解禁市值', 0) or 0) / 10000  # 转为亿元
                    jiejin_ratio = float(row.get('解禁比例', row.get('占总股本比例', 0)) or 0)

                    # 确保股票代码格式正确
                    if len(code) == 6:
                        symbol = f"{code}.SH" if code.startswith('6') else f"{code}.SZ"
                    else:
                        symbol = code

                    pressure = self._evaluate_pressure(jiejin_ratio, jiejin_market_value)

                    stock = JiejinStock(
                        symbol=symbol,
                        name=str(row.get('股票简称', row.get('名称', ''))),
                        jiejin_date=jiejin_date,
                        jiejin_shares=jiejin_shares,
                        jiejin_market_value=jiejin_market_value,
                        jiejin_ratio=jiejin_ratio,
                        jiejin_type=str(row.get('限售股类型', row.get('解禁类型', '定增解禁'))),
                        pressure_level=pressure,
                    )
                    result.append(stock)

                except Exception as e:
                    logger.debug("Failed to parse jiejin row", error=str(e))
                    continue

            # 按日期排序
            result.sort(key=lambda x: x.jiejin_date)

            self._cache.set(cache_key, result)
            logger.info("Upcoming jiejin fetched", count=len(result), days=days)
            return result

        except Exception as e:
            logger.error("Failed to fetch upcoming jiejin", error=str(e))
            return []

    async def get_jiejin_calendar(self, days: int = 30) -> List[JiejinCalendar]:
        """获取解禁日历

        按日期聚合解禁数据
        """
        stocks = await self.get_upcoming_jiejin(days)

        if not stocks:
            return []

        # 按日期分组
        date_groups: Dict[date, List[JiejinStock]] = {}
        for stock in stocks:
            if stock.jiejin_date not in date_groups:
                date_groups[stock.jiejin_date] = []
            date_groups[stock.jiejin_date].append(stock)

        result = []
        for d, group in sorted(date_groups.items()):
            total_shares = sum(s.jiejin_shares for s in group) / 10000  # 转为亿股
            total_value = sum(s.jiejin_market_value for s in group)

            result.append(JiejinCalendar(
                date=d,
                stock_count=len(group),
                total_shares=total_shares,
                total_market_value=total_value,
                stocks=group,
            ))

        return result

    async def get_stock_jiejin_plan(self, symbol: str) -> Optional[StockJiejinPlan]:
        """获取个股解禁计划

        Args:
            symbol: 股票代码
        """
        cache_key = f"stock_jiejin_{symbol}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        try:
            code = symbol.split('.')[0]

            # 获取该股票的解禁数据
            df = await asyncio.to_thread(
                ak.stock_restricted_release_detail_em,
                symbol=code
            )

            if df.empty:
                return None

            today = DateType.today()
            upcoming = []
            past = []

            for _, row in df.iterrows():
                try:
                    jiejin_date = pd.to_datetime(row.get('解禁日期', '')).date()
                    jiejin_shares = float(row.get('解禁数量', 0) or 0)
                    jiejin_market_value = float(row.get('解禁市值', 0) or 0) / 10000
                    jiejin_ratio = float(row.get('占总股本比例', 0) or 0)

                    stock = JiejinStock(
                        symbol=symbol,
                        name=str(row.get('股票简称', '')),
                        jiejin_date=jiejin_date,
                        jiejin_shares=jiejin_shares,
                        jiejin_market_value=jiejin_market_value,
                        jiejin_ratio=jiejin_ratio,
                        jiejin_type=str(row.get('限售股类型', '定增解禁')),
                        pressure_level=self._evaluate_pressure(jiejin_ratio, jiejin_market_value),
                    )

                    if jiejin_date >= today:
                        upcoming.append(stock)
                    else:
                        past.append(stock)

                except Exception:
                    continue

            # 排序
            upcoming.sort(key=lambda x: x.jiejin_date)
            past.sort(key=lambda x: x.jiejin_date, reverse=True)

            # 计算限售股总量
            total_locked = sum(s.jiejin_shares for s in upcoming)
            total_locked_ratio = sum(s.jiejin_ratio for s in upcoming)

            result = StockJiejinPlan(
                symbol=symbol,
                name=upcoming[0].name if upcoming else (past[0].name if past else ""),
                upcoming_jiejin=upcoming,
                past_jiejin=past[:10],  # 只保留最近 10 条历史
                total_locked_shares=total_locked,
                total_locked_ratio=total_locked_ratio,
            )

            self._cache.set(cache_key, result)
            return result

        except Exception as e:
            logger.error("Failed to fetch stock jiejin plan", symbol=symbol, error=str(e))
            return None

    async def get_high_pressure_stocks(self, days: int = 7) -> List[JiejinStock]:
        """获取高解禁压力股票

        Args:
            days: 查询未来天数
        """
        stocks = await self.get_upcoming_jiejin(days)
        return [s for s in stocks if s.pressure_level == "高"]

    async def get_summary(self, days: int = 30) -> JiejinSummary:
        """获取解禁概览"""
        stocks = await self.get_upcoming_jiejin(days)
        calendar = await self.get_jiejin_calendar(days)

        total_value = sum(s.jiejin_market_value for s in stocks)
        high_pressure = [s for s in stocks if s.pressure_level == "高"]

        # 按解禁市值排序高压力股票
        high_pressure.sort(key=lambda x: x.jiejin_market_value, reverse=True)

        today = DateType.today()
        end_date = today + timedelta(days=days)

        return JiejinSummary(
            date_range=f"{today.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}",
            total_stocks=len(set(s.symbol for s in stocks)),
            total_market_value=total_value,
            daily_average=total_value / days if days > 0 else 0,
            high_pressure_stocks=high_pressure[:20],  # 前 20 个高压力股票
            calendar=calendar,
        )

    async def check_stock_jiejin_warning(self, symbol: str, days: int = 30) -> Optional[dict]:
        """检查个股解禁预警

        Args:
            symbol: 股票代码
            days: 预警时间窗口

        Returns:
            预警信息，无预警则返回 None
        """
        plan = await self.get_stock_jiejin_plan(symbol)

        if not plan or not plan.upcoming_jiejin:
            return None

        today = DateType.today()
        warning_date = today + timedelta(days=days)

        # 筛选预警时间窗口内的解禁
        warnings = [
            j for j in plan.upcoming_jiejin
            if j.jiejin_date <= warning_date
        ]

        if not warnings:
            return None

        # 计算总解禁压力
        total_value = sum(w.jiejin_market_value for w in warnings)
        total_ratio = sum(w.jiejin_ratio for w in warnings)

        # 确定预警级别
        if total_ratio > 20 or total_value > 100:
            level = "严重"
        elif total_ratio > 10 or total_value > 50:
            level = "警告"
        else:
            level = "提示"

        return {
            "symbol": symbol,
            "name": plan.name,
            "warning_level": level,
            "total_jiejin_value": total_value,
            "total_jiejin_ratio": total_ratio,
            "jiejin_count": len(warnings),
            "nearest_jiejin": warnings[0].model_dump() if warnings else None,
            "message": f"未来 {days} 天内有 {len(warnings)} 次解禁，"
                       f"合计 {total_value:.2f} 亿元，占流通股 {total_ratio:.2f}%"
        }


# 单例实例
jiejin_service = JiejinService()
