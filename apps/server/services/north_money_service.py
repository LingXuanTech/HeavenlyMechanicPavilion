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


class NorthMoneySectorFlow(BaseModel):
    """北向资金板块流向"""
    sector: str = Field(description="板块名称")
    sector_code: str = Field(default="", description="板块代码")
    net_buy: float = Field(description="净买入金额（亿元）")
    stock_count: int = Field(description="涉及股票数量")
    top_stocks: List[str] = Field(default_factory=list, description="TOP 净买入个股")
    flow_direction: str = Field(description="资金方向: inflow / outflow / neutral")
    change_ratio: float = Field(default=0, description="较昨日变化比例（%）")


class SectorRotationSignal(BaseModel):
    """板块轮动信号"""
    date: DateType = Field(description="信号日期")
    inflow_sectors: List[str] = Field(description="资金流入板块（按流入强度排序）")
    outflow_sectors: List[str] = Field(description="资金流出板块（按流出强度排序）")
    rotation_pattern: str = Field(description="轮动模式: defensive / aggressive / mixed / unclear")
    signal_strength: int = Field(description="信号强度 0-100")
    interpretation: str = Field(description="信号解读")


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

    # ============ 板块轮动分析 ============

    # 申万一级行业与关键词映射
    SECTOR_KEYWORDS = {
        "银行": ["银行", "农商", "城商"],
        "非银金融": ["证券", "券商", "保险", "信托", "期货"],
        "房地产": ["地产", "房产", "物业", "置业"],
        "食品饮料": ["酒", "乳业", "饮料", "食品", "调味"],
        "医药生物": ["医药", "生物", "制药", "医疗", "疫苗"],
        "电子": ["电子", "半导体", "芯片", "面板", "元器件"],
        "计算机": ["软件", "信息", "科技", "数据", "云计算"],
        "电气设备": ["电气", "新能源", "光伏", "风电", "电池", "储能"],
        "汽车": ["汽车", "整车", "汽配"],
        "机械设备": ["机械", "设备", "工程", "自动化"],
        "有色金属": ["有色", "铜", "铝", "锂", "稀土", "黄金"],
        "化工": ["化工", "化学", "材料"],
        "建筑材料": ["水泥", "玻璃", "建材"],
        "公用事业": ["电力", "水务", "燃气", "环保"],
        "交通运输": ["航运", "物流", "铁路", "航空", "港口"],
        "传媒": ["传媒", "游戏", "影视", "广告"],
        "通信": ["通信", "电信", "5G", "运营商"],
        "家用电器": ["家电", "电器", "空调"],
        "纺织服装": ["服装", "纺织", "鞋帽"],
        "国防军工": ["军工", "航天", "国防", "航空"],
    }

    # 板块特性分类
    DEFENSIVE_SECTORS = ["银行", "食品饮料", "公用事业", "医药生物", "交通运输"]
    AGGRESSIVE_SECTORS = ["电子", "计算机", "电气设备", "有色金属", "国防军工"]

    async def get_sector_flow(self) -> List[NorthMoneySectorFlow]:
        """获取北向资金板块流向

        基于个股北向持仓变化，聚合到板块级别。
        """
        cache_key = "sector_flow"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            # 获取北向持股数据
            df = await asyncio.to_thread(
                ak.stock_hsgt_hold_stock_em,
                market="北向",
                indicator="今日排行"
            )

            if df.empty:
                return []

            # 聚合到板块
            sector_data: Dict[str, Dict] = {}

            for _, row in df.iterrows():
                stock_name = str(row.get('名称', ''))
                net_buy = float(row.get('净买额', 0) or row.get('今日增持市值', 0) or 0) / 1e8

                # 识别板块
                matched_sector = self._match_sector(stock_name)
                if matched_sector not in sector_data:
                    sector_data[matched_sector] = {
                        "net_buy": 0,
                        "stock_count": 0,
                        "top_stocks": [],
                    }

                sector_data[matched_sector]["net_buy"] += net_buy
                sector_data[matched_sector]["stock_count"] += 1

                # 记录 TOP 个股
                if abs(net_buy) > 0.1:  # 净买入/卖出超过 1000 万
                    sector_data[matched_sector]["top_stocks"].append(
                        f"{stock_name}({net_buy:+.2f}亿)"
                    )

            # 转换为模型
            result = []
            for sector, data in sector_data.items():
                net_buy = data["net_buy"]
                if net_buy > 0.5:
                    direction = "inflow"
                elif net_buy < -0.5:
                    direction = "outflow"
                else:
                    direction = "neutral"

                result.append(NorthMoneySectorFlow(
                    sector=sector,
                    net_buy=round(net_buy, 2),
                    stock_count=data["stock_count"],
                    top_stocks=data["top_stocks"][:5],
                    flow_direction=direction,
                ))

            # 按净买入排序
            result.sort(key=lambda x: x.net_buy, reverse=True)

            self._set_cache(cache_key, result)
            logger.info("Calculated sector flow", sectors=len(result))
            return result

        except Exception as e:
            logger.error("Failed to calculate sector flow", error=str(e))
            return []

    def _match_sector(self, stock_name: str) -> str:
        """根据股票名称匹配板块"""
        for sector, keywords in self.SECTOR_KEYWORDS.items():
            for keyword in keywords:
                if keyword in stock_name:
                    return sector
        return "其他"

    async def get_sector_rotation_signal(self) -> SectorRotationSignal:
        """获取板块轮动信号

        分析北向资金在不同板块间的流动，判断轮动模式。
        """
        sector_flows = await self.get_sector_flow()

        if not sector_flows:
            return SectorRotationSignal(
                date=datetime.now().date(),
                inflow_sectors=[],
                outflow_sectors=[],
                rotation_pattern="unclear",
                signal_strength=0,
                interpretation="数据不足，无法判断板块轮动",
            )

        # 分类流入/流出板块
        inflow_sectors = [
            s.sector for s in sector_flows
            if s.flow_direction == "inflow"
        ]
        outflow_sectors = [
            s.sector for s in sector_flows
            if s.flow_direction == "outflow"
        ]

        # 计算防御/进攻板块的净流入
        defensive_net = sum(
            s.net_buy for s in sector_flows
            if s.sector in self.DEFENSIVE_SECTORS
        )
        aggressive_net = sum(
            s.net_buy for s in sector_flows
            if s.sector in self.AGGRESSIVE_SECTORS
        )

        # 判断轮动模式
        total_inflow = sum(s.net_buy for s in sector_flows if s.net_buy > 0)
        total_outflow = abs(sum(s.net_buy for s in sector_flows if s.net_buy < 0))

        if defensive_net > aggressive_net * 1.5:
            pattern = "defensive"
            interpretation = "北向资金流向防御性板块（银行、食品饮料、公用事业等），市场风险偏好下降，建议谨慎操作。"
        elif aggressive_net > defensive_net * 1.5:
            pattern = "aggressive"
            interpretation = "北向资金流向进攻性板块（电子、计算机、新能源等），市场风险偏好上升，可适当加仓成长股。"
        elif total_inflow > total_outflow * 2:
            pattern = "broad_inflow"
            interpretation = "北向资金全面流入，市场情绪积极，可维持多头思维。"
        elif total_outflow > total_inflow * 2:
            pattern = "broad_outflow"
            interpretation = "北向资金全面流出，市场情绪谨慎，建议控制仓位。"
        else:
            pattern = "mixed"
            interpretation = "北向资金板块分化，无明显轮动方向，建议观望或个股操作。"

        # 计算信号强度
        total_flow = total_inflow + total_outflow
        if total_flow > 100:
            strength = 90
        elif total_flow > 50:
            strength = 70
        elif total_flow > 20:
            strength = 50
        else:
            strength = 30

        # 调整：如果模式清晰，强度加成
        if pattern in ["defensive", "aggressive"]:
            strength = min(100, strength + 15)

        return SectorRotationSignal(
            date=datetime.now().date(),
            inflow_sectors=inflow_sectors[:5],
            outflow_sectors=outflow_sectors[:5],
            rotation_pattern=pattern,
            signal_strength=strength,
            interpretation=interpretation,
        )

    async def get_sector_flow_history(self, days: int = 5) -> Dict[str, List[float]]:
        """获取板块资金流向历史（简化版，用于趋势分析）

        注意：由于 AkShare 不提供历史板块流向，此方法返回模拟数据或需要自行存储。
        实际生产中应接入专业数据源或自建历史数据库。
        """
        # TODO: 实现历史数据存储和查询
        # 当前返回空数据，后续迭代可接入数据库
        logger.debug("Sector flow history not implemented, returning empty")
        return {}


# 单例实例
north_money_service = NorthMoneyService()
