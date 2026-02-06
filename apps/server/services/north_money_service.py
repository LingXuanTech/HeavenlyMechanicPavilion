"""北向资金监控服务

提供沪深港通北向资金流向数据，包括：
- 当日资金流向
- 盘中分时流向（实时）
- 个股北向持仓变化
- 净买入/卖出 TOP 榜单
- 板块轮动信号
- 异常流动检测
- 历史数据持久化存储
- 北向资金与指数相关性分析
"""
from datetime import datetime, date as DateType, time as TimeType
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field
import structlog
import akshare as ak
import pandas as pd
import numpy as np
from functools import lru_cache
import asyncio
import statistics

from sqlmodel import Session, select
from db.models import NorthMoneyHistoryRecord, engine
from services.cache_service import cache_service

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


# ============ 盘中实时模型 ============

class IntradayFlowPoint(BaseModel):
    """盘中分时流向数据点"""
    time: str = Field(description="时间 (HH:MM)")
    sh_connect: float = Field(description="沪股通净流入（亿元）")
    sz_connect: float = Field(description="深股通净流入（亿元）")
    total: float = Field(description="北向资金净流入合计（亿元）")
    cumulative_total: float = Field(description="累计净流入（亿元）")


class IntradayFlowSummary(BaseModel):
    """盘中实时流向汇总"""
    date: DateType = Field(description="日期")
    last_update: str = Field(description="最后更新时间")
    current_total: float = Field(description="当前累计净流入（亿元）")
    flow_points: List[IntradayFlowPoint] = Field(default_factory=list, description="分时数据点")
    peak_inflow: float = Field(description="盘中峰值净流入")
    peak_outflow: float = Field(description="盘中峰值净流出")
    flow_volatility: float = Field(default=0, description="流向波动率")
    momentum: str = Field(description="动量方向: accelerating / decelerating / stable")


class NorthMoneyAnomaly(BaseModel):
    """北向资金异常信号"""
    timestamp: datetime = Field(description="检测时间")
    anomaly_type: str = Field(description="异常类型: sudden_inflow / sudden_outflow / reversal / volume_spike")
    severity: str = Field(description="严重程度: low / medium / high / critical")
    description: str = Field(description="异常描述")
    affected_stocks: List[str] = Field(default_factory=list, description="受影响个股")
    flow_change: float = Field(description="流向变化（亿元）")
    recommendation: str = Field(description="操作建议")


class NorthMoneyRealtime(BaseModel):
    """北向资金实时全景"""
    summary: NorthMoneySummary = Field(description="基础概览")
    intraday: Optional[IntradayFlowSummary] = Field(default=None, description="盘中实时")
    anomalies: List[NorthMoneyAnomaly] = Field(default_factory=list, description="异常信号")
    index_correlation: Optional[Dict[str, float]] = Field(default=None, description="与主要指数相关性")
    is_trading_hours: bool = Field(default=False, description="是否交易时段")


# ============ 历史数据和相关性分析模型 ============

class NorthMoneyHistoryData(BaseModel):
    """北向资金历史数据（从数据库查询）"""
    date: str = Field(description="日期 YYYY-MM-DD")
    north_inflow: float = Field(description="北向资金净流入（亿元）")
    sh_inflow: float = Field(description="沪股通净流入（亿元）")
    sz_inflow: float = Field(description="深股通净流入（亿元）")
    cumulative_inflow: float = Field(description="累计净流入（亿元）")
    market_index: Optional[float] = Field(default=None, description="上证指数收盘价")
    hs300_index: Optional[float] = Field(default=None, description="沪深300收盘价")
    cyb_index: Optional[float] = Field(default=None, description="创业板指收盘价")


class CorrelationResult(BaseModel):
    """相关性计算结果"""
    index_name: str = Field(description="指数名称")
    window: int = Field(description="计算窗口（天数）")
    correlation: float = Field(description="相关系数 (-1 到 1)")
    p_value: Optional[float] = Field(default=None, description="P值（统计显著性）")
    sample_size: int = Field(description="样本数量")
    interpretation: str = Field(description="相关性解读")


class CorrelationAnalysis(BaseModel):
    """北向资金与指数相关性分析"""
    analysis_date: str = Field(description="分析日期")
    correlations: List[CorrelationResult] = Field(description="各指数相关性结果")
    summary: str = Field(description="综合分析结论")
    data_range: str = Field(description="数据范围")


class HistoryQueryResult(BaseModel):
    """历史数据查询结果"""
    data: List[NorthMoneyHistoryData] = Field(description="历史数据列表")
    total_count: int = Field(description="总记录数")
    start_date: str = Field(description="起始日期")
    end_date: str = Field(description="结束日期")
    statistics: Dict[str, float] = Field(description="统计信息")


# ============ 服务类 ============

class NorthMoneyService:
    """北向资金监控服务"""

    def __init__(self):
        pass

    async def get_north_money_flow(self) -> NorthMoneyFlow:
        """获取当日北向资金流向"""
        cache_key = "north_money_flow"
        cached = cache_service.get_sync(cache_key)
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

            cache_service.set_sync(cache_key, flow, ttl=300)
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
        cached = cache_service.get_sync(cache_key)
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

            cache_service.set_sync(cache_key, history, ttl=300)
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
        cached = cache_service.get_sync(cache_key)
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

            cache_service.set_sync(cache_key, result, ttl=300)
            return result

        except Exception as e:
            logger.error("Failed to fetch top north buys", error=str(e))
            return []

    async def get_top_north_sells(self, limit: int = 20) -> List[NorthMoneyTopStock]:
        """获取北向资金净卖出 TOP"""
        cache_key = f"top_north_sells_{limit}"
        cached = cache_service.get_sync(cache_key)
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

            cache_service.set_sync(cache_key, result, ttl=300)
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
        cached = cache_service.get_sync(cache_key)
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

            cache_service.set_sync(cache_key, result, ttl=300)
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

    async def save_daily_data(self, target_date: Optional[DateType] = None) -> bool:
        """将每日北向资金和指数数据保存到数据库"""
        try:
            date_str = (target_date or datetime.now().date()).strftime("%Y-%m-%d")
            
            # 1. 获取北向资金数据
            df_north = await asyncio.to_thread(ak.stock_hsgt_north_net_flow_in_em)
            if df_north.empty:
                logger.warning("No north money data from AkShare")
                return False
            
            # 匹配日期
            df_north['日期'] = pd.to_datetime(df_north['日期']).dt.strftime("%Y-%m-%d")
            day_data = df_north[df_north['日期'] == date_str]
            
            if day_data.empty:
                logger.info("No north money data for date", date=date_str)
                return False
            
            row = day_data.iloc[0]
            
            # 2. 获取指数数据
            # 上证指数
            df_sh = await asyncio.to_thread(ak.stock_zh_index_daily, symbol="sh000001")
            df_sh.index = pd.to_datetime(df_sh.index).strftime("%Y-%m-%d")
            sh_price = float(df_sh.loc[date_str, 'close']) if date_str in df_sh.index else None
            
            # 沪深300
            df_hs300 = await asyncio.to_thread(ak.stock_zh_index_daily, symbol="sh000300")
            df_hs300.index = pd.to_datetime(df_hs300.index).strftime("%Y-%m-%d")
            hs300_price = float(df_hs300.loc[date_str, 'close']) if date_str in df_hs300.index else None
            
            # 创业板
            df_cyb = await asyncio.to_thread(ak.stock_zh_index_daily, symbol="sz399006")
            df_cyb.index = pd.to_datetime(df_cyb.index).strftime("%Y-%m-%d")
            cyb_price = float(df_cyb.loc[date_str, 'close']) if date_str in df_cyb.index else None
            
            # 3. 保存到数据库
            with Session(engine) as session:
                # 检查是否已存在
                existing = session.exec(
                    select(NorthMoneyHistoryRecord).where(NorthMoneyHistoryRecord.date == date_str)
                ).first()
                
                if existing:
                    record = existing
                    record.updated_at = datetime.now()
                else:
                    record = NorthMoneyHistoryRecord(date=date_str)
                
                record.north_inflow = float(row.get('北向资金', 0) or row.get('合计', 0))
                record.sh_inflow = float(row.get('沪股通', 0) or 0)
                record.sz_inflow = float(row.get('深股通', 0) or 0)
                record.cumulative_inflow = float(row.get('累计净流入', 0) or 0)
                record.market_index = sh_price
                record.hs300_index = hs300_price
                record.cyb_index = cyb_price
                
                session.add(record)
                session.commit()
                logger.info("Saved daily north money data", date=date_str)
                return True
                
        except Exception as e:
            logger.error("Failed to save daily data", error=str(e))
            return False

    async def get_history(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> HistoryQueryResult:
        """从数据库查询历史数据"""
        try:
            with Session(engine) as session:
                statement = select(NorthMoneyHistoryRecord).order_by(NorthMoneyHistoryRecord.date.desc())
                
                if start_date:
                    statement = statement.where(NorthMoneyHistoryRecord.date >= start_date)
                if end_date:
                    statement = statement.where(NorthMoneyHistoryRecord.date <= end_date)
                
                statement = statement.limit(limit)
                results = session.exec(statement).all()
                
                data = [
                    NorthMoneyHistoryData(
                        date=r.date,
                        north_inflow=r.north_inflow,
                        sh_inflow=r.sh_inflow,
                        sz_inflow=r.sz_inflow,
                        cumulative_inflow=r.cumulative_inflow,
                        market_index=r.market_index,
                        hs300_index=r.hs300_index,
                        cyb_index=r.cyb_index
                    ) for r in results
                ]
                
                # 计算简单统计
                stats = {}
                if data:
                    inflows = [d.north_inflow for d in data]
                    stats = {
                        "avg_inflow": round(statistics.mean(inflows), 2),
                        "max_inflow": round(max(inflows), 2),
                        "min_inflow": round(min(inflows), 2),
                        "total_inflow": round(sum(inflows), 2)
                    }
                
                return HistoryQueryResult(
                    data=data,
                    total_count=len(data),
                    start_date=data[-1].date if data else "",
                    end_date=data[0].date if data else "",
                    statistics=stats
                )
        except Exception as e:
            logger.error("Failed to query history from DB", error=str(e))
            return HistoryQueryResult(data=[], total_count=0, start_date="", end_date="", statistics={})

    async def calculate_correlation(self, days: int = 20) -> CorrelationAnalysis:
        """计算北向资金与指数的相关性"""
        try:
            # 获取历史数据
            history = await self.get_history(limit=days + 1)
            if len(history.data) < 5:
                return CorrelationAnalysis(
                    analysis_date=datetime.now().strftime("%Y-%m-%d"),
                    correlations=[],
                    summary="数据不足，无法计算相关性",
                    data_range=""
                )
            
            # 转换为 DataFrame
            df = pd.DataFrame([d.model_dump() for d in history.data])
            df = df.sort_values('date')
            
            results = []
            indices = [
                ("上证指数", "market_index"),
                ("沪深300", "hs300_index"),
                ("创业板指", "cyb_index")
            ]
            
            for name, col in indices:
                if col in df.columns and not df[col].isnull().all():
                    # 计算收益率或直接计算价格相关性？通常计算资金流入与指数涨跌的相关性
                    # 这里按照要求计算 north_inflow 与 market_index 的相关性
                    valid_df = df[['north_inflow', col]].dropna()
                    if len(valid_df) >= 5:
                        corr = valid_df['north_inflow'].corr(valid_df[col])
                        
                        if abs(corr) > 0.8:
                            interp = "极强相关"
                        elif abs(corr) > 0.6:
                            interp = "强相关"
                        elif abs(corr) > 0.4:
                            interp = "中等相关"
                        else:
                            interp = "弱相关或不相关"
                            
                        results.append(CorrelationResult(
                            index_name=name,
                            window=len(valid_df),
                            correlation=round(corr, 4),
                            sample_size=len(valid_df),
                            interpretation=interp
                        ))
            
            # 生成总结
            if results:
                main_corr = results[0].correlation
                if main_corr > 0.5:
                    summary = f"北向资金与主要指数呈现显著正相关({main_corr})，资金流入对市场有较强带动作用。"
                elif main_corr < -0.5:
                    summary = f"北向资金与主要指数呈现显著负相关({main_corr})，可能存在背离或对冲行为。"
                else:
                    summary = "北向资金与主要指数相关性不明显，市场走势受多重因素影响。"
            else:
                summary = "无法计算有效相关性"

            return CorrelationAnalysis(
                analysis_date=datetime.now().strftime("%Y-%m-%d"),
                correlations=results,
                summary=summary,
                data_range=f"{history.start_date} 至 {history.end_date}"
            )
            
        except Exception as e:
            logger.error("Failed to calculate correlation", error=str(e))
            return CorrelationAnalysis(
                analysis_date=datetime.now().strftime("%Y-%m-%d"),
                correlations=[],
                summary=f"计算出错: {str(e)}",
                data_range=""
            )

    async def get_sector_flow_history(self, days: int = 5) -> Dict[str, List[float]]:
        """获取板块资金流向历史（简化版，用于趋势分析）"""
        # 暂时保留，因为任务主要关注整体北向资金持久化
        logger.debug("Sector flow history not implemented, returning empty")
        return {}

    # ============ 盘中实时流向 ============

    def _is_trading_hours(self) -> bool:
        """判断当前是否在交易时段"""
        now = datetime.now()
        # 交易日判断（简化：非周末）
        if now.weekday() >= 5:
            return False

        current_time = now.time()
        # 上午盘 9:30 - 11:30，下午盘 13:00 - 15:00
        morning_start = TimeType(9, 30)
        morning_end = TimeType(11, 30)
        afternoon_start = TimeType(13, 0)
        afternoon_end = TimeType(15, 0)

        return (
            (morning_start <= current_time <= morning_end) or
            (afternoon_start <= current_time <= afternoon_end)
        )

    async def get_intraday_flow(self) -> IntradayFlowSummary:
        """获取盘中分时北向资金流向

        使用 AkShare 的分钟级数据（如可用），否则返回当前累计。
        """
        cache_key = "intraday_flow"
        # 盘中数据缓存时间较短（1分钟）
        cached = cache_service.get_sync(cache_key)
        if cached:
            return cached

        try:
            # 尝试获取分时数据
            df = await asyncio.to_thread(ak.stock_hsgt_north_min_em)

            flow_points = []
            cumulative = 0.0

            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    try:
                        time_str = str(row.get('时间', ''))[-5:]  # 取 HH:MM
                        sh = float(row.get('沪股通', 0) or 0)
                        sz = float(row.get('深股通', 0) or 0)
                        total = sh + sz
                        cumulative = float(row.get('北向资金', cumulative) or cumulative)

                        flow_points.append(IntradayFlowPoint(
                            time=time_str,
                            sh_connect=round(sh, 2),
                            sz_connect=round(sz, 2),
                            total=round(total, 2),
                            cumulative_total=round(cumulative, 2),
                        ))
                    except Exception:
                        continue

            # 计算统计指标
            if flow_points:
                totals = [p.cumulative_total for p in flow_points]
                peak_inflow = max(totals)
                peak_outflow = min(totals)
                volatility = statistics.stdev(totals) if len(totals) > 1 else 0

                # 计算动量（最近 5 个点的趋势）
                recent = totals[-5:] if len(totals) >= 5 else totals
                if len(recent) >= 2:
                    slope = recent[-1] - recent[0]
                    if slope > 5:
                        momentum = "accelerating"
                    elif slope < -5:
                        momentum = "decelerating"
                    else:
                        momentum = "stable"
                else:
                    momentum = "stable"
            else:
                peak_inflow = 0
                peak_outflow = 0
                volatility = 0
                momentum = "stable"
                cumulative = 0

            result = IntradayFlowSummary(
                date=datetime.now().date(),
                last_update=datetime.now().strftime("%H:%M:%S"),
                current_total=round(cumulative, 2),
                flow_points=flow_points,
                peak_inflow=round(peak_inflow, 2),
                peak_outflow=round(peak_outflow, 2),
                flow_volatility=round(volatility, 2),
                momentum=momentum,
            )

            cache_service.set_sync(cache_key, result, ttl=60)
            return result

        except Exception as e:
            logger.warning("Failed to fetch intraday flow, using fallback", error=str(e))
            # 降级：使用当日总流向
            today = await self.get_north_money_flow()
            return IntradayFlowSummary(
                date=datetime.now().date(),
                last_update=datetime.now().strftime("%H:%M:%S"),
                current_total=today.total,
                flow_points=[],
                peak_inflow=max(0, today.total),
                peak_outflow=min(0, today.total),
                flow_volatility=0,
                momentum="stable",
            )

    # ============ 异常检测 ============

    async def detect_anomalies(self) -> List[NorthMoneyAnomaly]:
        """检测北向资金异常流动

        检测规则：
        1. 突然大额流入/流出（单日超过 100 亿）
        2. 流向反转（连续多日后方向突变）
        3. 盘中剧烈波动（波动率超阈值）
        4. 个股异常集中（单一股票占比过高）
        """
        anomalies = []

        try:
            # 获取基础数据
            today_flow = await self.get_north_money_flow()
            history = await self.get_north_money_history(days=10)
            intraday = await self.get_intraday_flow()
            top_buys = await self.get_top_north_buys(limit=5)

            now = datetime.now()

            # 规则 1: 大额流入/流出
            if abs(today_flow.total) > 100:
                anomaly_type = "sudden_inflow" if today_flow.total > 0 else "sudden_outflow"
                severity = "critical" if abs(today_flow.total) > 150 else "high"
                direction = "流入" if today_flow.total > 0 else "流出"

                anomalies.append(NorthMoneyAnomaly(
                    timestamp=now,
                    anomaly_type=anomaly_type,
                    severity=severity,
                    description=f"北向资金单日大额{direction} {abs(today_flow.total):.1f} 亿元",
                    affected_stocks=[s.name for s in top_buys[:3]],
                    flow_change=today_flow.total,
                    recommendation=f"{'关注机构重仓股机会' if today_flow.total > 0 else '警惕市场回调风险'}",
                ))

            # 规则 2: 流向反转
            if len(history) >= 5:
                recent_5d = [h.total for h in history[-5:]]
                prev_direction = sum(recent_5d[:-1]) / 4  # 前4天平均
                today_direction = recent_5d[-1]

                # 前4天单边，今天反转
                if (prev_direction > 20 and today_direction < -20) or \
                   (prev_direction < -20 and today_direction > 20):
                    anomalies.append(NorthMoneyAnomaly(
                        timestamp=now,
                        anomaly_type="reversal",
                        severity="high",
                        description=f"北向资金流向突然反转：前4日平均{prev_direction:+.1f}亿 → 今日{today_direction:+.1f}亿",
                        affected_stocks=[],
                        flow_change=today_direction - prev_direction,
                        recommendation="关注市场风格切换，适当调整持仓结构",
                    ))

            # 规则 3: 盘中剧烈波动
            if intraday.flow_volatility > 30:
                anomalies.append(NorthMoneyAnomaly(
                    timestamp=now,
                    anomaly_type="volume_spike",
                    severity="medium",
                    description=f"盘中资金流向波动剧烈（波动率: {intraday.flow_volatility:.1f}）",
                    affected_stocks=[],
                    flow_change=intraday.peak_inflow - intraday.peak_outflow,
                    recommendation="短线波动加大，避免追涨杀跌",
                ))

            # 规则 4: 个股集中度异常
            if top_buys and today_flow.total != 0:
                top1_ratio = abs(top_buys[0].net_buy / today_flow.total) if today_flow.total else 0
                if top1_ratio > 0.3:  # 单一个股占比超过 30%
                    anomalies.append(NorthMoneyAnomaly(
                        timestamp=now,
                        anomaly_type="concentration",
                        severity="medium",
                        description=f"资金高度集中于 {top_buys[0].name}，占比 {top1_ratio*100:.1f}%",
                        affected_stocks=[top_buys[0].name],
                        flow_change=top_buys[0].net_buy,
                        recommendation=f"密切关注 {top_buys[0].name} 走势，警惕筹码集中风险",
                    ))

            return anomalies

        except Exception as e:
            logger.error("Failed to detect anomalies", error=str(e))
            return []

    # ============ 实时全景 API ============

    async def get_realtime_panorama(self) -> NorthMoneyRealtime:
        """获取北向资金实时全景数据

        整合所有北向资金相关数据，适合前端仪表盘使用。
        """
        is_trading = self._is_trading_hours()

        # 并行获取所有数据
        if is_trading:
            summary, intraday, anomalies = await asyncio.gather(
                self.get_summary(),
                self.get_intraday_flow(),
                self.detect_anomalies(),
            )
        else:
            summary, anomalies = await asyncio.gather(
                self.get_summary(),
                self.detect_anomalies(),
            )
            intraday = None

        # 计算与指数相关性（简化版，需要指数数据支持）
        index_correlation = None
        try:
            history = await self.get_north_money_history(days=20)
            if len(history) >= 10:
                # 接入指数数据计算相关性
                corr_analysis = await self.calculate_correlation(days=20)
                if corr_analysis.correlations:
                    index_correlation = {
                        c.index_name: c.correlation for c in corr_analysis.correlations
                    }
        except Exception:
            pass

        return NorthMoneyRealtime(
            summary=summary,
            intraday=intraday,
            anomalies=anomalies,
            index_correlation=index_correlation,
            is_trading_hours=is_trading,
        )


# 单例实例
north_money_service = NorthMoneyService()
