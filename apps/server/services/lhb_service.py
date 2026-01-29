"""龙虎榜解析服务

提供 A 股龙虎榜数据，包括：
- 每日龙虎榜
- 个股龙虎榜历史
- 机构/游资席位识别
- 知名游资动向追踪
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

class LHBSeat(BaseModel):
    """龙虎榜席位"""
    seat_name: str = Field(description="营业部名称")
    buy_amount: float = Field(description="买入金额（万元）")
    sell_amount: float = Field(description="卖出金额（万元）")
    net_amount: float = Field(description="净买入金额（万元）")
    seat_type: str = Field(description="席位类型: 机构/游资/普通")
    hot_money_name: Optional[str] = Field(default=None, description="知名游资名称（如有）")


class LHBStock(BaseModel):
    """龙虎榜个股"""
    symbol: str = Field(description="股票代码")
    name: str = Field(description="股票名称")
    close_price: float = Field(description="收盘价")
    change_percent: float = Field(description="涨跌幅（%）")
    turnover_rate: float = Field(description="换手率（%）")
    lhb_net_buy: float = Field(description="龙虎榜净买入（万元）")
    lhb_buy_amount: float = Field(description="龙虎榜买入总额（万元）")
    lhb_sell_amount: float = Field(description="龙虎榜卖出总额（万元）")
    reason: str = Field(description="上榜原因")
    buy_seats: List[LHBSeat] = Field(description="买入席位")
    sell_seats: List[LHBSeat] = Field(description="卖出席位")
    institution_net: float = Field(description="机构净买入（万元）")
    hot_money_involved: bool = Field(description="是否有知名游资参与")


class LHBRecord(BaseModel):
    """个股龙虎榜历史记录"""
    date: date
    reason: str
    net_buy: float
    buy_amount: float
    sell_amount: float
    institution_net: float


class HotMoneySeat(BaseModel):
    """知名游资席位"""
    seat_name: str = Field(description="营业部名称")
    alias: str = Field(description="游资别名")
    style: str = Field(description="操作风格")
    recent_stocks: List[dict] = Field(description="近期操作股票")
    win_rate: Optional[float] = Field(default=None, description="历史胜率")


class LHBSummary(BaseModel):
    """龙虎榜概览"""
    date: date
    total_stocks: int = Field(description="上榜股票数")
    total_net_buy: float = Field(description="全市场龙虎榜净买入（亿元）")
    institution_net_buy: float = Field(description="机构净买入（亿元）")
    top_buys: List[LHBStock] = Field(description="净买入 TOP")
    top_sells: List[LHBStock] = Field(description="净卖出 TOP")
    hot_money_active: List[HotMoneySeat] = Field(description="活跃知名游资")


# ============ 知名游资席位库 ============

# 知名游资席位映射（实际应用中应该从数据库加载）
HOT_MONEY_SEATS = {
    # 一线游资
    "华鑫证券上海分公司": {"alias": "溧阳路", "style": "打板/接力"},
    "中国银河证券绍兴证券营业部": {"alias": "赵老哥", "style": "打板/龙头"},
    "国泰君安上海江苏路": {"alias": "章盟主", "style": "趋势/波段"},
    "东方财富证券拉萨团结路第二": {"alias": "拉萨天团", "style": "打板/接力"},
    "东方财富证券拉萨东环路第二": {"alias": "拉萨天团", "style": "打板/接力"},
    "华泰证券深圳益田路荣超商务中心": {"alias": "深圳帮", "style": "趋势/题材"},
    "中信证券上海溧阳路": {"alias": "顶级游资", "style": "大资金/趋势"},

    # 二线游资
    "财通证券杭州上塘路": {"alias": "杭州帮", "style": "题材/接力"},
    "国盛证券宁波桑田路": {"alias": "宁波桑田路", "style": "打板/短线"},
    "华泰证券成都蜀金路": {"alias": "成都帮", "style": "题材/波段"},
    "西藏东方财富证券拉萨团结路第一": {"alias": "拉萨天团", "style": "打板/接力"},

    # 机构专用席位标识
    "机构专用": {"alias": "机构", "style": "机构"},
}


# ============ 服务类 ============

class LHBService:
    """龙虎榜解析服务"""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = 600  # 10 分钟缓存

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

    def _identify_seat_type(self, seat_name: str) -> tuple:
        """识别席位类型和游资信息"""
        if "机构专用" in seat_name:
            return "机构", "机构", None

        for pattern, info in HOT_MONEY_SEATS.items():
            if pattern in seat_name:
                return "游资", info["style"], info["alias"]

        return "普通", "未知", None

    def _parse_seat_data(self, seat_name: str, buy: float, sell: float) -> LHBSeat:
        """解析席位数据"""
        seat_type, style, hot_money = self._identify_seat_type(seat_name)
        return LHBSeat(
            seat_name=seat_name,
            buy_amount=buy,
            sell_amount=sell,
            net_amount=buy - sell,
            seat_type=seat_type,
            hot_money_name=hot_money,
        )

    async def get_daily_lhb(self, trade_date: str = None) -> List[LHBStock]:
        """获取每日龙虎榜

        Args:
            trade_date: 交易日期，格式 YYYYMMDD，默认最近交易日
        """
        cache_key = f"daily_lhb_{trade_date or 'latest'}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            # 获取龙虎榜汇总数据
            if trade_date:
                df = await asyncio.to_thread(
                    ak.stock_lhb_detail_em,
                    start_date=trade_date,
                    end_date=trade_date
                )
            else:
                # 获取最近的龙虎榜
                df = await asyncio.to_thread(ak.stock_lhb_detail_em)

            if df.empty:
                logger.warning("No LHB data available", trade_date=trade_date)
                return []

            result = []
            # 按股票代码分组
            grouped = df.groupby('代码') if '代码' in df.columns else df.groupby(df.columns[0])

            for code, group in grouped:
                try:
                    first_row = group.iloc[0]

                    # 解析买入席位
                    buy_seats = []
                    sell_seats = []

                    # 尝试解析席位数据（不同 API 返回格式可能不同）
                    for _, row in group.iterrows():
                        if '买入营业部' in row or '营业部名称' in row:
                            seat_name = str(row.get('买入营业部', row.get('营业部名称', '')))
                            buy_amt = float(row.get('买入金额', 0) or 0)
                            sell_amt = float(row.get('卖出金额', 0) or 0)

                            if buy_amt > 0:
                                buy_seats.append(self._parse_seat_data(seat_name, buy_amt, sell_amt))
                            if sell_amt > 0:
                                sell_seats.append(self._parse_seat_data(seat_name, buy_amt, sell_amt))

                    # 计算机构净买入
                    inst_buy = sum(s.buy_amount for s in buy_seats if s.seat_type == "机构")
                    inst_sell = sum(s.sell_amount for s in sell_seats if s.seat_type == "机构")

                    # 检查是否有知名游资
                    hot_money = any(s.hot_money_name for s in buy_seats + sell_seats)

                    total_buy = sum(s.buy_amount for s in buy_seats)
                    total_sell = sum(s.sell_amount for s in sell_seats)

                    stock = LHBStock(
                        symbol=f"{code}.SH" if str(code).startswith('6') else f"{code}.SZ",
                        name=str(first_row.get('名称', first_row.get('股票名称', ''))),
                        close_price=float(first_row.get('收盘价', 0) or 0),
                        change_percent=float(first_row.get('涨跌幅', 0) or 0),
                        turnover_rate=float(first_row.get('换手率', 0) or 0),
                        lhb_net_buy=total_buy - total_sell,
                        lhb_buy_amount=total_buy,
                        lhb_sell_amount=total_sell,
                        reason=str(first_row.get('上榜原因', first_row.get('解读', '未知'))),
                        buy_seats=buy_seats[:5],  # 只保留前 5 个
                        sell_seats=sell_seats[:5],
                        institution_net=inst_buy - inst_sell,
                        hot_money_involved=hot_money,
                    )
                    result.append(stock)
                except Exception as e:
                    logger.debug("Failed to parse LHB stock", code=code, error=str(e))
                    continue

            # 按净买入排序
            result.sort(key=lambda x: x.lhb_net_buy, reverse=True)

            self._set_cache(cache_key, result)
            logger.info("Fetched daily LHB", count=len(result), date=trade_date)
            return result

        except Exception as e:
            logger.error("Failed to fetch daily LHB", error=str(e))
            return []

    async def get_stock_lhb_history(self, symbol: str, days: int = 30) -> List[LHBRecord]:
        """获取个股龙虎榜历史"""
        cache_key = f"stock_lhb_{symbol}_{days}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            code = symbol.split('.')[0]
            df = await asyncio.to_thread(ak.stock_lhb_stock_statistic_em, symbol=code)

            if df.empty:
                return []

            result = []
            for _, row in df.head(days).iterrows():
                try:
                    result.append(LHBRecord(
                        date=pd.to_datetime(row.get('上榜日期', row.get('日期', datetime.now()))).date(),
                        reason=str(row.get('上榜原因', '未知')),
                        net_buy=float(row.get('龙虎榜净买额', 0) or 0),
                        buy_amount=float(row.get('龙虎榜买入额', 0) or 0),
                        sell_amount=float(row.get('龙虎榜卖出额', 0) or 0),
                        institution_net=float(row.get('机构净买额', 0) or 0),
                    ))
                except Exception:
                    continue

            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            logger.error("Failed to fetch stock LHB history", symbol=symbol, error=str(e))
            return []

    async def get_hot_money_activity(self, days: int = 5) -> List[HotMoneySeat]:
        """获取知名游资近期活动"""
        cache_key = f"hot_money_{days}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            # 获取近期龙虎榜数据
            daily_lhb = await self.get_daily_lhb()

            # 统计游资活动
            hot_money_activity: Dict[str, List[dict]] = {}

            for stock in daily_lhb:
                for seat in stock.buy_seats + stock.sell_seats:
                    if seat.hot_money_name:
                        if seat.hot_money_name not in hot_money_activity:
                            hot_money_activity[seat.hot_money_name] = []
                        hot_money_activity[seat.hot_money_name].append({
                            "symbol": stock.symbol,
                            "name": stock.name,
                            "action": "买入" if seat.net_amount > 0 else "卖出",
                            "amount": abs(seat.net_amount),
                        })

            result = []
            for alias, stocks in hot_money_activity.items():
                # 查找席位信息
                seat_info = next(
                    (v for k, v in HOT_MONEY_SEATS.items() if v.get("alias") == alias),
                    {"alias": alias, "style": "未知"}
                )
                seat_name = next(
                    (k for k, v in HOT_MONEY_SEATS.items() if v.get("alias") == alias),
                    alias
                )

                result.append(HotMoneySeat(
                    seat_name=seat_name,
                    alias=alias,
                    style=seat_info.get("style", "未知"),
                    recent_stocks=stocks[:10],
                    win_rate=None,  # 需要历史数据计算
                ))

            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            logger.error("Failed to fetch hot money activity", error=str(e))
            return []

    async def get_summary(self) -> LHBSummary:
        """获取龙虎榜概览"""
        daily_lhb, hot_money = await asyncio.gather(
            self.get_daily_lhb(),
            self.get_hot_money_activity(),
        )

        total_net = sum(s.lhb_net_buy for s in daily_lhb) / 10000  # 转为亿元
        inst_net = sum(s.institution_net for s in daily_lhb) / 10000

        # 排序获取 TOP
        top_buys = sorted(daily_lhb, key=lambda x: x.lhb_net_buy, reverse=True)[:10]
        top_sells = sorted(daily_lhb, key=lambda x: x.lhb_net_buy)[:10]

        return LHBSummary(
            date=datetime.now().date(),
            total_stocks=len(daily_lhb),
            total_net_buy=total_net,
            institution_net_buy=inst_net,
            top_buys=top_buys,
            top_sells=top_sells,
            hot_money_active=hot_money,
        )


# 单例实例
lhb_service = LHBService()
