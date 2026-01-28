/**
 * API 服务层 - 统一管理所有后端 API 调用
 *
 * 设计原则：
 * 1. 所有 API 调用集中在此文件
 * 2. 统一错误处理
 * 3. 类型安全
 */

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
} from '../types';

// ============ 基础配置 ============

const API_BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000/api';

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
 * 触发股票分析（SSE 流式，带重连机制）
 *
 * @param symbol 股票代码
 * @param callbacks 回调函数
 * @param retryConfig 重连配置
 * @returns 控制器，可用于取消分析
 */
export const analyzeStockWithAgent = async (
  symbol: string,
  callbacks: SSEAnalysisCallbacks | ((event: string, data: SSEEventData) => void),
  retryConfig: SSERetryConfig = {}
): Promise<SSEAnalysisController> => {
  // 兼容旧的函数签名
  const { onEvent, onConnectionState } =
    typeof callbacks === 'function' ? { onEvent: callbacks, onConnectionState: undefined } : callbacks;

  const {
    maxRetries = 3,
    initialDelay = 1000,
    maxDelay = 8000,
    backoffMultiplier = 2,
  } = retryConfig;

  let aborted = false;
  let currentEventSource: EventSource | null = null;

  const controller: SSEAnalysisController = {
    abort: () => {
      aborted = true;
      if (currentEventSource) {
        currentEventSource.close();
        currentEventSource = null;
      }
    },
  };

  // 计算退避延迟
  const getBackoffDelay = (retryCount: number): number => {
    const delay = initialDelay * Math.pow(backoffMultiplier, retryCount);
    return Math.min(delay, maxDelay);
  };

  // 等待指定时间
  const sleep = (ms: number): Promise<void> =>
    new Promise((resolve) => setTimeout(resolve, ms));

  // 触发分析任务
  onConnectionState?.('connecting');

  const response = await fetch(`${API_BASE}/analyze/${symbol}`, {
    method: 'POST',
  });

  if (!response.ok) {
    onConnectionState?.('error');
    throw new ApiError(response.status, response.statusText, `Failed to start analysis for ${symbol}`);
  }

  const { task_id } = await response.json();

  // SSE 连接函数（支持重试）
  const connectSSE = async (retryCount: number = 0): Promise<void> => {
    if (aborted) {
      onConnectionState?.('closed');
      return;
    }

    return new Promise((resolve, reject) => {
      const eventSource = new EventSource(`${API_BASE}/analyze/stream/${task_id}`);
      currentEventSource = eventSource;

      let hasReceivedData = false;
      let isCompleted = false;

      const stages = ['stage_analyst', 'stage_debate', 'stage_risk', 'stage_final', 'error', 'progress'];

      // 连接成功时触发
      eventSource.onopen = () => {
        if (retryCount > 0) {
          console.info(`SSE reconnected after ${retryCount} retries`);
        }
        onConnectionState?.('connected');
      };

      stages.forEach((stage) => {
        eventSource.addEventListener(stage, (event: MessageEvent) => {
          hasReceivedData = true;

          try {
            const data = JSON.parse(event.data);
            onEvent(stage, data);

            if (stage === 'stage_final' || stage === 'error') {
              isCompleted = true;
              eventSource.close();
              currentEventSource = null;
              onConnectionState?.('closed');
              resolve();
            }
          } catch (parseError) {
            console.error('Failed to parse SSE data:', parseError);
          }
        });
      });

      eventSource.onerror = async (err) => {
        eventSource.close();
        currentEventSource = null;

        // 已完成或已中止，不重试
        if (isCompleted || aborted) {
          onConnectionState?.('closed');
          resolve();
          return;
        }

        // 检查是否可以重试
        if (retryCount < maxRetries) {
          const delay = getBackoffDelay(retryCount);
          console.warn(`SSE connection error, retrying in ${delay}ms (attempt ${retryCount + 1}/${maxRetries})`, err);

          onConnectionState?.('reconnecting', retryCount + 1);

          await sleep(delay);

          if (!aborted) {
            try {
              await connectSSE(retryCount + 1);
              resolve();
            } catch (retryError) {
              reject(retryError);
            }
          } else {
            onConnectionState?.('closed');
            resolve();
          }
        } else {
          // 达到最大重试次数
          console.error(`SSE connection failed after ${maxRetries} retries`);
          onConnectionState?.('error');
          onEvent('error', {
            message: `连接失败，已重试 ${maxRetries} 次`,
            code: 'SSE_MAX_RETRIES_EXCEEDED',
          });
          reject(new Error(`SSE connection failed after ${maxRetries} retries`));
        }
      };
    });
  };

  // 启动 SSE 连接（异步，不阻塞返回控制器）
  connectSSE().catch((error) => {
    console.error('SSE connection failed:', error);
  });

  return controller;
};

/**
 * 获取最新分析结果
 */
export const getLatestAnalysis = (symbol: string) =>
  request<any>(`/analyze/latest/${symbol}`);

/**
 * 获取分析历史
 */
export const getAnalysisHistory = (symbol: string, limit: number = 10) =>
  request<any[]>(`/analyze/history/${symbol}?limit=${limit}`);

/**
 * 获取分析任务状态
 */
export const getAnalysisStatus = (taskId: string) =>
  request<any>(`/analyze/status/${taskId}`);

// ============ 监听列表 API ============

export const getWatchlist = () => request<any[]>('/watchlist/');

export const addToWatchlist = (symbol: string) =>
  request<any>(`/watchlist/${symbol}`, { method: 'POST' });

export const removeFromWatchlist = (symbol: string) =>
  request<any>(`/watchlist/${symbol}`, { method: 'DELETE' });

// ============ 市场数据 API ============

export const getMarketPrice = (symbol: string) =>
  request<any>(`/market/price/${symbol}`);

export const getMarketHistory = (symbol: string, period: string = '1mo') =>
  request<any[]>(`/market/history/${symbol}?period=${period}`);

export const getGlobalMarket = () => request<any>('/market/global');

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
  request<any[]>(`/news/${symbol}`);

// ============ 聊天 API ============

export const getChatResponse = (threadId: string, message: string) =>
  request<any>(`/chat/${threadId}?message=${encodeURIComponent(message)}`, {
    method: 'POST',
  });

export const getChatHistory = (threadId: string) =>
  request<any[]>(`/chat/${threadId}`);

// ============ Prompt 管理 API ============

export interface PromptConfig {
  system: string;
  user: string;
}

export const getPrompts = () => request<{ prompts: Record<string, PromptConfig>; path: string }>('/settings/prompts');

export const getPromptByRole = (role: string) =>
  request<PromptConfig>(`/settings/prompts/${role}`);

export const updatePromptByRole = (role: string, config: PromptConfig, apiKey?: string) =>
  request<any>(`/settings/prompts/${role}`, {
    method: 'PUT',
    headers: apiKey ? { 'X-API-Key': apiKey } : undefined,
    body: JSON.stringify(config),
  });

export const updateAllPrompts = (prompts: Record<string, PromptConfig>, apiKey?: string) =>
  request<any>('/settings/prompts', {
    method: 'PUT',
    headers: apiKey ? { 'X-API-Key': apiKey } : undefined,
    body: JSON.stringify({ prompts }),
  });

export const reloadPrompts = () =>
  request<any>('/settings/prompts/reload', { method: 'POST' });

// ============ Portfolio 分析 API ============

export const getPortfolioCorrelation = (symbols: string[], period: string = '1mo') =>
  request<any>('/portfolio/correlation', {
    method: 'POST',
    body: JSON.stringify({ symbols, period }),
  });

export const getPortfolioAnalysis = (symbols: string[], period: string = '1mo') =>
  request<any>('/portfolio/analyze', {
    method: 'POST',
    body: JSON.stringify({ symbols, period }),
  });

export const getQuickPortfolioCheck = (symbols: string[]) =>
  request<any>(`/portfolio/quick-check?symbols=${symbols.join(',')}`);

// ============ 宏观经济 API ============

export const getMacroOverview = () => request<any>('/macro/overview');

export const getMacroIndicator = (name: string) =>
  request<any>(`/macro/indicator/${name}`);

export const getMacroImpactAnalysis = (market?: string) => {
  const query = market ? `?market=${market}` : '';
  return request<any>(`/macro/impact-analysis${query}`);
};

export const refreshMacro = () =>
  request<any>('/macro/refresh', { method: 'POST' });

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
  request<any>('/memory/store', {
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

