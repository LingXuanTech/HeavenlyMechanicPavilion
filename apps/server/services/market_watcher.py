"""市场指数监控服务 - 定期获取全球主要市场指数"""
import asyncio
import structlog
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    ak = None

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    yf = None

from config.settings import settings
from services.cache_service import cache_service

logger = structlog.get_logger()


class MarketRegion(str, Enum):
    """市场区域"""
    CN = "CN"  # 中国大陆
    HK = "HK"  # 香港
    US = "US"  # 美国
    GLOBAL = "GLOBAL"  # 全球


class IndexStatus(str, Enum):
    """指数状态"""
    TRADING = "trading"
    CLOSED = "closed"
    PRE_MARKET = "pre_market"
    AFTER_HOURS = "after_hours"
    UNKNOWN = "unknown"


class MarketIndex(BaseModel):
    """市场指数数据"""
    code: str
    name: str
    name_en: str
    region: MarketRegion
    current: float
    change: float
    change_percent: float
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    prev_close: Optional[float] = None
    volume: Optional[float] = None
    status: IndexStatus = IndexStatus.UNKNOWN
    updated_at: datetime


class MarketOverview(BaseModel):
    """市场概览"""
    indices: List[MarketIndex]
    global_sentiment: str  # Bullish / Bearish / Neutral
    risk_level: int  # 1-5
    updated_at: datetime


# 主要市场指数配置
MARKET_INDICES = {
    # 中国大陆
    "000001.SS": {"name": "上证指数", "name_en": "SSE Composite", "region": MarketRegion.CN, "ak_code": "sh000001"},
    "399001.SZ": {"name": "深证成指", "name_en": "SZSE Component", "region": MarketRegion.CN, "ak_code": "sz399001"},
    "399006.SZ": {"name": "创业板指", "name_en": "ChiNext", "region": MarketRegion.CN, "ak_code": "sz399006"},

    # 香港
    "^HSI": {"name": "恒生指数", "name_en": "Hang Seng", "region": MarketRegion.HK},
    "^HSCE": {"name": "恒生中国企业", "name_en": "Hang Seng China", "region": MarketRegion.HK},

    # 美国
    "^DJI": {"name": "道琼斯工业", "name_en": "Dow Jones", "region": MarketRegion.US},
    "^GSPC": {"name": "标普500", "name_en": "S&P 500", "region": MarketRegion.US},
    "^IXIC": {"name": "纳斯达克", "name_en": "NASDAQ", "region": MarketRegion.US},
}


class MarketWatcherService:
    """
    市场监控服务

    功能：
    1. 定期获取全球主要市场指数
    2. 计算市场情绪
    3. 提供实时数据 API
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._initialized = getattr(self, '_initialized', False)
        if not self._initialized:
            self._initialized = True
            logger.info("MarketWatcherService initialized")

    async def _fetch_cn_indices(self) -> List[MarketIndex]:
        """获取 A 股指数（使用 akshare）"""
        if not AKSHARE_AVAILABLE:
            logger.warning("akshare not available, skipping CN indices")
            return []

        indices = []
        now = datetime.now()

        try:
            # 使用 asyncio.to_thread 避免阻塞事件循环，并设置超时
            df = await asyncio.wait_for(
                asyncio.to_thread(ak.stock_zh_index_spot_sina),
                timeout=15.0
            )

            for code, config in MARKET_INDICES.items():
                if config["region"] != MarketRegion.CN:
                    continue

                try:
                    ak_code = config.get("ak_code", "")
                    if not ak_code:
                        continue

                    # stock_zh_index_spot_sina 代码列含前缀如 sh000001
                    row = df[df['代码'] == ak_code]

                    if not row.empty:
                        row = row.iloc[0]
                        current = float(row['最新价'])
                        change = float(row['涨跌额'])
                        change_percent = float(row['涨跌幅'])

                        indices.append(MarketIndex(
                            code=code,
                            name=config["name"],
                            name_en=config["name_en"],
                            region=config["region"],
                            current=round(current, 2),
                            change=round(change, 2),
                            change_percent=round(change_percent, 2),
                            volume=float(row.get('成交量', 0)) if row.get('成交量') else None,
                            status=IndexStatus.TRADING,
                            updated_at=now
                        ))

                except Exception as e:
                    logger.warning(f"Failed to fetch CN index {code}", error=str(e))

        except Exception as e:
            logger.error("Failed to fetch CN indices", error=str(e))

        return indices

    async def _fetch_global_indices(self) -> List[MarketIndex]:
        """获取港股和美股指数（使用 yfinance）"""
        if not YFINANCE_AVAILABLE:
            logger.warning("yfinance not available, skipping global indices")
            return []

        indices = []
        now = datetime.now()

        global_codes = [code for code, cfg in MARKET_INDICES.items()
                        if cfg["region"] in [MarketRegion.HK, MarketRegion.US]]

        for code in global_codes:
            try:
                config = MARKET_INDICES[code]
                # yfinance 的 ticker.info 是阻塞调用，使用 to_thread + 超时保护
                ticker = yf.Ticker(code)
                info = await asyncio.wait_for(
                    asyncio.to_thread(lambda t=ticker: t.info),
                    timeout=10.0
                )

                current = info.get('regularMarketPrice') or info.get('previousClose', 0)
                prev_close = info.get('previousClose', current)
                change = current - prev_close
                change_percent = (change / prev_close * 100) if prev_close else 0

                # 判断市场状态
                market_state = info.get('marketState', 'CLOSED')
                status_map = {
                    'REGULAR': IndexStatus.TRADING,
                    'CLOSED': IndexStatus.CLOSED,
                    'PRE': IndexStatus.PRE_MARKET,
                    'POST': IndexStatus.AFTER_HOURS,
                }
                status = status_map.get(market_state, IndexStatus.UNKNOWN)

                indices.append(MarketIndex(
                    code=code,
                    name=config["name"],
                    name_en=config["name_en"],
                    region=config["region"],
                    current=round(current, 2),
                    change=round(change, 2),
                    change_percent=round(change_percent, 2),
                    high=info.get('dayHigh'),
                    low=info.get('dayLow'),
                    open=info.get('open'),
                    prev_close=prev_close,
                    volume=info.get('volume'),
                    status=status,
                    updated_at=now
                ))

            except Exception as e:
                logger.warning(f"Failed to fetch global index {code}", error=str(e))

        return indices

    async def get_all_indices(self, force_refresh: bool = False) -> List[MarketIndex]:
        """
        获取所有市场指数

        Args:
            force_refresh: 强制刷新缓存

        Returns:
            市场指数列表
        """
        cached_dict = cache_service.get_sync("indices")
        if not force_refresh and cached_dict:
            return list(cached_dict.values())

        # 并行获取各市场数据
        cn_task = asyncio.create_task(self._fetch_cn_indices())
        global_task = asyncio.create_task(self._fetch_global_indices())

        cn_indices, global_indices = await asyncio.gather(cn_task, global_task)

        all_indices = cn_indices + global_indices

        # 更新缓存
        indices_dict = {idx.code: idx for idx in all_indices}
        cache_service.set_sync("indices", indices_dict, ttl=60)

        logger.info("Market indices refreshed", count=len(all_indices))
        return all_indices

    async def get_index(self, code: str) -> Optional[MarketIndex]:
        """获取单个指数"""
        cached_dict = cache_service.get_sync("indices")
        if not cached_dict:
            await self.get_all_indices()
            cached_dict = cache_service.get_sync("indices") or {}

        return cached_dict.get(code)

    async def get_indices_by_region(self, region: MarketRegion) -> List[MarketIndex]:
        """按区域获取指数"""
        all_indices = await self.get_all_indices()
        return [idx for idx in all_indices if idx.region == region]

    def _calculate_sentiment(self, indices: List[MarketIndex]) -> str:
        """计算全球市场情绪"""
        if not indices:
            return "Neutral"

        positive = sum(1 for idx in indices if idx.change_percent > 0.5)
        negative = sum(1 for idx in indices if idx.change_percent < -0.5)
        total = len(indices)

        if positive > total * 0.6:
            return "Bullish"
        elif negative > total * 0.6:
            return "Bearish"
        else:
            return "Neutral"

    def _calculate_risk_level(self, indices: List[MarketIndex]) -> int:
        """
        计算市场风险等级 (1-5)

        考虑因素：
        - 跌幅程度
        - 下跌指数数量
        """
        if not indices:
            return 3

        avg_change = sum(idx.change_percent for idx in indices) / len(indices)
        negative_count = sum(1 for idx in indices if idx.change_percent < 0)
        negative_ratio = negative_count / len(indices)

        # 基础风险
        risk = 3

        # 根据平均涨跌幅调整
        if avg_change < -3:
            risk = 5
        elif avg_change < -1.5:
            risk = 4
        elif avg_change > 1.5:
            risk = 2
        elif avg_change > 3:
            risk = 1

        # 根据下跌比例微调
        if negative_ratio > 0.7:
            risk = min(5, risk + 1)
        elif negative_ratio < 0.3:
            risk = max(1, risk - 1)

        return risk

    async def get_market_overview(self) -> MarketOverview:
        """获取市场概览"""
        indices = await self.get_all_indices()

        return MarketOverview(
            indices=indices,
            global_sentiment=self._calculate_sentiment(indices),
            risk_level=self._calculate_risk_level(indices),
            updated_at=datetime.now()
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计"""
        cached_dict = cache_service.get_sync("indices") or {}
        return {
            "status": "available",
            "akshare_available": AKSHARE_AVAILABLE,
            "yfinance_available": YFINANCE_AVAILABLE,
            "cached_indices": len(cached_dict),
            "cache_valid": cached_dict is not None,
        }


# 全局单例
market_watcher = MarketWatcherService()
