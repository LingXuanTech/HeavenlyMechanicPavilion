/**
 * API 服务层 - 统一管理所有后端 API 调用
 *
 * 设计原则：
 * 1. 所有 API 调用集中在此文件
 * 2. 统一错误处理
 * 3. 类型安全
 */

import { logger } from '../utils/logger';
import { API_BASE as SHARED_API_BASE } from '../config/api';

import type * as T from '../src/types/schema';

// 暂时保留旧的导入，直到全部替换完成

/** SSE 事件数据类型 */
export type SSEEventData = Record<string, unknown>;

// ============ 基础配置 ============

export const API_BASE = SHARED_API_BASE;

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
export async function request<T>(
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
  request<T.AgentAnalysis>(`/analyze/latest/${symbol}`);

/**
 * 快速扫描（L1 模式）
 *
 * 仅运行 Market + News + Macro 三个分析师，跳过辩论和风险评估。
 */
export const quickScanStock = (symbol: string) =>
  request<T.ApiResponse<'/api/analyze/quick/{symbol}', 'post'>>(`/analyze/quick/${symbol}`, { method: 'POST' });

/**
 * 获取分析历史
 */
export const getAnalysisHistory = (symbol: string, limit: number = 10) =>
  request<T.ApiResponse<'/api/analyze/history/{symbol}'>>(`/analyze/history/${symbol}?limit=${limit}&status=completed`);

/**
 * 获取指定 ID 的完整分析报告
 */
export const getAnalysisDetail = (analysisId: number) =>
  request<T.ApiResponse<'/api/analyze/detail/{analysis_id}'>>(`/analyze/detail/${analysisId}`);

/**
 * 获取分析任务状态
 */
export const getAnalysisStatus = (taskId: string) =>
  request<T.AnalysisTaskStatus>(`/analyze/status/${taskId}`);

// ============ 监听列表 API ============

export const getWatchlist = () => request<T.Watchlist[]>('/watchlist/');

export const addToWatchlist = (symbol: string) =>
  request<T.Watchlist>(`/watchlist/${symbol}`, { method: 'POST' });

export const removeFromWatchlist = (symbol: string) =>
  request<{ deleted: boolean }>(`/watchlist/${symbol}`, { method: 'DELETE' });

// ============ 市场数据 API ============

export const getMarketPrice = (symbol: string) =>
  request<T.StockPrice>(`/market/price/${symbol}`);

export const getMarketHistory = (symbol: string, period: string = '1mo') =>
  request<T.KlineData[]>(`/market/history/${symbol}?period=${period}`);

export const getMarketKline = (symbol: string, days: number = 90) =>
  request<{ data: T.KlineData[]; symbol: string }>(`/market/kline/${encodeURIComponent(symbol)}?days=${days}`);

export const getGlobalMarket = () => request<T.MarketOverview>('/market/global');

// ============ 发现 API ============

export const discoverStocks = async (query: string): Promise<T.MarketOpportunity[]> => {
  const data = await request<{ results: T.MarketOpportunity[] }>(
    `/discover/?query=${encodeURIComponent(query)}`
  );
  return data.results;
};

// ============ 新闻 API (旧版) ============

export const getFlashNews = () => request<T.FlashNews[]>('/news/flash');

export const getStockNews = (symbol: string) =>
  request<T.FlashNews[]>(`/news/${symbol}`);

// ============ 聊天 API ============

export const getChatResponse = (threadId: string, message: string) =>
  request<T.ChatMessage>(`/chat/${threadId}?message=${encodeURIComponent(message)}`, {
    method: 'POST',
  });

export const getChatHistory = (threadId: string) =>
  request<T.ChatMessage[]>(`/chat/${threadId}`);

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

export type PortfolioPeriod = '1d' | '5d' | '1mo' | '3mo' | '6mo' | '1y';
export type PortfolioRiskProfile = 'conservative' | 'balanced' | 'aggressive';

export interface PortfolioRebalanceConstraints {
  maxSingleWeight?: number;
  maxTop2Weight?: number;
  maxTurnover?: number;
  riskProfile?: PortfolioRiskProfile;
}

export interface PortfolioAnalysisOptions {
  period?: PortfolioPeriod;
  clusterThreshold?: number;
  weights?: number[];
  constraints?: PortfolioRebalanceConstraints;
  enableBacktestHint?: boolean;
}

export interface BacktestSignalPayload {
  date: string;
  signal: string;
  confidence?: number;
  source?: string;
}

export interface BacktestRunRequest {
  symbol: string;
  signals?: BacktestSignalPayload[];
  initial_capital?: number;
  holding_days?: number;
  stop_loss_pct?: number;
  take_profit_pct?: number;
  use_historical_signals?: boolean;
  days_back?: number;
}

export interface BacktestRunResult {
  symbol: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_capital: number;
  total_return_pct: number;
  annualized_return_pct: number;
  max_drawdown_pct: number;
  sharpe_ratio: number | null;
  win_rate: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  avg_win_pct: number;
  avg_loss_pct: number;
  profit_factor: number | null;
  benchmark_return_pct: number | null;
  alpha: number | null;
  error: string | null;
  trades: Array<Record<string, unknown>>;
}

export interface BacktestRunResponse {
  status: string;
  result: BacktestRunResult;
}

export interface BacktestBackgroundResponse {
  status: string;
  symbol: string;
  message: string;
}

export interface BacktestHistoryItem {
  id: number;
  period: string;
  total_return_pct: number;
  win_rate: string;
  total_trades: number;
  max_drawdown_pct: number;
  sharpe_ratio: number | null;
  alpha: number | null;
  created_at: string;
}

export interface BacktestHistoryResponse {
  status: string;
  symbol: string;
  count: number;
  history: BacktestHistoryItem[];
}

export interface BacktestDetailTrade {
  entry_date: string;
  entry_price: number;
  signal: string;
  confidence: number;
  exit_date?: string | null;
  exit_price?: number | null;
  return_pct?: number | null;
  is_winner?: boolean | null;
  holding_days?: number | null;
  notes?: string;
}

export interface BacktestDetailResponse {
  status: string;
  symbol: string;
  period: string;
  initial_capital: number;
  final_capital: number;
  total_return_pct: number;
  annualized_return_pct: number;
  max_drawdown_pct: number;
  sharpe_ratio: number | null;
  win_rate: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  avg_win_pct: number;
  avg_loss_pct: number;
  profit_factor: number | null;
  benchmark_return_pct: number | null;
  alpha: number | null;
  trades: BacktestDetailTrade[];
  config: {
    holding_days: number;
    stop_loss_pct: number;
    take_profit_pct: number;
  };
  created_at: string;
}

interface NormalizedPortfolioAnalysisOptions {
  period: PortfolioPeriod;
  clusterThreshold: number;
  weights?: number[];
  constraints?: {
    max_single_weight: number;
    max_top2_weight: number;
    max_turnover: number;
    risk_profile: PortfolioRiskProfile;
  };
  enableBacktestHint: boolean;
}

const DEFAULT_PORTFOLIO_PERIOD: PortfolioPeriod = '1mo';
const DEFAULT_CLUSTER_THRESHOLD = 0.7;
const DEFAULT_PORTFOLIO_CONSTRAINTS = {
  maxSingleWeight: 0.45,
  maxTop2Weight: 0.65,
  maxTurnover: 0.35,
  riskProfile: 'balanced' as PortfolioRiskProfile,
};

const clampValue = (value: number, min: number, max: number): number =>
  Math.min(max, Math.max(min, value));

const normalizePortfolioOptions = (
  options: PortfolioAnalysisOptions = {}
): NormalizedPortfolioAnalysisOptions => {
  const normalizedWeights =
    options.weights
      ?.map((weight) => Number(weight))
      .filter((weight) => Number.isFinite(weight)) ?? undefined;

  const constraints = options.constraints
    ? {
        max_single_weight: clampValue(
          Number(options.constraints.maxSingleWeight ?? DEFAULT_PORTFOLIO_CONSTRAINTS.maxSingleWeight),
          0.1,
          0.9
        ),
        max_top2_weight: clampValue(
          Number(options.constraints.maxTop2Weight ?? DEFAULT_PORTFOLIO_CONSTRAINTS.maxTop2Weight),
          0.2,
          1
        ),
        max_turnover: clampValue(
          Number(options.constraints.maxTurnover ?? DEFAULT_PORTFOLIO_CONSTRAINTS.maxTurnover),
          0,
          1
        ),
        risk_profile: options.constraints.riskProfile ?? DEFAULT_PORTFOLIO_CONSTRAINTS.riskProfile,
      }
    : undefined;

  return {
    period: options.period ?? DEFAULT_PORTFOLIO_PERIOD,
    clusterThreshold: options.clusterThreshold ?? DEFAULT_CLUSTER_THRESHOLD,
    weights: normalizedWeights?.length ? normalizedWeights : undefined,
    constraints,
    enableBacktestHint: options.enableBacktestHint ?? true,
  };
};

export const getPortfolioCorrelation = (
  symbols: string[],
  options: PortfolioAnalysisOptions = {}
) => {
  const { period, weights } = normalizePortfolioOptions(options);

  return request<T.CorrelationResult>('/portfolio/correlation', {
    method: 'POST',
    body: JSON.stringify({
      symbols,
      period,
      ...(weights ? { weights } : {}),
    }),
  });
};

export const getPortfolioAnalysis = (
  symbols: string[],
  options: PortfolioAnalysisOptions = {}
) => {
  const { period, clusterThreshold, weights, constraints, enableBacktestHint } =
    normalizePortfolioOptions(options);

  return request<T.PortfolioAnalysis>('/portfolio/analyze', {
    method: 'POST',
    body: JSON.stringify({
      symbols,
      period,
      cluster_threshold: clusterThreshold,
      ...(weights ? { weights } : {}),
      ...(constraints ? { constraints } : {}),
      enable_backtest_hint: enableBacktestHint,
    }),
  });
};

export const getQuickPortfolioCheck = (
  symbols: string[],
  options: PortfolioAnalysisOptions = {}
) => {
  const { period, clusterThreshold, weights } = normalizePortfolioOptions(options);
  const query = new URLSearchParams({
    symbols: symbols.join(','),
    period,
    cluster_threshold: clusterThreshold.toString(),
  });

  if (weights?.length) {
    query.set('weights', weights.join(','));
  }

  return request<T.QuickPortfolioCheck>(`/portfolio/quick-check?${query.toString()}`);
};

// ============ Backtest API ============

export const runBacktest = (payload: BacktestRunRequest) =>
  request<BacktestRunResponse>('/backtest/run', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

export const runBacktestInBackground = (payload: BacktestRunRequest) =>
  request<BacktestBackgroundResponse>('/backtest/run/background', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

export const getBacktestHistory = (symbol: string, limit: number = 10) =>
  request<BacktestHistoryResponse>(
    `/backtest/history/${encodeURIComponent(symbol)}?limit=${limit}`
  );

export const getBacktestDetail = (symbol: string, recordId: number) =>
  request<BacktestDetailResponse>(
    `/backtest/history/${encodeURIComponent(symbol)}/${recordId}`
  );

// ============ 宏观经济 API ============

export const getMacroOverview = () => request<T.MacroOverview>('/macro/overview');

export const getMacroIndicator = (name: string) =>
  request<Record<string, unknown>>(`/macro/indicator/${name}`);

export const getMacroImpactAnalysis = (market?: string) => {
  const query = market ? `?market=${market}` : '';
  return request<T.MacroImpactAnalysis>(`/macro/impact-analysis${query}`);
};

export const refreshMacro = () =>
  request<T.ApiResponse<'/api/macro/refresh', 'post'>>('/macro/refresh', { method: 'POST' });

// ============ 记忆服务 API ============

export const getMemoryStatus = () =>
  request<T.ApiResponse<'/api/memory/status'>>('/memory/status');

export const getMemoryRetrieve = (symbol: string, nResults: number = 5, maxDays: number = 365) =>
  request<T.MemoryRetrievalResult[]>(
    `/memory/retrieve/${symbol}?n_results=${nResults}&max_days=${maxDays}`
  );

export const getReflection = (symbol: string) =>
  request<T.ReflectionReport | null>(`/memory/reflection/${symbol}`);

export const storeMemory = (memory: T.AnalysisMemory) =>
  request<T.ApiResponse<'/api/memory/store', 'post'>>('/memory/store', {
    method: 'POST',
    body: JSON.stringify(memory),
  });

export const clearMemory = (symbol?: string) => {
  const query = symbol ? `?symbol=${symbol}` : '';
  return request<T.ApiResponse<'/api/memory/clear', 'delete'>>(`/memory/clear${query}`, { method: 'DELETE' });
};

export const searchMemory = (query: string, nResults: number = 10) =>
  request<T.ApiResponse<'/api/memory/search'>>(
    `/memory/search?query=${encodeURIComponent(query)}&n_results=${nResults}`
  );

// ============ 市场监控 API ============

export const getMarketWatcherStatus = () =>
  request<T.ApiResponse<'/api/market-watcher/status'>>('/market-watcher/status');

export const getMarketWatcherOverview = (forceRefresh: boolean = false) =>
  request<T.MarketOverview>(
    `/market-watcher/overview${forceRefresh ? '?force_refresh=true' : ''}`
  );

export const getMarketIndices = (region?: T.MarketRegion, forceRefresh: boolean = false) => {
  const params = new URLSearchParams();
  if (region) params.append('region', region);
  if (forceRefresh) params.append('force_refresh', 'true');
  const query = params.toString() ? `?${params.toString()}` : '';
  return request<T.MarketIndex[]>(`/market-watcher/indices${query}`);
};

export const getMarketIndex = (code: string) =>
  request<T.MarketIndex>(`/market-watcher/index/${code}`);

export const refreshMarketIndices = () =>
  request<T.ApiResponse<'/api/market-watcher/refresh', 'post'>>('/market-watcher/refresh', { method: 'POST' });

export const getMarketSentiment = () =>
  request<T.MarketSentiment>('/market-watcher/sentiment');

// ============ 新闻聚合 API ============

export const getNewsAggregatorStatus = () =>
  request<T.ApiResponse<'/api/news-aggregator/status'>>('/news-aggregator/status');

export const getAggregatedNews = (forceRefresh: boolean = false) =>
  request<T.NewsAggregateResult>(
    `/news-aggregator/all${forceRefresh ? '?force_refresh=true' : ''}`
  );

export const getNewsFlashAggregated = (limit: number = 10) =>
  request<T.AggregatedNewsItem[]>(`/news-aggregator/flash?limit=${limit}`);

export const getNewsByCategory = (category: T.NewsCategory, limit: number = 20) =>
  request<T.AggregatedNewsItem[]>(`/news-aggregator/category/${category}?limit=${limit}`);

export const getNewsBySymbol = (symbol: string, limit: number = 20) =>
  request<T.AggregatedNewsItem[]>(`/news-aggregator/symbol/${symbol}?limit=${limit}`);

export const refreshAggregatedNews = () =>
  request<T.ApiResponse<'/api/news-aggregator/refresh', 'post'>>('/news-aggregator/refresh', { method: 'POST' });

export const getNewsSources = () =>
  request<T.ApiResponse<'/api/news-aggregator/sources'>>('/news-aggregator/sources');

// ============ 健康监控 API ============

export const getHealthQuick = () =>
  request<T.ApiResponse<'/api/health/'>>('/health/');

export const getHealthReport = (forceRefresh: boolean = false) =>
  request<T.HealthReport>(`/health/report${forceRefresh ? '?force_refresh=true' : ''}`);

export const getHealthComponents = () =>
  request<T.ApiResponse<'/api/health/components'>>('/health/components');

export const getHealthMetrics = () =>
  request<T.SystemMetrics>('/health/metrics');

export const getHealthErrors = (limit: number = 10) =>
  request<T.ApiResponse<'/api/health/errors'>>(`/health/errors?limit=${limit}`);

export const clearHealthErrors = () =>
  request<T.ApiResponse<'/api/health/errors', 'delete'>>('/health/errors', { method: 'DELETE' });

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

export const resetCircuitBreaker = (provider: string) =>
  request<{ status: string; message: string }>(`/health/reset-circuit-breaker/${provider}`, {
    method: 'POST',
  });

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

export const createAIProvider = (data: T.ApiRequestBody<'/api/ai/providers', 'post'>) =>
  request<T.AIProvider>('/ai/providers', {
    method: 'POST',
    body: JSON.stringify(data),
  });

export const updateAIProvider = (
  providerId: number,
  data: T.ApiRequestBody<'/api/ai/providers/{provider_id}', 'put'>
) =>
  request<T.AIProvider>(`/ai/providers/${providerId}`, {
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
  request<T.ModelConfigListResponse>('/ai/models');

export const updateAIModelConfig = (
  configKey: string,
  data: T.ApiRequestBody<'/api/ai/models/{config_key}', 'put'>
) =>
  request<T.AIModelConfig>(`/ai/models/${configKey}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });

// 管理操作
export const refreshAIConfig = () =>
  request<{ refreshed: boolean }>('/ai/refresh', { method: 'POST' });

export const getAIConfigStatus = () =>
  request<T.AIConfigStatus>('/ai/status');

// ============ 北向资金 API (A股特有) ============

export const getNorthMoneyFlow = () =>
  request<T.NorthMoneyFlow>('/north-money/flow');

export const getNorthMoneySummary = () =>
  request<T.NorthMoneySummary>('/north-money/summary');

export const getNorthMoneyHistory = (days: number = 30) =>
  request<T.NorthMoneyHistory[]>(`/north-money/history?days=${days}`);

export const getNorthMoneyHolding = (symbol: string) =>
  request<T.StockNorthHolding>(`/north-money/holding/${symbol}`);

export const getNorthMoneyTopBuys = (limit: number = 20) =>
  request<T.NorthMoneyTopStock[]>(`/north-money/top-buys?limit=${limit}`);

export const getNorthMoneyTopSells = (limit: number = 20) =>
  request<T.NorthMoneyTopStock[]>(`/north-money/top-sells?limit=${limit}`);

export const getNorthMoneyIntraday = () =>
  request<T.IntradayFlowSummary>('/north-money/intraday');

export const getNorthMoneyAnomalies = () =>
  request<T.NorthMoneyAnomaly[]>('/north-money/anomalies');

export const getNorthMoneyRealtime = () =>
  request<T.NorthMoneyRealtime>('/north-money/realtime');

export const getNorthMoneySectorFlow = () =>
  request<T.NorthMoneySectorFlow[]>('/north-money/sector-flow');

export const getNorthMoneyRotationSignal = () =>
  request<T.SectorRotationSignal>('/north-money/rotation-signal');

// ============ 龙虎榜 API (A股特有) ============

export const getLHBDaily = (tradeDate?: string) => {
  const query = tradeDate ? `?trade_date=${tradeDate}` : '';
  return request<T.LHBStock[]>(`/lhb/daily${query}`);
};

export const getLHBSummary = () =>
  request<T.LHBSummary>('/lhb/summary');

export const getLHBStockHistory = (symbol: string, days: number = 30) =>
  request<T.LHBStock[]>(`/lhb/stock/${symbol}?days=${days}`);

export const getLHBHotMoneyActivity = (days: number = 5) =>
  request<T.HotMoneySeat[]>(`/lhb/hot-money?days=${days}`);

export const getLHBTopBuys = (limit: number = 10) =>
  request<T.LHBStock[]>(`/lhb/top-buys?limit=${limit}`);

export const getLHBTopSells = (limit: number = 10) =>
  request<T.LHBStock[]>(`/lhb/top-sells?limit=${limit}`);

export const getLHBInstitutionActivity = (direction: 'buy' | 'sell' | 'all' = 'all') =>
  request<T.LHBStock[]>(`/lhb/institution-activity?direction=${direction}`);

export const getLHBHotMoneyStocks = () =>
  request<T.LHBStock[]>('/lhb/hot-money-stocks');

// ============ 限售解禁 API (A股特有) ============

export const getJiejinUpcoming = (days: number = 30) =>
  request<T.JiejinStock[]>(`/jiejin/upcoming?days=${days}`);

export const getJiejinCalendar = (days: number = 30) =>
  request<T.JiejinCalendar[]>(`/jiejin/calendar?days=${days}`);

export const getJiejinSummary = (days: number = 30) =>
  request<T.JiejinSummary>(`/jiejin/summary?days=${days}`);

export const getJiejinStockPlan = (symbol: string) =>
  request<T.JiejinStock>(`/jiejin/stock/${symbol}`);

export const getJiejinHighPressure = (days: number = 7) =>
  request<T.JiejinStock[]>(`/jiejin/high-pressure?days=${days}`);

export const getJiejinWarning = (symbol: string, days: number = 30) =>
  request<{ symbol: string; warning: boolean; message: string; upcoming: T.JiejinStock[] }>(`/jiejin/warning/${symbol}?days=${days}`);

export const getJiejinToday = () =>
  request<T.JiejinStock[]>('/jiejin/today');

export const getJiejinWeek = () =>
  request<T.JiejinStock[]>('/jiejin/week');

// ============ 产业链知识图谱 API ============

export const getChainList = () =>
  request<Record<string, unknown>>('/supply-chain/chains');

export const getChainGraph = (chainId: string) =>
  request<Record<string, unknown>>(`/supply-chain/graph/${chainId}`);

export const getStockChainPosition = (symbol: string) =>
  request<Record<string, unknown>>(`/supply-chain/stock/${encodeURIComponent(symbol)}`);

export const getSupplyChainImpact = (symbol: string) =>
  request<Record<string, unknown>>(`/supply-chain/impact/${encodeURIComponent(symbol)}`);

// ============ Vision 分析 API ============

export const analyzeVisionImage = async (
  file: File,
  description: string = '',
  symbol: string = ''
) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('description', description);
  formData.append('symbol', symbol);

  const response = await fetch(`${API_BASE}/vision/analyze`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => response.statusText);
    throw new ApiError(response.status, response.statusText, errorText);
  }

  return response.json();
};

export const getVisionHistory = (symbol?: string, limit: number = 10) => {
  const params = new URLSearchParams();
  if (symbol) params.append('symbol', symbol);
  params.append('limit', String(limit));
  return request<{ history: unknown[]; total: number }>(`/vision/history?${params.toString()}`);
};

// ============ 另类数据 API ============

export const getAHPremiumList = (sortBy: string = 'premium_rate', limit: number = 50) =>
  request<Record<string, unknown>>(`/alternative/ah-premium?sort_by=${sortBy}&limit=${limit}`);

export const getAHPremiumDetail = (symbol: string) =>
  request<Record<string, unknown>>(`/alternative/ah-premium/${encodeURIComponent(symbol)}`);

export const getPatentAnalysis = (symbol: string, companyName?: string) => {
  const params = new URLSearchParams();
  if (companyName) params.append('company_name', companyName);
  const query = params.toString() ? `?${params.toString()}` : '';
  return request<Record<string, unknown>>(`/alternative/patents/${encodeURIComponent(symbol)}${query}`);
};

// ============ Prompt 配置 API ============

/** 获取所有 Prompt 列表 */
export const getPromptList = (category?: T.AgentCategory) => {
  const query = category ? `?category=${category}` : '';
  return request<T.PromptListResponse>(`/prompts/${query}`);
};

/** 获取 Prompt 详情（含版本历史） */
export const getPromptDetail = (promptId: number) =>
  request<T.AgentPromptDetail>(`/prompts/${promptId}`);

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
  request<T.PromptServiceStatus>('/prompts/refresh', { method: 'POST' });

/** 获取 Prompt 服务状态 */
export const getPromptServiceStatus = () =>
  request<T.PromptServiceStatus>('/prompts/status');

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
