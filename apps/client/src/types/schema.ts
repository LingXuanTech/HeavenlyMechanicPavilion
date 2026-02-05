/**
 * 前端类型定义中心
 *
 * 所有类型都从 OpenAPI 自动生成的 api.ts 中导出
 * 不再手动定义类型，确保前后端类型同步
 */

import { paths, components } from './api';

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
export type HealthReport = Schemas['HealthReport'];
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

// ============ 兼容性别名（逐步废弃） ============
// 这些别名是为了兼容旧代码，新代码应直接使用上面的类型

/** @deprecated 使用 AgentAnalysisResponse */
export type AgentAnalysis = AgentAnalysisResponse;

/** @deprecated 使用 AssetPrice */
export type Stock = AssetPrice;

/** @deprecated 使用 StockNorthHolding */
export type NorthMoneyHolding = StockNorthHolding;

// ============ 前端专用类型（后端未定义） ============

/**
 * 市场状态（前端 UI 专用）
 */
export interface MarketStatus {
  sentiment: 'Bullish' | 'Bearish' | 'Neutral';
  lastUpdated: string;
  activeAgents: number;
}

/**
 * 快讯新闻（前端 UI 专用）
 */
export interface FlashNews {
  id: string;
  time: string;
  headline: string;
  impact: 'High' | 'Medium' | 'Low';
  sentiment: 'Positive' | 'Negative';
  relatedSymbols: string[];
}

/**
 * 市场机会（Scout 返回）
 */
export interface MarketOpportunity {
  symbol: string;
  name: string;
  market: 'US' | 'HK' | 'CN';
  reason: string;
  score: number;
}


/**
 * 分析任务状态
 */
export type AnalysisTaskStatus = Schemas['AnalysisTaskStatus'];

/**
 * 投资组合分析结果
 */
export interface PortfolioAnalysisResult {
  correlation: CorrelationResult;
  diversification_score: number;
  risk_clusters: Array<{
    stocks: string[];
    avg_correlation: number;
    risk_level: string;
  }>;
  recommendations: string[];
}

/**
 * 快速投资组合检查
 */
export interface QuickPortfolioCheck {
  summary: string;
  risk_level: string;
  top_risks: string[];
}

/**
 * 市场情绪数据
 */
export interface MarketSentiment {
  global_sentiment: string;
  risk_level: number;
  regions: Record<string, {
    indices_count: number;
    avg_change_percent: number;
    sentiment: string;
  }>;
  updated_at: string;
}

/**
 * 宏观影响分析 (兼容旧名称，建议使用 MacroAnalysisResult)
 */
export type MacroImpactAnalysis = MacroAnalysisResult;

/**
 * 聚合新闻条目
 */
export interface AggregatedNewsItem {
  id: string;
  title: string;
  summary?: string | null;
  source: string;
  url: string;
  category: NewsCategory;
  sentiment: NewsSentiment;
  symbols: string[];
  published_at: string;
  fetched_at: string;
}
