"""API Schema 定义模块

所有 API 响应的 Pydantic 模型定义，用于：
1. FastAPI 自动生成 OpenAPI schema
2. 前端通过 openapi-typescript 自动生成 TypeScript 类型
3. 运行时数据验证
"""

from .macro import (
    MacroIndicator,
    MacroOverview,
    MacroImpact,
    MacroAnalysisResult,
)
from .analysis import (
    # 枚举类型
    SignalType,
    AlertLevel,
    VisualStyle,
    VolatilityStatus,
    RiskVerdict,
    DebateWinner,
    TrendDirection,
    # 基础模型
    DebatePoint,
    ResearcherDebate,
    RiskAssessment,
    TechnicalIndicators,
    TradeSetup,
    NewsItem,
    PeerData,
    CatalystEvent,
    PriceLevels,
    MacroContext,
    WebSource,
    # A股市场专用
    RetailSentimentAnalysis,
    PolicyAnalysis,
    ChinaMarketAnalysis,
    # UI Hints
    DebateDisplay,
    UIHints,
    # 诊断信息
    AnalysisDiagnostics,
    # 完整报告
    FullReport,
    # API 响应模型
    AgentAnalysisResponse,
    AnalysisHistoryItem,
    AnalysisHistoryResponse,
    AnalysisDetailResponse,
    AnalysisTaskStatus,
)

from .chat import ChatMessage, ChatResponse

from .alternative import (
    AHPremiumStock,
    AHPremiumStats,
    AHPremiumListResponse,
    ArbitrageSignal,
    AHPremiumHistoryPoint,
    AHPremiumDetailResponse,
    PatentNewsItem,
    PatentAnalysisResponse,
)

from .vision import (
    VisionKeyDataPoint,
    VisionAnalysisResult,
    VisionAnalysisResponse,
)

from .supply_chain import (
    ChainSegmentCounts,
    ChainSummary,
    ChainListResponse,
    GraphNode,
    GraphEdge,
    ChainGraphStats,
    ChainGraphResponse,
    ChainPosition,
    StockChainPositionResponse,
    SupplyChainImpactAnalysis,
    SupplyChainImpact,
    SupplyChainImpactResponse,
)

__all__ = [
    # 枚举
    "SignalType",
    "AlertLevel",
    "VisualStyle",
    "VolatilityStatus",
    "RiskVerdict",
    "DebateWinner",
    "TrendDirection",
    # 基础模型
    "DebatePoint",
    "ResearcherDebate",
    "RiskAssessment",
    "TechnicalIndicators",
    "TradeSetup",
    "NewsItem",
    "PeerData",
    "CatalystEvent",
    "PriceLevels",
    "MacroContext",
    "WebSource",
    # A股
    "RetailSentimentAnalysis",
    "PolicyAnalysis",
    "ChinaMarketAnalysis",
    # UI
    "DebateDisplay",
    "UIHints",
    # 诊断
    "AnalysisDiagnostics",
    # 报告
    "FullReport",
    # 响应
    "AgentAnalysisResponse",
    "AnalysisHistoryItem",
    "AnalysisHistoryResponse",
    "AnalysisDetailResponse",
    "AnalysisTaskStatus",
    # Macro
    "MacroIndicator",
    "MacroOverview",
    "MacroImpact",
    "MacroAnalysisResult",
    # Chat
    "ChatMessage",
    "ChatResponse",
    # Alternative Data
    "AHPremiumStock",
    "AHPremiumStats",
    "AHPremiumListResponse",
    "ArbitrageSignal",
    "AHPremiumHistoryPoint",
    "AHPremiumDetailResponse",
    "PatentNewsItem",
    "PatentAnalysisResponse",
    # Vision
    "VisionKeyDataPoint",
    "VisionAnalysisResult",
    "VisionAnalysisResponse",
    # Supply Chain
    "ChainSegmentCounts",
    "ChainSummary",
    "ChainListResponse",
    "GraphNode",
    "GraphEdge",
    "ChainGraphStats",
    "ChainGraphResponse",
    "ChainPosition",
    "StockChainPositionResponse",
    "SupplyChainImpactAnalysis",
    "SupplyChainImpact",
    "SupplyChainImpactResponse",
]
