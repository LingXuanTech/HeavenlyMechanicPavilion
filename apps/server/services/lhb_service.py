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

from services.cache_service import cache_service

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


class HotMoneyProfile(BaseModel):
    """游资席位完整画像"""
    seat_name: str = Field(description="营业部名称")
    alias: str = Field(description="游资别名/江湖名号")
    tier: str = Field(description="游资层级: 一线/二线/新锐")
    style: str = Field(description="操作风格")
    style_tags: List[str] = Field(default_factory=list, description="风格标签")

    # 历史统计
    total_appearances: int = Field(default=0, description="历史上榜次数")
    total_buy_amount: float = Field(default=0, description="历史总买入金额（亿元）")
    total_sell_amount: float = Field(default=0, description="历史总卖出金额（亿元）")
    avg_net_buy: float = Field(default=0, description="平均单次净买入（万元）")
    win_rate: Optional[float] = Field(default=None, description="历史胜率（次日上涨%）")
    avg_holding_days: Optional[float] = Field(default=None, description="平均持有天数")

    # 操作偏好
    preferred_sectors: List[str] = Field(default_factory=list, description="偏好板块")
    preferred_market_cap: str = Field(default="中小盘", description="偏好市值: 大盘/中盘/小盘/中小盘")
    active_time_pattern: str = Field(default="全天活跃", description="活跃时间特征")

    # 近期操作
    recent_operations: List[dict] = Field(default_factory=list, description="近期操作记录")
    last_active_date: Optional[date] = Field(default=None, description="最近活跃日期")

    # 关联分析
    correlated_seats: List[str] = Field(default_factory=list, description="常一起出现的席位")
    success_stocks: List[str] = Field(default_factory=list, description="成功案例股票")


class HotMoneyMovementSignal(BaseModel):
    """游资动向信号"""
    signal_date: date = Field(description="信号日期")
    signal_type: str = Field(description="信号类型: consensus_buy/consensus_sell/divergence/new_entry")
    signal_strength: int = Field(description="信号强度 0-100")
    involved_seats: List[str] = Field(description="涉及的游资席位")
    target_stocks: List[dict] = Field(description="目标股票列表")
    interpretation: str = Field(description="信号解读")


class LHBSummary(BaseModel):
    """龙虎榜概览"""
    data_date: date
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
    "华鑫证券上海分公司": {
        "alias": "溧阳路",
        "tier": "一线",
        "style": "打板/接力",
        "style_tags": ["打板", "接力", "题材"],
        "preferred_sectors": ["科技", "新能源", "军工"],
        "preferred_market_cap": "中小盘",
    },
    "中国银河证券绍兴证券营业部": {
        "alias": "赵老哥",
        "tier": "一线",
        "style": "打板/龙头",
        "style_tags": ["打板", "龙头战法", "趋势"],
        "preferred_sectors": ["题材龙头", "次新股"],
        "preferred_market_cap": "中盘",
    },
    "国泰君安上海江苏路": {
        "alias": "章盟主",
        "tier": "一线",
        "style": "趋势/波段",
        "style_tags": ["趋势", "波段", "大资金"],
        "preferred_sectors": ["白马股", "行业龙头"],
        "preferred_market_cap": "大盘",
    },
    "东方财富证券拉萨团结路第二": {
        "alias": "拉萨天团",
        "tier": "一线",
        "style": "打板/接力",
        "style_tags": ["打板", "接力", "激进"],
        "preferred_sectors": ["题材", "概念"],
        "preferred_market_cap": "小盘",
    },
    "东方财富证券拉萨东环路第二": {
        "alias": "拉萨天团",
        "tier": "一线",
        "style": "打板/接力",
        "style_tags": ["打板", "接力", "激进"],
        "preferred_sectors": ["题材", "概念"],
        "preferred_market_cap": "小盘",
    },
    "华泰证券深圳益田路荣超商务中心": {
        "alias": "深圳帮",
        "tier": "一线",
        "style": "趋势/题材",
        "style_tags": ["趋势", "题材", "中线"],
        "preferred_sectors": ["科技", "消费"],
        "preferred_market_cap": "中盘",
    },
    "中信证券上海溧阳路": {
        "alias": "顶级游资",
        "tier": "一线",
        "style": "大资金/趋势",
        "style_tags": ["大资金", "趋势", "稳健"],
        "preferred_sectors": ["行业龙头", "白马股"],
        "preferred_market_cap": "大盘",
    },

    # 二线游资
    "财通证券杭州上塘路": {
        "alias": "杭州帮",
        "tier": "二线",
        "style": "题材/接力",
        "style_tags": ["题材", "接力", "短线"],
        "preferred_sectors": ["互联网", "新零售"],
        "preferred_market_cap": "中小盘",
    },
    "国盛证券宁波桑田路": {
        "alias": "宁波桑田路",
        "tier": "二线",
        "style": "打板/短线",
        "style_tags": ["打板", "短线", "激进"],
        "preferred_sectors": ["题材", "次新"],
        "preferred_market_cap": "小盘",
    },
    "华泰证券成都蜀金路": {
        "alias": "成都帮",
        "tier": "二线",
        "style": "题材/波段",
        "style_tags": ["题材", "波段", "区域股"],
        "preferred_sectors": ["西部概念", "基建"],
        "preferred_market_cap": "中盘",
    },
    "西藏东方财富证券拉萨团结路第一": {
        "alias": "拉萨天团",
        "tier": "一线",
        "style": "打板/接力",
        "style_tags": ["打板", "接力", "激进"],
        "preferred_sectors": ["题材", "概念"],
        "preferred_market_cap": "小盘",
    },
    "申万宏源西部证券上海分公司": {
        "alias": "上海帮",
        "tier": "二线",
        "style": "趋势/题材",
        "style_tags": ["趋势", "题材"],
        "preferred_sectors": ["科技", "新能源"],
        "preferred_market_cap": "中盘",
    },
    "中泰证券深圳欢乐海岸": {
        "alias": "欢乐海岸",
        "tier": "二线",
        "style": "接力/题材",
        "style_tags": ["接力", "题材", "短线"],
        "preferred_sectors": ["热点题材"],
        "preferred_market_cap": "中小盘",
    },
    "国信证券深圳泰然九路": {
        "alias": "泰然九路",
        "tier": "二线",
        "style": "趋势/波段",
        "style_tags": ["趋势", "波段"],
        "preferred_sectors": ["科技", "医药"],
        "preferred_market_cap": "中盘",
    },

    # 机构专用席位标识
    "机构专用": {
        "alias": "机构",
        "tier": "机构",
        "style": "机构",
        "style_tags": ["机构"],
        "preferred_sectors": [],
        "preferred_market_cap": "大盘",
    },
}


# ============ 服务类 ============

class LHBService:
    """龙虎榜解析服务"""

    def __init__(self):
        pass

    def _identify_seat_type(self, seat_name: str) -> tuple:
        """识别席位类型和游资信息

        Returns:
            (seat_type, style, hot_money_alias, tier)
        """
        if "机构专用" in seat_name:
            return "机构", "机构", "机构", "机构"

        for pattern, info in HOT_MONEY_SEATS.items():
            if pattern in seat_name:
                return "游资", info["style"], info["alias"], info.get("tier", "未知")

        return "普通", "未知", None, None

    def _parse_seat_data(self, seat_name: str, buy: float, sell: float) -> LHBSeat:
        """解析席位数据"""
        seat_type, style, hot_money, _ = self._identify_seat_type(seat_name)
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
        cached = cache_service.get_sync(cache_key)
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

            cache_service.set_sync(cache_key, result, ttl=600)
            logger.info("Fetched daily LHB", count=len(result), date=trade_date)
            return result

        except Exception as e:
            logger.error("Failed to fetch daily LHB", error=str(e))
            return []

    async def get_stock_lhb_history(self, symbol: str, days: int = 30) -> List[LHBRecord]:
        """获取个股龙虎榜历史"""
        cache_key = f"stock_lhb_{symbol}_{days}"
        cached = cache_service.get_sync(cache_key)
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

            cache_service.set_sync(cache_key, result, ttl=600)
            return result

        except Exception as e:
            logger.error("Failed to fetch stock LHB history", symbol=symbol, error=str(e))
            return []

    async def get_hot_money_activity(self, days: int = 5) -> List[HotMoneySeat]:
        """获取知名游资近期活动"""
        cache_key = f"hot_money_{days}"
        cached = cache_service.get_sync(cache_key)
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

            cache_service.set_sync(cache_key, result, ttl=600)
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
            data_date=datetime.now().date(),
            total_stocks=len(daily_lhb),
            total_net_buy=total_net,
            institution_net_buy=inst_net,
            top_buys=top_buys,
            top_sells=top_sells,
            hot_money_active=hot_money,
        )

    # ============ 游资席位画像功能 ============

    async def get_hot_money_profile(self, alias: str) -> Optional[HotMoneyProfile]:
        """获取单个游资席位的完整画像

        Args:
            alias: 游资别名（如 "溧阳路"、"赵老哥"）

        Returns:
            游资完整画像，包含历史统计和操作特征
        """
        cache_key = f"hot_money_profile_{alias}"
        cached = cache_service.get_sync(cache_key)
        if cached:
            return cached

        try:
            # 查找席位信息
            seat_name = None
            seat_info = None
            for name, info in HOT_MONEY_SEATS.items():
                if info.get("alias") == alias:
                    seat_name = name
                    seat_info = info
                    break

            if not seat_info:
                logger.warning("Hot money alias not found", alias=alias)
                return None

            # 获取近期活动数据
            daily_lhb = await self.get_daily_lhb()

            # 统计该游资的操作
            operations = []
            total_buy = 0.0
            total_sell = 0.0
            appearance_count = 0

            for stock in daily_lhb:
                for seat in stock.buy_seats + stock.sell_seats:
                    if seat.hot_money_name == alias:
                        appearance_count += 1
                        total_buy += seat.buy_amount
                        total_sell += seat.sell_amount
                        operations.append({
                            "date": datetime.now().date().isoformat(),
                            "symbol": stock.symbol,
                            "name": stock.name,
                            "action": "买入" if seat.net_amount > 0 else "卖出",
                            "amount": abs(seat.net_amount),
                            "change_percent": stock.change_percent,
                        })

            # 构建画像
            profile = HotMoneyProfile(
                seat_name=seat_name,
                alias=alias,
                tier=seat_info.get("tier", "未知"),
                style=seat_info.get("style", "未知"),
                style_tags=seat_info.get("style_tags", []),
                total_appearances=appearance_count,
                total_buy_amount=total_buy / 10000,  # 转为亿元
                total_sell_amount=total_sell / 10000,
                avg_net_buy=(total_buy - total_sell) / max(appearance_count, 1),
                preferred_sectors=seat_info.get("preferred_sectors", []),
                preferred_market_cap=seat_info.get("preferred_market_cap", "中小盘"),
                recent_operations=operations[:20],
                last_active_date=datetime.now().date() if operations else None,
                # 以下字段需要历史数据计算，暂时使用预设值
                win_rate=None,
                avg_holding_days=None,
                correlated_seats=[],
                success_stocks=[],
            )

            cache_service.set_sync(cache_key, profile, ttl=600)
            return profile

        except Exception as e:
            logger.error("Failed to get hot money profile", alias=alias, error=str(e))
            return None

    async def get_all_hot_money_profiles(self, tier: Optional[str] = None) -> List[HotMoneyProfile]:
        """获取所有知名游资画像列表

        Args:
            tier: 可选过滤条件，按层级筛选（一线/二线）

        Returns:
            游资画像列表
        """
        cache_key = f"all_hot_money_profiles_{tier or 'all'}"
        cached = cache_service.get_sync(cache_key)
        if cached:
            return cached

        try:
            # 获取所有唯一的游资别名
            unique_aliases = set()
            for info in HOT_MONEY_SEATS.values():
                if info.get("alias") and info.get("alias") != "机构":
                    if tier is None or info.get("tier") == tier:
                        unique_aliases.add(info["alias"])

            # 并行获取所有画像
            profiles = await asyncio.gather(
                *[self.get_hot_money_profile(alias) for alias in unique_aliases]
            )

            result = [p for p in profiles if p is not None]

            # 按层级和活跃度排序
            tier_order = {"一线": 0, "二线": 1, "新锐": 2, "未知": 3}
            result.sort(key=lambda x: (tier_order.get(x.tier, 99), -x.total_appearances))

            cache_service.set_sync(cache_key, result, ttl=600)
            return result

        except Exception as e:
            logger.error("Failed to get all hot money profiles", error=str(e))
            return []

    async def get_hot_money_movement_signal(self) -> HotMoneyMovementSignal:
        """获取游资动向信号

        分析多个知名游资的同向操作，生成跟踪信号。
        """
        try:
            daily_lhb = await self.get_daily_lhb()

            # 统计游资操作
            buy_consensus: Dict[str, List[str]] = {}  # 股票 -> 买入的游资列表
            sell_consensus: Dict[str, List[str]] = {}  # 股票 -> 卖出的游资列表

            involved_seats = set()
            target_stocks = []

            for stock in daily_lhb:
                stock_buys = []
                stock_sells = []

                for seat in stock.buy_seats:
                    if seat.hot_money_name:
                        stock_buys.append(seat.hot_money_name)
                        involved_seats.add(seat.hot_money_name)

                for seat in stock.sell_seats:
                    if seat.hot_money_name:
                        stock_sells.append(seat.hot_money_name)
                        involved_seats.add(seat.hot_money_name)

                if stock_buys:
                    buy_consensus[stock.symbol] = stock_buys
                if stock_sells:
                    sell_consensus[stock.symbol] = stock_sells

            # 分析信号类型
            # 找出多个游资同时买入的股票
            multi_buy_stocks = {
                k: v for k, v in buy_consensus.items() if len(v) >= 2
            }
            multi_sell_stocks = {
                k: v for k, v in sell_consensus.items() if len(v) >= 2
            }

            # 确定信号类型和强度
            if multi_buy_stocks:
                signal_type = "consensus_buy"
                signal_strength = min(100, 50 + len(multi_buy_stocks) * 20)
                for symbol, seats in multi_buy_stocks.items():
                    stock_info = next((s for s in daily_lhb if s.symbol == symbol), None)
                    if stock_info:
                        target_stocks.append({
                            "symbol": symbol,
                            "name": stock_info.name,
                            "change_percent": stock_info.change_percent,
                            "involved_seats": seats,
                            "action": "买入",
                        })
                interpretation = (
                    f"多路知名游资（{', '.join(list(involved_seats)[:3])}等）同时买入 "
                    f"{len(multi_buy_stocks)} 只股票，形成共识看多信号。"
                )

            elif multi_sell_stocks:
                signal_type = "consensus_sell"
                signal_strength = min(100, 50 + len(multi_sell_stocks) * 20)
                for symbol, seats in multi_sell_stocks.items():
                    stock_info = next((s for s in daily_lhb if s.symbol == symbol), None)
                    if stock_info:
                        target_stocks.append({
                            "symbol": symbol,
                            "name": stock_info.name,
                            "change_percent": stock_info.change_percent,
                            "involved_seats": seats,
                            "action": "卖出",
                        })
                interpretation = (
                    f"多路知名游资同时卖出 {len(multi_sell_stocks)} 只股票，"
                    f"注意规避风险。"
                )

            elif buy_consensus and sell_consensus:
                signal_type = "divergence"
                signal_strength = 40
                # 合并目标股票
                for symbol, seats in list(buy_consensus.items())[:5]:
                    stock_info = next((s for s in daily_lhb if s.symbol == symbol), None)
                    if stock_info:
                        target_stocks.append({
                            "symbol": symbol,
                            "name": stock_info.name,
                            "change_percent": stock_info.change_percent,
                            "involved_seats": seats,
                            "action": "买入",
                        })
                interpretation = "游资操作分化，无明显共识方向，建议观望或轻仓试探。"

            elif involved_seats:
                signal_type = "new_entry"
                signal_strength = 30
                for symbol, seats in list(buy_consensus.items())[:5]:
                    stock_info = next((s for s in daily_lhb if s.symbol == symbol), None)
                    if stock_info:
                        target_stocks.append({
                            "symbol": symbol,
                            "name": stock_info.name,
                            "change_percent": stock_info.change_percent,
                            "involved_seats": seats,
                            "action": "买入",
                        })
                interpretation = "知名游资有新动作，但未形成共识，可关注后续动向。"

            else:
                signal_type = "no_activity"
                signal_strength = 0
                interpretation = "今日无知名游资活动记录。"

            return HotMoneyMovementSignal(
                signal_date=datetime.now().date(),
                signal_type=signal_type,
                signal_strength=signal_strength,
                involved_seats=list(involved_seats)[:10],
                target_stocks=target_stocks[:10],
                interpretation=interpretation,
            )

        except Exception as e:
            logger.error("Failed to get hot money movement signal", error=str(e))
            return HotMoneyMovementSignal(
                signal_date=datetime.now().date(),
                signal_type="error",
                signal_strength=0,
                involved_seats=[],
                target_stocks=[],
                interpretation=f"获取游资动向信号失败: {str(e)}",
            )

    async def get_seat_correlation(self, alias: str) -> List[Dict[str, Any]]:
        """获取与指定游资经常一起出现的席位

        Args:
            alias: 游资别名

        Returns:
            关联席位列表，按共现次数排序
        """
        try:
            daily_lhb = await self.get_daily_lhb()

            # 统计共现
            co_occurrence: Dict[str, int] = {}

            for stock in daily_lhb:
                all_seats = stock.buy_seats + stock.sell_seats
                target_present = any(s.hot_money_name == alias for s in all_seats)

                if target_present:
                    for seat in all_seats:
                        if seat.hot_money_name and seat.hot_money_name != alias:
                            co_occurrence[seat.hot_money_name] = (
                                co_occurrence.get(seat.hot_money_name, 0) + 1
                            )

            # 排序并返回
            result = [
                {"alias": k, "co_occurrence_count": v}
                for k, v in sorted(co_occurrence.items(), key=lambda x: -x[1])
            ]

            return result[:10]

        except Exception as e:
            logger.error("Failed to get seat correlation", alias=alias, error=str(e))
            return []


# 单例实例
lhb_service = LHBService()
