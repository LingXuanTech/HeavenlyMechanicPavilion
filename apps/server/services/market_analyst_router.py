"""
Market-based Analyst Router

根据股票市场类型（A股/港股/美股）智能选择最适合的 Analyst 组合，
支持用户自定义覆盖和动态配置。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set
import structlog

logger = structlog.get_logger(__name__)


class Market(str, Enum):
    """市场类型"""
    CN = "CN"   # A股（上海/深圳）
    HK = "HK"   # 港股
    US = "US"   # 美股
    UNKNOWN = "UNKNOWN"


class AnalystType(str, Enum):
    """分析师类型"""
    # 基础分析师（所有市场通用）
    MARKET = "market"             # 技术分析
    FUNDAMENTALS = "fundamentals"  # 基本面分析
    NEWS = "news"                 # 新闻分析
    SOCIAL = "social"             # 社交媒体分析

    # 高级分析师（市场特定）
    SENTIMENT = "sentiment"       # 散户情绪分析（FOMO/FUD 检测）
    POLICY = "policy"             # 政策分析（A股特有）
    FUND_FLOW = "fund_flow"       # 资金流向分析（北向资金+龙虎榜）


@dataclass
class AnalystConfig:
    """分析师配置"""
    analysts: List[str]  # 启用的分析师列表
    description: str     # 配置描述
    priority_order: List[str] = field(default_factory=list)  # 优先级顺序（可选）


# 市场默认分析师配置
MARKET_ANALYST_PRESETS: Dict[Market, AnalystConfig] = {
    Market.CN: AnalystConfig(
        analysts=[
            AnalystType.MARKET.value,
            AnalystType.FUNDAMENTALS.value,
            AnalystType.NEWS.value,
            AnalystType.SOCIAL.value,
            AnalystType.SENTIMENT.value,
            AnalystType.POLICY.value,
            AnalystType.FUND_FLOW.value,
        ],
        description="A股市场：完整分析师团队，包括政策分析、资金流向（北向+龙虎榜）",
        priority_order=["policy", "fund_flow", "market", "fundamentals", "news", "sentiment", "social"],
    ),
    Market.HK: AnalystConfig(
        analysts=[
            AnalystType.MARKET.value,
            AnalystType.FUNDAMENTALS.value,
            AnalystType.NEWS.value,
            AnalystType.SOCIAL.value,
            AnalystType.SENTIMENT.value,
        ],
        description="港股市场：标准分析师 + 散户情绪（港股受 A股情绪影响）",
        priority_order=["market", "fundamentals", "news", "sentiment", "social"],
    ),
    Market.US: AnalystConfig(
        analysts=[
            AnalystType.MARKET.value,
            AnalystType.FUNDAMENTALS.value,
            AnalystType.NEWS.value,
            AnalystType.SOCIAL.value,
        ],
        description="美股市场：标准分析师团队",
        priority_order=["market", "fundamentals", "news", "social"],
    ),
    Market.UNKNOWN: AnalystConfig(
        analysts=[
            AnalystType.MARKET.value,
            AnalystType.FUNDAMENTALS.value,
            AnalystType.NEWS.value,
            AnalystType.SOCIAL.value,
        ],
        description="未知市场：使用基础分析师团队",
        priority_order=["market", "fundamentals", "news", "social"],
    ),
}


class MarketAnalystRouter:
    """市场智能分析师路由器

    根据 symbol 自动检测市场类型，返回最适合的 Analyst 组合。
    支持用户自定义覆盖。
    """

    # Symbol 后缀到市场的映射
    SUFFIX_MARKET_MAP = {
        ".SH": Market.CN,  # 上海
        ".SZ": Market.CN,  # 深圳
        ".SS": Market.CN,  # 上海（Yahoo Finance 格式）
        ".HK": Market.HK,  # 港股
    }

    @classmethod
    def detect_market(cls, symbol: str) -> Market:
        """根据 symbol 检测市场类型

        Args:
            symbol: 股票代码，如 "600519.SH", "00700.HK", "AAPL"

        Returns:
            Market 枚举值
        """
        symbol_upper = symbol.upper()

        # 检查后缀
        for suffix, market in cls.SUFFIX_MARKET_MAP.items():
            if symbol_upper.endswith(suffix):
                return market

        # A股代码格式（纯数字 6 位）
        clean_symbol = symbol_upper.split(".")[0]
        if clean_symbol.isdigit() and len(clean_symbol) == 6:
            # 6/9 开头 -> 上海，0/3 开头 -> 深圳
            if clean_symbol[0] in ("6", "9"):
                return Market.CN
            elif clean_symbol[0] in ("0", "3"):
                return Market.CN

        # 港股代码格式（纯数字 5 位）
        if clean_symbol.isdigit() and len(clean_symbol) == 5:
            return Market.HK

        # 默认美股
        return Market.US

    @classmethod
    def get_analysts_by_market(cls, market: Market) -> List[str]:
        """根据 Market 枚举直接获取分析师列表

        Args:
            market: Market 枚举值

        Returns:
            分析师类型列表
        """
        preset = MARKET_ANALYST_PRESETS.get(market, MARKET_ANALYST_PRESETS[Market.UNKNOWN])
        return list(preset.analysts)

    @classmethod
    def get_analysts(
        cls,
        symbol: str,
        override_analysts: Optional[List[str]] = None,
        exclude_analysts: Optional[List[str]] = None,
        include_analysts: Optional[List[str]] = None,
    ) -> List[str]:
        """获取指定 symbol 的推荐分析师列表

        Args:
            symbol: 股票代码
            override_analysts: 完全覆盖默认配置（如果提供）
            exclude_analysts: 从默认配置中排除的分析师
            include_analysts: 额外添加到默认配置的分析师

        Returns:
            分析师类型列表
        """
        # 用户完全覆盖
        if override_analysts:
            logger.info("Using override analysts", symbol=symbol, analysts=override_analysts)
            return cls._validate_analysts(override_analysts)

        # 检测市场
        market = cls.detect_market(symbol)
        preset = MARKET_ANALYST_PRESETS.get(market, MARKET_ANALYST_PRESETS[Market.UNKNOWN])

        # 基于预设构建列表
        analysts = set(preset.analysts)

        # 排除指定分析师
        if exclude_analysts:
            for analyst in exclude_analysts:
                analysts.discard(analyst)
            logger.info("Excluded analysts", symbol=symbol, excluded=exclude_analysts)

        # 添加额外分析师
        if include_analysts:
            valid_extra = cls._validate_analysts(include_analysts)
            analysts.update(valid_extra)
            logger.info("Included extra analysts", symbol=symbol, included=valid_extra)

        result = list(analysts)
        logger.info(
            "Analysts selected",
            symbol=symbol,
            market=market.value,
            analysts=result,
            preset_description=preset.description,
        )

        return result

    @classmethod
    def get_market_config(cls, symbol: str) -> Dict:
        """获取完整的市场配置信息

        Args:
            symbol: 股票代码

        Returns:
            包含市场类型、分析师列表、描述等的配置字典
        """
        market = cls.detect_market(symbol)
        preset = MARKET_ANALYST_PRESETS.get(market, MARKET_ANALYST_PRESETS[Market.UNKNOWN])

        return {
            "market": market.value,
            "symbol": symbol,
            "analysts": preset.analysts,
            "description": preset.description,
            "priority_order": preset.priority_order,
            "all_available_analysts": [a.value for a in AnalystType],
        }

    @classmethod
    def get_available_analysts(cls) -> List[Dict]:
        """获取所有可用的分析师及其描述

        Returns:
            分析师列表，每项包含 name, description, markets
        """
        analyst_info = {
            AnalystType.MARKET: {
                "name": "market",
                "display_name": "技术分析师",
                "description": "K线形态识别、RSI/MACD 等技术指标分析",
                "markets": ["CN", "HK", "US"],
            },
            AnalystType.FUNDAMENTALS: {
                "name": "fundamentals",
                "display_name": "基本面分析师",
                "description": "财报解析、估值模型、行业催化剂分析",
                "markets": ["CN", "HK", "US"],
            },
            AnalystType.NEWS: {
                "name": "news",
                "display_name": "新闻分析师",
                "description": "财经新闻、公告、事件驱动分析",
                "markets": ["CN", "HK", "US"],
            },
            AnalystType.SOCIAL: {
                "name": "social",
                "display_name": "社交媒体分析师",
                "description": "Twitter/Reddit/雪球 等社交媒体热度监控",
                "markets": ["CN", "HK", "US"],
            },
            AnalystType.SENTIMENT: {
                "name": "sentiment",
                "display_name": "散户情绪分析师",
                "description": "FOMO/FUD 检测、逆向信号生成",
                "markets": ["CN", "HK"],
            },
            AnalystType.POLICY: {
                "name": "policy",
                "display_name": "政策分析师",
                "description": "央行/证监会/发改委 政策解读、行业规划",
                "markets": ["CN"],
            },
            AnalystType.FUND_FLOW: {
                "name": "fund_flow",
                "display_name": "资金流向分析师",
                "description": "北向资金、龙虎榜、游资动向追踪",
                "markets": ["CN"],
            },
        }

        return [analyst_info[a] for a in AnalystType]

    @classmethod
    def _validate_analysts(cls, analysts: List[str]) -> List[str]:
        """验证分析师列表，过滤无效值

        Args:
            analysts: 待验证的分析师列表

        Returns:
            验证后的有效分析师列表
        """
        valid_analysts = {a.value for a in AnalystType}
        result = []
        invalid = []

        for analyst in analysts:
            if analyst in valid_analysts:
                result.append(analyst)
            else:
                invalid.append(analyst)

        if invalid:
            logger.warning("Invalid analysts filtered out", invalid=invalid)

        return result


# 单例实例
market_analyst_router = MarketAnalystRouter()
