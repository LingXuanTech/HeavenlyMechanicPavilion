/**
 * Custom Hooks - 基于 TanStack Query
 *
 * 集中导出所有自定义 hooks
 */

// Watchlist 管理
export { useWatchlist, useAddStock, useRemoveStock, WATCHLIST_KEY } from './useWatchlist';

// 价格数据
export { useStockPrice, useStockHistory, useStockPrices, PRICE_KEY, HISTORY_KEY } from './usePrices';

// 分析数据
export {
  useLatestAnalysis,
  useStockAnalysis,
  useCachedAnalyses,
  ANALYSIS_KEY,
  LATEST_ANALYSIS_KEY,
} from './useAnalysis';
export type { AnalysisState } from './useAnalysis';
export type { AnalysisOptions } from '../services/api';

// 市场数据
export {
  useGlobalMarket,
  useFlashNews,
  useMarketStatus,
  GLOBAL_MARKET_KEY,
  FLASH_NEWS_KEY,
} from './useMarket';

// Prompt 管理
export {
  usePrompts,
  usePromptByRole,
  useUpdatePrompt,
  useUpdateAllPrompts,
  useReloadPrompts,
  PROMPTS_KEY,
} from './usePrompts';
export type { PromptConfig, PromptsData } from './usePrompts';

// Portfolio 分析
export {
  usePortfolioCorrelation,
  usePortfolioAnalysis,
  useQuickPortfolioCheck,
  PORTFOLIO_KEY,
} from './usePortfolio';

// 宏观经济分析
export {
  useMacroOverview,
  useMacroImpactAnalysis,
  useRefreshMacro,
  MACRO_KEY,
} from './useMacro';

// 记忆服务
export {
  useMemoryStatus,
  useMemoryRetrieve,
  useReflection,
  useMemorySearch,
  useStoreMemory,
  useClearMemory,
  MEMORY_KEY,
} from './useMemory';

// 市场监控
export {
  useMarketWatcherStatus,
  useMarketWatcherOverview,
  useMarketIndices,
  useMarketIndex,
  useMarketSentiment,
  useRefreshMarketIndices,
  MARKET_WATCHER_KEY,
} from './useMarketWatcher';

// 新闻聚合
export {
  useNewsAggregatorStatus,
  useAggregatedNews,
  useNewsFlash,
  useNewsByCategory,
  useNewsBySymbol,
  useNewsSources,
  useRefreshNews,
  NEWS_AGGREGATOR_KEY,
} from './useNewsAggregator';

// 健康监控
export {
  useHealthQuick,
  useHealthReport,
  useHealthComponents,
  useHealthMetrics,
  useHealthErrors,
  useSystemUptime,
  useLiveness,
  useReadiness,
  useClearHealthErrors,
  useResetCircuitBreaker,
  useProviderHistory,
  useTrackedProviders,
  HEALTH_KEY,
} from './useHealth';
export type {
  ProviderHistoryRecord,
  ProviderHistorySummary,
  CircuitBreakerEvent,
  ProviderHistoryResponse,
} from './useHealth';

// AI Scout
export { useScout, SCOUT_KEY } from './useScout';
export type { UseScoutReturn } from './useScout';

// 调度器管理
export {
  useSchedulerStatus,
  useSchedulerJobs,
  useTriggerDailyAnalysis,
  useRefreshScheduler,
  SCHEDULER_KEY,
} from './useScheduler';
export type { SchedulerJob, SchedulerStatus, SchedulerJobsResponse } from './useScheduler';

// 打字机效果
export { useTypewriter, useStreamTypewriter } from './useTypewriter';
export type {
  UseTypewriterOptions,
  UseTypewriterReturn,
  UseStreamTypewriterOptions,
  UseStreamTypewriterReturn,
} from './useTypewriter';

// 流式分析
export { useStreamingAnalysis } from './useStreamingAnalysis';
export type {
  StreamingAnalysisState,
  UseStreamingAnalysisOptions,
} from './useStreamingAnalysis';

// A 股特有功能
export {
  // 北向资金
  useNorthMoneyFlow,
  useNorthMoneySummary,
  useNorthMoneyHistory,
  useNorthMoneyHolding,
  useNorthMoneyTopBuys,
  useNorthMoneyTopSells,
  useNorthMoneyIntraday,
  useNorthMoneyAnomalies,
  useNorthMoneyRealtime,
  useNorthMoneySectorFlow,
  useNorthMoneyRotationSignal,
  NORTH_MONEY_KEY,
  // 龙虎榜
  useLHBDaily,
  useLHBSummary,
  useLHBHotMoney,
  useLHBTopBuys,
  useLHBTopSells,
  useLHBInstitution,
  useLHBHotMoneyStocks,
  LHB_KEY,
  // 限售解禁
  useJiejinUpcoming,
  useJiejinCalendar,
  useJiejinSummary,
  useJiejinHighPressure,
  useJiejinToday,
  useJiejinWeek,
  useJiejinWarning,
  JIEJIN_KEY,
} from './useChinaMarket';

// 图表指标
export { useChartIndicators } from './useChartIndicators';
export type { default as UseChartIndicatorsOptions } from './useChartIndicators';

// 历史分析对比
export {
  useAnalysisHistory,
  useAnalysisDetail,
  useAnalysisComparison,
  ANALYSIS_HISTORY_KEY,
  ANALYSIS_DETAIL_KEY,
} from './useAnalysisHistory';

// AI 配置
export {
  useAIProviders,
  useAIProvider,
  useCreateAIProvider,
  useUpdateAIProvider,
  useDeleteAIProvider,
  useTestAIProvider,
  useAIModelConfigs,
  useUpdateAIModelConfig,
  useRefreshAIConfig,
  useAIConfigStatus,
  getProviderTypeLabel,
  getConfigKeyLabel,
  getConfigKeyDescription,
} from './useAIConfig';

// 另类数据（AH 溢价 + 专利监控）
export {
  useAHPremiumList,
  useAHPremiumDetail,
  usePatentAnalysis,
  alternativeDataKeys,
} from './useAlternativeData';
export type {
  AHPremiumStock,
  AHPremiumStats,
  AHPremiumListResponse,
  ArbitrageSignal,
  AHPremiumDetailResponse,
  PatentNewsItem,
  PatentAnalysisResponse,
} from './useAlternativeData';

// Vision 分析（多模态）
export {
  useVisionAnalysis,
  useVisionHistory,
  visionKeys,
} from './useVision';
export type {
  VisionAnalysisResult,
  VisionAnalysisResponse,
  VisionKeyDataPoint,
} from './useVision';

// 产业链知识图谱
export {
  useChainList,
  useChainGraph,
  useStockChainPosition,
  useSupplyChainImpact,
  supplyChainKeys,
} from './useSupplyChain';
export type {
  ChainSummary,
  ChainListResponse,
  GraphNode,
  GraphEdge,
  ChainGraphResponse,
  ChainPosition,
  StockChainPositionResponse,
  SupplyChainImpact,
  SupplyChainImpactResponse,
} from './useSupplyChain';

// 风控建模
export {
  useCalculateVaR,
  useStressTest,
  useRiskMetrics,
} from './useRiskModeling';
export type {
  VaRResult,
  StressTestScenario,
  StressTestResult,
  RiskMetrics,
} from './useRiskModeling';

// SubGraph A/B 指标
export {
  useSubgraphComparison,
  useUpdateRollout,
  SUBGRAPH_METRICS_KEY,
} from './useSubgraphMetrics';
export type {
  ModeStats,
  Recommendation,
  SubgraphComparison,
  RolloutUpdateResult,
} from './useSubgraphMetrics';
