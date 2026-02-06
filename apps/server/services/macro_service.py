"""宏观经济数据服务"""
import structlog
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import httpx
from functools import lru_cache
import asyncio

from config.settings import settings
from services.cache_service import cache_service

logger = structlog.get_logger()


class MacroIndicator(BaseModel):
    """宏观经济指标"""
    name: str
    value: float
    previous_value: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    unit: str = ""
    date: str
    source: str
    trend: str = "stable"  # up, down, stable


class MacroOverview(BaseModel):
    """宏观经济概览"""
    fed_rate: Optional[MacroIndicator] = None
    gdp_growth: Optional[MacroIndicator] = None
    cpi: Optional[MacroIndicator] = None
    unemployment: Optional[MacroIndicator] = None
    pmi: Optional[MacroIndicator] = None
    treasury_10y: Optional[MacroIndicator] = None
    vix: Optional[MacroIndicator] = None
    dxy: Optional[MacroIndicator] = None
    sentiment: str = "Neutral"
    summary: str = ""
    last_updated: str = ""


class MacroImpact(BaseModel):
    """宏观因素对市场的影响评估"""
    indicator: str
    impact_level: str  # High, Medium, Low
    direction: str  # Bullish, Bearish, Neutral
    reasoning: str


class MacroAnalysisResult(BaseModel):
    """宏观分析结果"""
    overview: MacroOverview
    impacts: List[MacroImpact]
    market_outlook: str
    risk_factors: List[str]
    opportunities: List[str]




class MacroDataService:
    """
    宏观经济数据服务

    数据源：
    - FRED (Federal Reserve Economic Data) - 美国经济数据
    - 世界银行 API
    - Yahoo Finance (VIX, DXY)
    """

    # FRED API 指标代码
    FRED_INDICATORS = {
        "fed_rate": "FEDFUNDS",  # 联邦基金利率
        "gdp_growth": "A191RL1Q225SBEA",  # 实际GDP增长率
        "cpi": "CPIAUCSL",  # 消费者价格指数
        "unemployment": "UNRATE",  # 失业率
        "treasury_10y": "DGS10",  # 10年期国债收益率
        "pmi": "MANEMP",  # 制造业就业 (PMI proxy)
    }

    @classmethod
    async def _fetch_fred_data(cls, series_id: str) -> Optional[Dict]:
        """从 FRED API 获取数据"""
        api_key = settings.FRED_API_KEY
        if not api_key:
            logger.warning("FRED API key not configured")
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"https://api.stlouisfed.org/fred/series/observations"
                params = {
                    "series_id": series_id,
                    "api_key": api_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 2,  # 获取最近两个数据点用于计算变化
                }
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                if "observations" in data and len(data["observations"]) > 0:
                    return data["observations"]
                return None

        except Exception as e:
            logger.warning("FRED API request failed", series_id=series_id, error=str(e))
            return None

    @classmethod
    async def _fetch_vix(cls) -> Optional[MacroIndicator]:
        """获取 VIX 恐慌指数"""
        try:
            import yfinance as yf
            vix = yf.Ticker("^VIX")
            info = vix.fast_info

            value = info.get("last_price", 0)
            prev = info.get("previous_close", value)

            trend = "stable"
            if value > prev * 1.05:
                trend = "up"
            elif value < prev * 0.95:
                trend = "down"

            return MacroIndicator(
                name="VIX (恐慌指数)",
                value=round(value, 2),
                previous_value=round(prev, 2),
                change=round(value - prev, 2),
                change_percent=round((value / prev - 1) * 100, 2) if prev else 0,
                unit="",
                date=datetime.now().strftime("%Y-%m-%d"),
                source="Yahoo Finance",
                trend=trend
            )
        except Exception as e:
            logger.warning("Failed to fetch VIX", error=str(e))
            return None

    @classmethod
    async def _fetch_dxy(cls) -> Optional[MacroIndicator]:
        """获取美元指数"""
        try:
            import yfinance as yf
            dxy = yf.Ticker("DX-Y.NYB")
            info = dxy.fast_info

            value = info.get("last_price", 0)
            prev = info.get("previous_close", value)

            trend = "stable"
            if value > prev * 1.005:
                trend = "up"
            elif value < prev * 0.995:
                trend = "down"

            return MacroIndicator(
                name="DXY (美元指数)",
                value=round(value, 2),
                previous_value=round(prev, 2),
                change=round(value - prev, 2),
                change_percent=round((value / prev - 1) * 100, 2) if prev else 0,
                unit="",
                date=datetime.now().strftime("%Y-%m-%d"),
                source="Yahoo Finance",
                trend=trend
            )
        except Exception as e:
            logger.warning("Failed to fetch DXY", error=str(e))
            return None

    @classmethod
    async def get_macro_overview(cls) -> MacroOverview:
        """获取宏观经济概览"""

        # 检查缓存
        cached = cache_service.get_sync("macro_overview")
        if cached:
            logger.debug("Using cached macro overview")
            return cached

        overview = MacroOverview(last_updated=datetime.now().isoformat())

        # 并行获取各项指标
        tasks = []

        # FRED 数据
        for indicator_name, series_id in cls.FRED_INDICATORS.items():
            tasks.append(cls._fetch_fred_indicator(indicator_name, series_id))

        # 市场数据
        tasks.append(cls._fetch_vix())
        tasks.append(cls._fetch_dxy())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理 FRED 结果
        fred_results = results[:len(cls.FRED_INDICATORS)]
        for indicator_name, result in zip(cls.FRED_INDICATORS.keys(), fred_results):
            if isinstance(result, MacroIndicator):
                setattr(overview, indicator_name, result)

        # 处理 VIX 和 DXY
        if isinstance(results[-2], MacroIndicator):
            overview.vix = results[-2]
        if isinstance(results[-1], MacroIndicator):
            overview.dxy = results[-1]

        # 生成整体情绪
        overview.sentiment = cls._calculate_sentiment(overview)
        overview.summary = cls._generate_summary(overview)

        # 缓存结果
        cache_service.set_sync("macro_overview", overview, ttl=3600)

        return overview

    @classmethod
    async def _fetch_fred_indicator(cls, name: str, series_id: str) -> Optional[MacroIndicator]:
        """获取单个 FRED 指标"""
        data = await cls._fetch_fred_data(series_id)
        if not data:
            return None

        try:
            latest = data[0]
            value = float(latest["value"]) if latest["value"] != "." else 0

            previous_value = None
            change = None
            change_percent = None

            if len(data) > 1 and data[1]["value"] != ".":
                previous_value = float(data[1]["value"])
                change = value - previous_value
                change_percent = (change / previous_value * 100) if previous_value else 0

            trend = "stable"
            if change and change > 0:
                trend = "up"
            elif change and change < 0:
                trend = "down"

            # 指标名称映射
            name_map = {
                "fed_rate": "联邦基金利率",
                "gdp_growth": "GDP增长率",
                "cpi": "CPI",
                "unemployment": "失业率",
                "treasury_10y": "10年期国债",
                "pmi": "制造业PMI",
            }

            unit_map = {
                "fed_rate": "%",
                "gdp_growth": "%",
                "cpi": "",
                "unemployment": "%",
                "treasury_10y": "%",
                "pmi": "",
            }

            return MacroIndicator(
                name=name_map.get(name, name),
                value=round(value, 2),
                previous_value=round(previous_value, 2) if previous_value else None,
                change=round(change, 2) if change else None,
                change_percent=round(change_percent, 2) if change_percent else None,
                unit=unit_map.get(name, ""),
                date=latest["date"],
                source="FRED",
                trend=trend
            )
        except Exception as e:
            logger.warning("Failed to parse FRED data", name=name, error=str(e))
            return None

    @classmethod
    def _calculate_sentiment(cls, overview: MacroOverview) -> str:
        """根据宏观指标计算整体情绪"""
        bullish_signals = 0
        bearish_signals = 0

        # 低利率 = 利好
        if overview.fed_rate and overview.fed_rate.value < 3:
            bullish_signals += 1
        elif overview.fed_rate and overview.fed_rate.value > 5:
            bearish_signals += 1

        # GDP 增长 = 利好
        if overview.gdp_growth and overview.gdp_growth.value > 2:
            bullish_signals += 1
        elif overview.gdp_growth and overview.gdp_growth.value < 0:
            bearish_signals += 2

        # 低失业率 = 利好
        if overview.unemployment and overview.unemployment.value < 4:
            bullish_signals += 1
        elif overview.unemployment and overview.unemployment.value > 6:
            bearish_signals += 1

        # 低 VIX = 利好
        if overview.vix and overview.vix.value < 15:
            bullish_signals += 1
        elif overview.vix and overview.vix.value > 25:
            bearish_signals += 1

        # 判断情绪
        if bullish_signals > bearish_signals + 1:
            return "Bullish"
        elif bearish_signals > bullish_signals + 1:
            return "Bearish"
        return "Neutral"

    @classmethod
    def _generate_summary(cls, overview: MacroOverview) -> str:
        """生成宏观概要"""
        parts = []

        if overview.fed_rate:
            parts.append(f"联邦基金利率 {overview.fed_rate.value}%")

        if overview.gdp_growth:
            parts.append(f"GDP增长 {overview.gdp_growth.value}%")

        if overview.vix:
            level = "低" if overview.vix.value < 15 else ("高" if overview.vix.value > 25 else "中等")
            parts.append(f"VIX {level}({overview.vix.value})")

        if parts:
            return "当前宏观环境：" + "，".join(parts)
        return "宏观数据暂不可用"

    @classmethod
    async def clear_cache(cls):
        """清除缓存"""
        await cache_service.delete("macro_overview")
        logger.info("Macro data cache cleared")
