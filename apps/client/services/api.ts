/**
 * API 服务层 - 统一管理所有后端 API 调用
 *
 * 设计原则：
 * 1. 所有 API 调用集中在此文件
 * 2. 统一错误处理
 * 3. 类型安全
 */

import { logger } from '../utils/logger';

import {
  MarketOpportunity,
  FlashNews,
  AnalysisMemory,
  MemoryRetrievalResult,
  ReflectionReport,
  MarketWatcherOverview,
  MarketWatcherIndex,
  MarketRegion,
  AggregatedNewsItem,
  NewsAggregateResult,
  NewsCategory,
  HealthReport,
  GlobalMarketResponse,
  KlineDataResponse,
  StockPriceResponse,
  MemorySearchResponse,
  NewsSourcesResponse,
  HealthErrorsResponse,
  SSEEventData,
  ErrorRecord,
  ServiceStatusResponse,
  RegionSentimentInfo,
  ComponentHealthInfo,
  NorthMoneyFlow,
  NorthMoneySummary,
  NorthMoneyHistory,
  NorthMoneyHolding,
  NorthMoneyTopStock,
  IntradayFlowSummary,
  NorthMoneyAnomaly,
  NorthMoneyRealtime,
  NorthMoneySectorFlow,
  SectorRotationSignal,
  LHBStock,
  LHBSummary,
  HotMoneySeat,
  JiejinStock,
  JiejinCalendar,
  JiejinSummary,
  // 新增类型
  Stock,
  AgentAnalysis,
  ChatMessage,
  AnalysisHistoryItem,
  AnalysisTaskStatus,
  CorrelationMatrix,
  PortfolioAnalysisResult,
  QuickPortfolioCheck,
  MacroOverview,
  MacroImpactAnalysis,
} from '../types';

// ============ 基础配置 ============

export const API_BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000/api';

/**
 * API 错误类
 */
export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * 统一请求封装
 */
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => response.statusText);
    throw new ApiError(response.status, response.statusText, errorText);
  }

  // 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// ============ 分析 API ============

/**
 * SSE 连接状态
 */
export type SSEConnectionState = 'connecting' | 'connected' | 'reconnecting' | 'error' | 'closed';

/**
 * SSE 重连配置
 */
export interface SSERetryConfig {
  /** 最大重试次数，默认 3 */
  maxRetries?: number;
  /** 初始重试延迟（毫秒），默认 1000 */
  initialDelay?: number;
  /** 最大重试延迟（毫秒），默认 8000 */
  maxDelay?: number;
  /** 延迟倍数，默认 2 */
  backoffMultiplier?: number;
  /** 心跳超时（毫秒），超过此时间未收到任何事件则视为静默断连，默认 90000 (90秒) */
  heartbeatTimeout?: number;
}

/**
 * SSE 分析回调
 */
export interface SSEAnalysisCallbacks {
  /** 阶段事件回调 */
  onEvent: (event: string, data: SSEEventData) => void;
  /** 连接状态变化回调（可选） */
  onConnectionState?: (state: SSEConnectionState, retryCount?: number) => void;
}

/**
 * SSE 分析控制器
 */
export interface SSEAnalysisController {
  /** 取消分析（包括重试） */
  abort: () => void;
}

/**
 * 分析选项
 */
export interface AnalysisOptions {
  /** 分析级别：L1 快速扫描, L2 完整分析（默认 L2） */
  analysisLevel?: 'L1' | 'L2';
  /** 是否使用 Planner 动态选择分析师 */
  usePlanner?: boolean;
  /** 自定义分析师列表（覆盖默认） */
  overrideAnalysts?: string[];
  /** 排除的分析师 */
  excludeAnalysts?: string[];
}

/**
 * 触发股票分析（SSE 流式，带重连机制）
 *
 * @param symbol 股票代码
 * @param callbacks 回调函数
 * @param retryConfig 重连配置
 * @param options 分析选项
 * @returns 控制器，可用于取消分析
 */
export const analyzeStockWithAgent = async (
  symbol: string,
  callbacks: SSEAnalysisCallbacks | ((event: string, data: SSEEventData) => void),
  retryConfig: SSERetryConfig = {},
  options: AnalysisOptions = {}
): Promise<SSEAnalysisController> => {
  // 兼容旧的函数签名
  const { onEvent, onConnectionState } =
    typeof callbacks === 'function' ? { onEvent: callbacks, onConnectionState: undefined } : callbacks;

  const {
    maxRetries = 3,
    initialDelay = 1000,
    maxDelay = 8000,
    backoffMultiplier = 2,
    heartbeatTimeout = 90_000,
  } = retryConfig;

  let aborted = false;
  let currentEventSource: EventSource | null = null;
  let heartbeatTimer: ReturnType<typeof setTimeout> | null = null;

  const clearHeartbeat = () => {
    if (heartbeatTimer) {
      clearTimeout(heartbeatTimer);
      heartbeatTimer = null;
    }
  };

  const controller: SSEAnalysisController = {
    abort: () => {
      aborted = true;
      clearHeartbeat();
      if (currentEventSource) {
        currentEventSource.close();
        currentEventSource = null;
      }
    },
  };

  // 计算退避延迟（含随机抖动，防止惊群效应）
  const getBackoffDelay = (retryCount: number): number => {
    const base = initialDelay * Math.pow(backoffMultiplier, retryCount);
    const capped = Math.min(base, maxDelay);
    // 添加 ±25% 的随机抖动
    const jitter = capped * (0.75 + Math.random() * 0.5);
    return Math.round(jitter);
  };

  // 等待指定时间
  const sleep = (ms: number): Promise<void> =>
    new Promise((resolve) => setTimeout(resolve, ms));

  // 触发分析任务
  onConnectionState?.('connecting');

  // 构建请求体（仅包含非默认值的选项）
  const requestBody: Record<string, unknown> = {};
  if (options.analysisLevel) {
    requestBody.analysis_level = options.analysisLevel;
  }
  if (options.usePlanner !== undefined) {
    requestBody.use_planner = options.usePlanner;
  }
  if (options.overrideAnalysts?.length) {
    requestBody.override_analysts = options.overrideAnalysts;
  }
  if (options.excludeAnalysts?.length) {
    requestBody.exclude_analysts = options.excludeAnalysts;
  }

  const response = await fetch(`${API_BASE}/analyze/${symbol}`, {
    method: 'POST',
    headers: Object.keys(requestBody).length > 0 ? { 'Content-Type': 'application/json' } : undefined,
    body: Object.keys(requestBody).length > 0 ? JSON.stringify(requestBody) : undefined,
  });

  if (!response.ok) {
    onConnectionState?.('error');
    throw new ApiError(response.status, response.statusText, `Failed to start analysis for ${symbol}`);
  }

  const { task_id } = await response.json();

  // SSE 连接函数（支持重试 + 心跳超时检测）
  const connectSSE = async (retryCount: number = 0): Promise<void> => {
    if (aborted) {
      onConnectionState?.('closed');
      return;
    }

    return new Promise((resolve, reject) => {
      const eventSource = new EventSource(`${API_BASE}/analyze/stream/${task_id}`);
      currentEventSource = eventSource;

      let isCompleted = false;

      const stages = ['stage_analyst', 'stage_debate', 'stage_risk', 'stage_final', 'error', 'progress'];

      // 心跳超时：若超过 heartbeatTimeout 未收到任何事件，视为静默断连
      const resetHeartbeat = () => {
        clearHeartbeat();
        if (isCompleted || aborted) return;
        heartbeatTimer = setTimeout(() => {
          if (isCompleted || aborted) return;
          logger.warn(`SSE heartbeat timeout (${heartbeatTimeout}ms), triggering reconnect`);
          eventSource.close();
          currentEventSource = null;
          handleReconnect(retryCount, resolve, reject);
        }, heartbeatTimeout);
      };

      // 连接成功时触发
      eventSource.onopen = () => {
        if (retryCount > 0) {
          logger.info(`SSE reconnected after ${retryCount} retries`);
        }
        onConnectionState?.('connected');
        resetHeartbeat();
      };

      stages.forEach((stage) => {
        eventSource.addEventListener(stage, (event: MessageEvent) => {
          // 收到事件，重置心跳计时
          resetHeartbeat();

          try {
            const data = JSON.parse(event.data);
            onEvent(stage, data);

            if (stage === 'stage_final' || stage === 'error') {
              isCompleted = true;
              clearHeartbeat();
              eventSource.close();
              currentEventSource = null;
              onConnectionState?.('closed');
              resolve();
            }
          } catch (parseError) {
            logger.error('Failed to parse SSE data:', parseError);
          }
        });
      });

      eventSource.onerror = async () => {
        clearHeartbeat();
        eventSource.close();
        currentEventSource = null;

        // 已完成或已中止，不重试
        if (isCompleted || aborted) {
          onConnectionState?.('closed');
          resolve();
          return;
        }

        handleReconnect(retryCount, resolve, reject);
      };
    });
  };

  // 统一的重连处理（onerror 和心跳超时共用）
  const handleReconnect = async (
    retryCount: number,
    resolve: () => void,
    reject: (reason: Error) => void,
  ) => {
    if (retryCount < maxRetries) {
      const delay = getBackoffDelay(retryCount);
      logger.warn(
        `SSE reconnecting in ${delay}ms (attempt ${retryCount + 1}/${maxRetries})`
      );

      onConnectionState?.('reconnecting', retryCount + 1);

      await sleep(delay);

      if (!aborted) {
        try {
          await connectSSE(retryCount + 1);
          resolve();
        } catch (retryError) {
          reject(retryError as Error);
        }
      } else {
        onConnectionState?.('closed');
        resolve();
      }
    } else {
      // 达到最大重试次数
      logger.error(`SSE connection failed after ${maxRetries} retries`);
      onConnectionState?.('error');
      onEvent('error', {
        message: `连接失败，已重试 ${maxRetries} 次`,
        code: 'SSE_MAX_RETRIES_EXCEEDED',
      });
      reject(new Error(`SSE connection failed after ${maxRetries} retries`));
    }
  };

  // 启动 SSE 连接（异步，不阻塞返回控制器）
  connectSSE().catch((error) => {
    logger.error('SSE connection failed:', error);
  });

  return controller;
};

/**
 * 获取最新分析结果
 */
export const getLatestAnalysis = (symbol: string) =>
  request<AgentAnalysis>(`/analyze/latest/${symbol}`);

/**
 * 快速扫描（L1 模式）
 *
 * 仅运行 Market + News + Macro 三个分析师，跳过辩论和风险评估。
 */
export const quickScanStock = (symbol: string) =>
  request<{
    task_id: string;
    symbol: string;
    status: string;
    analysis_level: string;
    analysts: string[];
    estimated_time_seconds: number;
  }>(`/analyze/quick/${symbol}`, { method: 'POST' });

/**
 * 获取分析历史
 */
export const getAnalysisHistory = (symbol: string, limit: number = 10) =>
  request<{ items: AnalysisHistoryItem[]; total: number; offset: number; limit: number }>(`/analyze/history/${symbol}?limit=${limit}&status=completed`);

/**
 * 获取指定 ID 的完整分析报告
 */
export const getAnalysisDetail = (analysisId: number) =>
  request<{
    id: number;
    symbol: string;
    date: string;
    signal: string;
    confidence: number;
    full_report: AgentAnalysis;
    anchor_script: string;
    created_at: string;
    task_id: string;
    elapsed_seconds: number;
  }>(`/analyze/detail/${analysisId}`);

/**
 * 获取分析任务状态
 */
export const getAnalysisStatus = (taskId: string) =>
  request<AnalysisTaskStatus>(`/analyze/status/${taskId}`);

// ============ 监听列表 API ============

export const getWatchlist = () => request<Stock[]>('/watchlist/');

export const addToWatchlist = (symbol: string) =>
  request<Stock>(`/watchlist/${symbol}`, { method: 'POST' });

export const removeFromWatchlist = (symbol: string) =>
  request<{ deleted: boolean }>(`/watchlist/${symbol}`, { method: 'DELETE' });

// ============ 市场数据 API ============

export const getMarketPrice = (symbol: string) =>
  request<StockPriceResponse>(`/market/price/${symbol}`);

export const getMarketHistory = (symbol: string, period: string = '1mo') =>
  request<KlineDataResponse[]>(`/market/history/${symbol}?period=${period}`);

export const getMarketKline = (symbol: string, days: number = 90) =>
  request<{ data: KlineDataResponse[]; symbol: string }>(`/market/kline/${encodeURIComponent(symbol)}?days=${days}`);

export const getGlobalMarket = () => request<GlobalMarketResponse>('/market/global');

// ============ 发现 API ============

export const discoverStocks = async (query: string): Promise<MarketOpportunity[]> => {
  const data = await request<{ results: MarketOpportunity[] }>(
    `/discover/?query=${encodeURIComponent(query)}`
  );
  return data.results;
};

// ============ 新闻 API (旧版) ============

export const getFlashNews = () => request<FlashNews[]>('/news/flash');

export const getStockNews = (symbol: string) =>
  request<FlashNews[]>(`/news/${symbol}`);

// ============ 聊天 API ============

export const getChatResponse = (threadId: string, message: string) =>
  request<ChatMessage>(`/chat/${threadId}?message=${encodeURIComponent(message)}`, {
    method: 'POST',
  });

export const getChatHistory = (threadId: string) =>
  request<ChatMessage[]>(`/chat/${threadId}`);

// ============ Prompt 管理 API ============

export interface PromptConfig {
  system: string;
  user: string;
}

export const getPrompts = () => request<{ prompts: Record<string, PromptConfig>; path: string }>('/settings/prompts');

export const getPromptByRole = (role: string) =>
  request<PromptConfig>(`/settings/prompts/${role}`);

export const updatePromptByRole = (role: string, config: PromptConfig, apiKey?: string) =>
  request<{ updated: boolean }>(`/settings/prompts/${role}`, {
    method: 'PUT',
    headers: apiKey ? { 'X-API-Key': apiKey } : undefined,
    body: JSON.stringify(config),
  });

export const updateAllPrompts = (prompts: Record<string, PromptConfig>, apiKey?: string) =>
  request<{ updated: boolean }>('/settings/prompts', {
    method: 'PUT',
    headers: apiKey ? { 'X-API-Key': apiKey } : undefined,
    body: JSON.stringify({ prompts }),
  });

export const reloadPrompts = () =>
  request<{ reloaded: boolean }>('/settings/prompts/reload', { method: 'POST' });

// ============ Portfolio 分析 API ============

export const getPortfolioCorrelation = (symbols: string[], period: string = '1mo') =>
  request<CorrelationMatrix>('/portfolio/correlation', {
    method: 'POST',
    body: JSON.stringify({ symbols, period }),
  });

export const getPortfolioAnalysis = (symbols: string[], period: string = '1mo') =>
  request<PortfolioAnalysisResult>('/portfolio/analyze', {
    method: 'POST',
    body: JSON.stringify({ symbols, period }),
  });

export const getQuickPortfolioCheck = (symbols: string[]) =>
  request<QuickPortfolioCheck>(`/portfolio/quick-check?symbols=${symbols.join(',')}`);

// ============ 宏观经济 API ============

export const getMacroOverview = () => request<MacroOverview>('/macro/overview');

export const getMacroIndicator = (name: string) =>
  request<Record<string, unknown>>(`/macro/indicator/${name}`);

export const getMacroImpactAnalysis = (market?: string) => {
  const query = market ? `?market=${market}` : '';
  return request<MacroImpactAnalysis>(`/macro/impact-analysis${query}`);
};

export const refreshMacro = () =>
  request<ServiceStatusResponse>('/macro/refresh', { method: 'POST' });

// ============ 记忆服务 API ============

export const getMemoryStatus = () =>
  request<{ status: string; total_memories: number; chroma_path: string }>('/memory/status');

export const getMemoryRetrieve = (symbol: string, nResults: number = 5, maxDays: number = 365) =>
  request<MemoryRetrievalResult[]>(
    `/memory/retrieve/${symbol}?n_results=${nResults}&max_days=${maxDays}`
  );

export const getReflection = (symbol: string) =>
  request<ReflectionReport | null>(`/memory/reflection/${symbol}`);

export const storeMemory = (memory: AnalysisMemory) =>
  request<ServiceStatusResponse>('/memory/store', {
    method: 'POST',
    body: JSON.stringify(memory),
  });

export const clearMemory = (symbol?: string) => {
  const query = symbol ? `?symbol=${symbol}` : '';
  return request<ServiceStatusResponse>(`/memory/clear${query}`, { method: 'DELETE' });
};

export const searchMemory = (query: string, nResults: number = 10) =>
  request<MemorySearchResponse>(
    `/memory/search?query=${encodeURIComponent(query)}&n_results=${nResults}`
  );

// ============ 市场监控 API ============

export const getMarketWatcherStatus = () =>
  request<ServiceStatusResponse>('/market-watcher/status');

export const getMarketWatcherOverview = (forceRefresh: boolean = false) =>
  request<MarketWatcherOverview>(
    `/market-watcher/overview${forceRefresh ? '?force_refresh=true' : ''}`
  );

export const getMarketIndices = (region?: MarketRegion, forceRefresh: boolean = false) => {
  const params = new URLSearchParams();
  if (region) params.append('region', region);
  if (forceRefresh) params.append('force_refresh', 'true');
  const query = params.toString() ? `?${params.toString()}` : '';
  return request<MarketWatcherIndex[]>(`/market-watcher/indices${query}`);
};

export const getMarketIndex = (code: string) =>
  request<MarketWatcherIndex>(`/market-watcher/index/${code}`);

export const refreshMarketIndices = () =>
  request<ServiceStatusResponse>('/market-watcher/refresh', { method: 'POST' });

export const getMarketSentiment = () =>
  request<{
    global_sentiment: string;
    risk_level: number;
    regions: Record<string, RegionSentimentInfo>;
    updated_at: string;
  }>('/market-watcher/sentiment');

// ============ 新闻聚合 API ============

export const getNewsAggregatorStatus = () =>
  request<ServiceStatusResponse>('/news-aggregator/status');

export const getAggregatedNews = (forceRefresh: boolean = false) =>
  request<NewsAggregateResult>(
    `/news-aggregator/all${forceRefresh ? '?force_refresh=true' : ''}`
  );

export const getNewsFlashAggregated = (limit: number = 10) =>
  request<AggregatedNewsItem[]>(`/news-aggregator/flash?limit=${limit}`);

export const getNewsByCategory = (category: NewsCategory, limit: number = 20) =>
  request<AggregatedNewsItem[]>(`/news-aggregator/category/${category}?limit=${limit}`);

export const getNewsBySymbol = (symbol: string, limit: number = 20) =>
  request<AggregatedNewsItem[]>(`/news-aggregator/symbol/${symbol}?limit=${limit}`);

export const refreshAggregatedNews = () =>
  request<ServiceStatusResponse>('/news-aggregator/refresh', { method: 'POST' });

export const getNewsSources = () =>
  request<NewsSourcesResponse>('/news-aggregator/sources');

// ============ 健康监控 API ============

export const getHealthQuick = () =>
  request<{ status: string; uptime_seconds: number }>('/health/');

export const getHealthReport = (forceRefresh: boolean = false) =>
  request<HealthReport>(`/health/report${forceRefresh ? '?force_refresh=true' : ''}`);

export const getHealthComponents = () =>
  request<{ overall: string; components: Record<string, ComponentHealthInfo> }>('/health/components');

export const getHealthMetrics = () =>
  request<{
    cpu: { percent: number };
    memory: { percent: number; used_mb: number; total_mb: number };
    disk: { percent: number; used_gb: number; total_gb: number };
  }>('/health/metrics');

export const getHealthErrors = (limit: number = 10) =>
  request<HealthErrorsResponse>(`/health/errors?limit=${limit}`);

export const clearHealthErrors = () =>
  request<ServiceStatusResponse>('/health/errors', { method: 'DELETE' });

export const getSystemUptime = () =>
  request<{
    start_time: string;
    uptime_seconds: number;
    uptime_formatted: string;
    current_time: string;
  }>('/health/uptime');

export const checkLiveness = () =>
  request<{ status: string }>('/health/liveness');

export const checkReadiness = () =>
  request<{ status: string; components: number }>('/health/readiness');

// ============ 管理 API ============

export const triggerDailyAnalysis = () =>
  request<{ status: string; message: string }>('/admin/trigger-daily-analysis', { method: 'POST' });

export const getSchedulerJobs = () =>
  request<{ jobs: Array<{ id: string; next_run_time: string | null; trigger: string }> }>('/admin/scheduler/jobs');

export const getSchedulerStatus = () =>
  request<{ running: boolean; analysis_in_progress: boolean; jobs_count: number }>('/admin/scheduler/status');

// ============ AI 配置 API ============

/**
 * AI 提供商类型
 */
export type AIProviderType = 'openai' | 'openai_compatible' | 'google' | 'anthropic' | 'deepseek';

/**
 * AI 提供商
 */
export interface AIProvider {
  id: number;
  name: string;
  provider_type: AIProviderType;
  base_url: string | null;
  api_key_masked: string;
  models: string[];
  is_enabled: boolean;
  priority: number;
  created_at: string;
  updated_at: string;
}

/**
 * AI 模型配置
 */
export interface AIModelConfig {
  config_key: string;
  provider_id: number | null;
  provider_name: string | null;
  model_name: string;
  is_active: boolean;
  updated_at: string;
}

/**
 * AI 配置状态
 */
export interface AIConfigStatus {
  initialized: boolean;
  providers_count: number;
  configs_count: number;
  cached_llms: string[];
  last_refresh: string | null;
}

/**
 * 测试提供商结果
 */
export interface TestProviderResult {
  success: boolean;
  model?: string;
  response_preview?: string;
  error?: string;
}

// 提供商 CRUD
export const listAIProviders = () =>
  request<{ providers: AIProvider[] }>('/ai/providers');

export const getAIProvider = (providerId: number) =>
  request<AIProvider>(`/ai/providers/${providerId}`);

export const createAIProvider = (data: {
  name: string;
  provider_type: AIProviderType;
  base_url?: string;
  api_key?: string;
  models?: string[];
  is_enabled?: boolean;
  priority?: number;
}) =>
  request<{ id: number; name: string; provider_type: string }>('/ai/providers', {
    method: 'POST',
    body: JSON.stringify(data),
  });

export const updateAIProvider = (
  providerId: number,
  data: Partial<{
    name: string;
    provider_type: AIProviderType;
    base_url: string;
    api_key: string;
    models: string[];
    is_enabled: boolean;
    priority: number;
  }>
) =>
  request<{ id: number; name: string; updated: boolean }>(`/ai/providers/${providerId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });

export const deleteAIProvider = (providerId: number) =>
  request<{ deleted: boolean }>(`/ai/providers/${providerId}`, {
    method: 'DELETE',
  });

export const testAIProvider = (providerId: number) =>
  request<TestProviderResult>(`/ai/providers/${providerId}/test`, {
    method: 'POST',
  });

// 模型配置
export const getAIModelConfigs = () =>
  request<{ configs: AIModelConfig[] }>('/ai/models');

export const updateAIModelConfig = (
  configKey: string,
  data: { provider_id: number; model_name: string }
) =>
  request<{ config_key: string; updated: boolean }>(`/ai/models/${configKey}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });

// 管理操作
export const refreshAIConfig = () =>
  request<{ refreshed: boolean }>('/ai/refresh', { method: 'POST' });

export const getAIConfigStatus = () =>
  request<AIConfigStatus>('/ai/status');

// ============ 北向资金 API (A股特有) ============

export const getNorthMoneyFlow = () =>
  request<NorthMoneyFlow>('/north-money/flow');

export const getNorthMoneySummary = () =>
  request<NorthMoneySummary>('/north-money/summary');

export const getNorthMoneyHistory = (days: number = 30) =>
  request<NorthMoneyHistory[]>(`/north-money/history?days=${days}`);

export const getNorthMoneyHolding = (symbol: string) =>
  request<NorthMoneyHolding>(`/north-money/holding/${symbol}`);

export const getNorthMoneyTopBuys = (limit: number = 20) =>
  request<NorthMoneyTopStock[]>(`/north-money/top-buys?limit=${limit}`);

export const getNorthMoneyTopSells = (limit: number = 20) =>
  request<NorthMoneyTopStock[]>(`/north-money/top-sells?limit=${limit}`);

export const getNorthMoneyIntraday = () =>
  request<IntradayFlowSummary>('/north-money/intraday');

export const getNorthMoneyAnomalies = () =>
  request<NorthMoneyAnomaly[]>('/north-money/anomalies');

export const getNorthMoneyRealtime = () =>
  request<NorthMoneyRealtime>('/north-money/realtime');

export const getNorthMoneySectorFlow = () =>
  request<NorthMoneySectorFlow[]>('/north-money/sector-flow');

export const getNorthMoneyRotationSignal = () =>
  request<SectorRotationSignal>('/north-money/rotation-signal');

// ============ 龙虎榜 API (A股特有) ============

export const getLHBDaily = (tradeDate?: string) => {
  const query = tradeDate ? `?trade_date=${tradeDate}` : '';
  return request<LHBStock[]>(`/lhb/daily${query}`);
};

export const getLHBSummary = () =>
  request<LHBSummary>('/lhb/summary');

export const getLHBStockHistory = (symbol: string, days: number = 30) =>
  request<LHBStock[]>(`/lhb/stock/${symbol}?days=${days}`);

export const getLHBHotMoneyActivity = (days: number = 5) =>
  request<HotMoneySeat[]>(`/lhb/hot-money?days=${days}`);

export const getLHBTopBuys = (limit: number = 10) =>
  request<LHBStock[]>(`/lhb/top-buys?limit=${limit}`);

export const getLHBTopSells = (limit: number = 10) =>
  request<LHBStock[]>(`/lhb/top-sells?limit=${limit}`);

export const getLHBInstitutionActivity = (direction: 'buy' | 'sell' | 'all' = 'all') =>
  request<LHBStock[]>(`/lhb/institution-activity?direction=${direction}`);

export const getLHBHotMoneyStocks = () =>
  request<LHBStock[]>('/lhb/hot-money-stocks');

// ============ 限售解禁 API (A股特有) ============

export const getJiejinUpcoming = (days: number = 30) =>
  request<JiejinStock[]>(`/jiejin/upcoming?days=${days}`);

export const getJiejinCalendar = (days: number = 30) =>
  request<JiejinCalendar[]>(`/jiejin/calendar?days=${days}`);

export const getJiejinSummary = (days: number = 30) =>
  request<JiejinSummary>(`/jiejin/summary?days=${days}`);

export const getJiejinStockPlan = (symbol: string) =>
  request<JiejinStock>(`/jiejin/stock/${symbol}`);

export const getJiejinHighPressure = (days: number = 7) =>
  request<JiejinStock[]>(`/jiejin/high-pressure?days=${days}`);

export const getJiejinWarning = (symbol: string, days: number = 30) =>
  request<{ symbol: string; warning: boolean; message: string; upcoming: JiejinStock[] }>(`/jiejin/warning/${symbol}?days=${days}`);

export const getJiejinToday = () =>
  request<JiejinStock[]>('/jiejin/today');

export const getJiejinWeek = () =>
  request<JiejinStock[]>('/jiejin/week');

// ============ Prompt 配置 API ============

import type { AgentPrompt, AgentPromptDetail, AgentCategory, PromptServiceStatus } from '../types';

/** 获取所有 Prompt 列表 */
export const getPromptList = (category?: AgentCategory) => {
  const query = category ? `?category=${category}` : '';
  return request<{ prompts: AgentPrompt[]; total: number }>(`/prompts/${query}`);
};

/** 获取 Prompt 详情（含版本历史） */
export const getPromptDetail = (promptId: number) =>
  request<AgentPromptDetail>(`/prompts/${promptId}`);

/** 更新 Prompt */
export const updatePrompt = (
  promptId: number,
  data: {
    system_prompt?: string;
    user_prompt_template?: string;
    display_name?: string;
    description?: string;
    available_variables?: string[];
    change_note?: string;
  }
) =>
  request<{ id: number; agent_key: string; version: number; updated: boolean }>(
    `/prompts/${promptId}`,
    { method: 'PUT', body: JSON.stringify(data) }
  );

/** 回滚 Prompt 到指定版本 */
export const rollbackPrompt = (promptId: number, targetVersion: number) =>
  request<{ id: number; agent_key: string; rolled_back_to: number; new_version: number }>(
    `/prompts/${promptId}/rollback`,
    { method: 'POST', body: JSON.stringify({ target_version: targetVersion }) }
  );

/** 刷新 Prompt 缓存 */
export const refreshPromptCache = () =>
  request<PromptServiceStatus>('/prompts/refresh', { method: 'POST' });

/** 获取 Prompt 服务状态 */
export const getPromptServiceStatus = () =>
  request<PromptServiceStatus>('/prompts/status');

/** 导出 Prompt 为 YAML */
export const exportPromptsYaml = async (): Promise<string> => {
  const response = await fetch(`${API_BASE}/prompts/export/yaml`);
  if (!response.ok) throw new ApiError(response.status, response.statusText, 'Export failed');
  return response.text();
};

/** 导入 YAML 格式的 Prompt */
export const importPromptsYaml = (yamlContent: string) =>
  request<{ success: boolean; created: number; updated: number }>(
    '/prompts/import/yaml',
    { method: 'POST', body: JSON.stringify({ yaml_content: yamlContent }) }
  );

/** 预览 Prompt（带变量注入） */
export const previewPrompt = (agentKey: string, variables?: Record<string, unknown>) =>
  request<{
    agent_key: string;
    rendered_system_prompt: string;
    rendered_user_prompt: string;
    variables_used: Record<string, unknown>;
  }>(
    `/prompts/preview?agent_key=${encodeURIComponent(agentKey)}`,
    { method: 'POST', body: JSON.stringify(variables || {}) }
  );

/** 获取所有 Agent 分类 */
export const getPromptCategories = () =>
  request<{ categories: { value: string; label: string }[] }>('/prompts/categories');

