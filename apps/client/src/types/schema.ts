/**
 * 前端类型定义中心
 *
 * 所有类型都从 OpenAPI 自动生成的 generated/ 目录导出
 * 不再手动定义类型，确保前后端类型同步
 */

import { paths, components } from './generated';

// ============ 辅助类型 ============

/**
 * 从 OpenAPI 路径中提取响应类型
 */
export type ApiResponse<T extends keyof paths, M extends keyof paths[T] & string = 'get'> =
  paths[T][M] extends { responses: { 200: { content: { 'application/json': infer R } } } }
    ? R
    : never;

/**
 * 从 OpenAPI 路径中提取请求参数类型
 */
export type ApiRequestParams<T extends keyof paths, M extends keyof paths[T] & string = 'get'> =
  paths[T][M] extends { parameters: { query?: infer Q; path?: infer P } }
    ? (Q extends undefined ? Record<string, never> : Q) & (P extends undefined ? Record<string, never> : P)
    : Record<string, never>;

/**
 * 从 OpenAPI 路径中提取请求体类型
 */
export type ApiRequestBody<T extends keyof paths, M extends keyof paths[T] & string = 'post'> =
  paths[T][M] extends { requestBody: { content: { 'application/json': infer B } } }
    ? B
    : never;

// ============ Schema 类型别名 ============
export type Schemas = components['schemas'];

// --- 分析相关 ---
export type AgentAnalysisResponse = Schemas['AgentAnalysisResponse'];
export type FullReport = Schemas['FullReport'];
export type ResearcherDebate = Schemas['ResearcherDebate'];
export type BullBearPosition = Schemas['BullBearPosition'];
export type DebatePoint = Schemas['DebatePoint'];
export type RiskAssessment = Schemas['RiskAssessment'];
export type TechnicalIndicators = Schemas['TechnicalIndicators'];
export type TradeSetup = Schemas['TradeSetup'];
export type NewsItem = Schemas['NewsItem'];
export type PeerData = Schemas['PeerData'];
export type CatalystEvent = Schemas['CatalystEvent'];
export type PriceLevels = Schemas['PriceLevels'];
export type MacroContext = Schemas['MacroContext'];
export type WebSource = Schemas['WebSource'];
export type UIHints = Schemas['UIHints'];
export type DebateDisplay = Schemas['DebateDisplay'];
export type AnalysisDiagnostics = Schemas['AnalysisDiagnostics'];
export type AnalysisHistoryItem = Schemas['AnalysisHistoryItem'];
export type AnalysisHistoryResponse = Schemas['AnalysisHistoryResponse'];
export type AnalysisDetailResponse = Schemas['AnalysisDetailResponse'];

// A股市场专用
export type RetailSentimentAnalysis = Schemas['RetailSentimentAnalysis'];
export type PolicyAnalysis = Schemas['PolicyAnalysis'];
export type ChinaMarketAnalysis = Schemas['ChinaMarketAnalysis'];

// 枚举类型
export type SignalType = Schemas['SignalType'];
export type AlertLevel = Schemas['AlertLevel'];
export type VisualStyle = Schemas['VisualStyle'];
export type VolatilityStatus = Schemas['VolatilityStatus'];
export type RiskVerdict = Schemas['RiskVerdict'];
export type DebateWinner = Schemas['DebateWinner'];
export type TrendDirection = Schemas['TrendDirection'];

// --- 北向资金 ---
export type NorthMoneySummary = Schemas['NorthMoneySummary'];
export type NorthMoneyFlow = Schemas['NorthMoneyFlow'];
export type NorthMoneyHistory = Schemas['NorthMoneyHistory'];
export type NorthMoneyTopStock = Schemas['NorthMoneyTopStock'];
export type IntradayFlowSummary = Schemas['IntradayFlowSummary'];
export type NorthMoneyAnomaly = Schemas['NorthMoneyAnomaly'];
export type NorthMoneyRealtime = Schemas['NorthMoneyRealtime'];
export type NorthMoneySectorFlow = Schemas['NorthMoneySectorFlow'];
export type SectorRotationSignal = Schemas['SectorRotationSignal'];
export type StockNorthHolding = Schemas['StockNorthHolding'];

// --- 龙虎榜 ---
export type LHBSummary = Schemas['LHBSummary'];
export type LHBStock = Schemas['LHBStock'];
export type HotMoneySeat = Schemas['HotMoneySeat'];

// --- 解禁 ---
export type JiejinSummary = Schemas['JiejinSummary'];
export type JiejinStock = Schemas['JiejinStock'];
export type JiejinCalendar = Schemas['JiejinCalendar'];

// --- 市场 ---
export type MarketRegion = Schemas['MarketRegion'];
export type MarketIndex = Schemas['MarketIndex'];
export type MarketOverview = Schemas['MarketOverview'];
export type AssetPrice = Schemas['AssetPrice'];
export type StockPrice = Schemas['StockPrice'];
export type KlineData = Schemas['KlineData'];

// --- 新闻 ---
export type NewsCategory = Schemas['NewsCategory'];
export type NewsSentiment = Schemas['NewsSentiment'];
export type NewsAggregateResult = Schemas['NewsAggregateResult'];

// --- 健康检查 ---

/**
 * 数据源状态（与后端 api/schemas/health.py ProviderStatus 对齐）
 */
export interface ProviderStatus {
  available: boolean;
  failure_count: number;
  threshold: number;
  last_failure?: string | null;
  cooldown_seconds: number;
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  avg_latency_ms: number;
  last_error?: string | null;
}

export type HealthReport = Schemas['HealthReport'] & {
  data_providers: Record<string, ProviderStatus>;
};
export type HealthStatus = Schemas['HealthStatus'];
export type SystemMetrics = Schemas['SystemMetrics'];
export type ErrorRecord = Schemas['ErrorRecord'];
export type ComponentHealth = Schemas['ComponentHealth'];
export type HealthQuickResponse = Schemas['HealthQuickResponse'];
export type ComponentHealthResponse = Schemas['ComponentHealthResponse'];
export type HealthErrorsResponse = Schemas['HealthErrorsResponse'];
export type SystemUptimeResponse = Schemas['SystemUptimeResponse'];

// --- 记忆服务 ---
export type AnalysisMemory = Schemas['AnalysisMemory'];
export type MemoryRetrievalResult = Schemas['MemoryRetrievalResult'];
export type ReflectionReport = Schemas['ReflectionReport'];

// --- 投资组合 ---
export type PortfolioAnalysis = Schemas['PortfolioAnalysis'];
export type CorrelationResult = Schemas['CorrelationResult'];

// --- 宏观 ---
export type MacroOverview = Schemas['MacroOverview'];
export type MacroIndicator = Schemas['MacroIndicator'];
export type MacroImpact = Schemas['MacroImpact'];
export type MacroAnalysisResult = Schemas['MacroAnalysisResult'];

// --- 解锁 ---
export type MarketUnlockOverview = Schemas['MarketUnlockOverview'];
export type UnlockStock = Schemas['UnlockStock'];
export type UnlockPressure = Schemas['UnlockPressure'];
export type UnlockCalendar = Schemas['UnlockCalendar'];

// --- 央行/政策 ---
export type CentralBankAnalysisResult = Schemas['CentralBankAnalysisResult'];
export type CrossAssetAnalysisResult = Schemas['CrossAssetAnalysisResult'];
export type PolicySentiment = Schemas['PolicySentiment'];
export type PolicyKeyword = Schemas['PolicyKeyword'];
export type PolicyChangeSignal = Schemas['PolicyChangeSignal'];

// --- 自选股 ---
export type Watchlist = Schemas['Watchlist'];

// --- Prompt 配置 ---
export type AgentPromptInfo = Schemas['AgentPromptInfo'];
export type AgentPromptDetail = Schemas['AgentPromptDetail'];
export type AgentCategory = Schemas['AgentCategory'];
export type PromptVersionInfo = Schemas['PromptVersionInfo'];
export type PromptListResponse = Schemas['PromptListResponse'];
export type PromptServiceStatus = Schemas['PromptServiceStatus'];

// --- AI 配置 ---
export type AIProvider = Schemas['AIProvider'];
export type AIProviderType = Schemas['AIProviderType'];
export type AIModelConfig = Schemas['AIModelConfig'];
export type AIConfigStatus = Schemas['AIConfigStatus'];
export type TestProviderResult = Schemas['TestProviderResult'];
export type ProviderListResponse = Schemas['ProviderListResponse'];
export type ModelConfigListResponse = Schemas['ModelConfigListResponse'];

// --- Chat ---
export type ChatMessage = Schemas['ChatMessage'];

// --- 分析任务 ---
export type AnalysisTaskStatus = Schemas['AnalysisTaskStatus'];

// ============ 前端专用类型（从 frontend-types.ts 导出） ============
export type {
  MarketStatus,
  FlashNews,
  MarketOpportunity,
  PortfolioAnalysisResult,
  QuickPortfolioCheck,
  MarketSentiment,
  AggregatedNewsItem,
  RolloutSettings,
} from './frontend-types';

// ============ 待迁移类型（后端 schema 已定义，等 api.ts 重新生成后切换为 Schemas['xxx']） ============
export type {
  // 另类数据
  AHPremiumStock,
  AHPremiumStats,
  AHPremiumListResponse,
  ArbitrageSignal,
  AHPremiumDetailResponse,
  PatentNewsItem,
  PatentAnalysisResponse,
  // Vision
  VisionKeyDataPoint,
  VisionAnalysisResult,
  VisionAnalysisResponse,
  // 产业链
  ChainSummary,
  ChainListResponse,
  GraphNode,
  GraphEdge,
  ChainGraphResponse,
  ChainPosition,
  StockChainPositionResponse,
  SupplyChainImpact,
  SupplyChainImpactResponse,
} from './frontend-types';

// ============ 兼容性别名 ============

/** @deprecated 使用 AgentAnalysisResponse */
export type AgentAnalysis = AgentAnalysisResponse;

/** @deprecated 使用 MacroAnalysisResult */
export type MacroImpactAnalysis = MacroAnalysisResult;

