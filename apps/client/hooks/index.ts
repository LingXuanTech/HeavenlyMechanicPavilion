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
export type { CorrelationResult, RiskCluster, PortfolioAnalysis } from './usePortfolio';

// 宏观经济分析
export {
  useMacroOverview,
  useMacroImpactAnalysis,
  useRefreshMacro,
  MACRO_KEY,
} from './useMacro';
export type { MacroIndicator, MacroOverview, MacroImpact, MacroAnalysisResult } from './useMacro';

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
  HEALTH_KEY,
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
