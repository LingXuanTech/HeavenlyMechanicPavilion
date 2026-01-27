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
  SystemMetrics,
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
 * 触发股票分析（SSE 流式）
 */
export const analyzeStockWithAgent = async (
  symbol: string,
  onEvent: (event: string, data: any) => void
): Promise<void> => {
  const response = await fetch(`${API_BASE}/analyze/${symbol}`, {
    method: 'POST',
  });

  const { task_id } = await response.json();

  const eventSource = new EventSource(`${API_BASE}/analyze/stream/${task_id}`);

  const stages = ['stage_analyst', 'stage_debate', 'stage_risk', 'stage_final', 'error', 'progress'];

  stages.forEach((stage) => {
    eventSource.addEventListener(stage, (event: any) => {
      const data = JSON.parse(event.data);
      onEvent(stage, data);

      if (stage === 'stage_final' || stage === 'error') {
        eventSource.close();
      }
    });
  });

  eventSource.onerror = (err) => {
    console.error('SSE Error:', err);
    eventSource.close();
  };
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
  return request<any>(`/memory/clear${query}`, { method: 'DELETE' });
};

export const searchMemory = (query: string, nResults: number = 10) =>
  request<{ query: string; results: any[]; count: number }>(
    `/memory/search?query=${encodeURIComponent(query)}&n_results=${nResults}`
  );

// ============ 市场监控 API ============

export const getMarketWatcherStatus = () =>
  request<any>('/market-watcher/status');

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
  request<any>('/market-watcher/refresh', { method: 'POST' });

export const getMarketSentiment = () =>
  request<{
    global_sentiment: string;
    risk_level: number;
    regions: Record<string, any>;
    updated_at: string;
  }>('/market-watcher/sentiment');

// ============ 新闻聚合 API ============

export const getNewsAggregatorStatus = () =>
  request<any>('/news-aggregator/status');

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
  request<any>('/news-aggregator/refresh', { method: 'POST' });

export const getNewsSources = () =>
  request<{ rss_feeds: any[]; finnhub_enabled: boolean; total_sources: number }>(
    '/news-aggregator/sources'
  );

// ============ 健康监控 API ============

export const getHealthQuick = () =>
  request<{ status: string; uptime_seconds: number }>('/health/');

export const getHealthReport = (forceRefresh: boolean = false) =>
  request<HealthReport>(`/health/report${forceRefresh ? '?force_refresh=true' : ''}`);

export const getHealthComponents = () =>
  request<{ overall: string; components: Record<string, any> }>('/health/components');

export const getHealthMetrics = () =>
  request<{
    cpu: { percent: number };
    memory: { percent: number; used_mb: number; total_mb: number };
    disk: { percent: number; used_gb: number; total_gb: number };
  }>('/health/metrics');

export const getHealthErrors = (limit: number = 10) =>
  request<{ errors: any[]; total: number }>(`/health/errors?limit=${limit}`);

export const clearHealthErrors = () =>
  request<any>('/health/errors', { method: 'DELETE' });

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
  request<any>('/admin/trigger-daily-analysis', { method: 'POST' });

export const getSchedulerJobs = () => request<any[]>('/admin/scheduler/jobs');

export const getSchedulerStatus = () => request<any>('/admin/scheduler/status');
