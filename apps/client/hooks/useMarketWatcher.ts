/**
 * 市场监控 Hooks
 *
 * 提供全球市场指数实时监控功能
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getMarketWatcherStatus,
  getMarketWatcherOverview,
  getMarketIndices,
  getMarketIndex,
  refreshMarketIndices,
  getMarketSentiment,
} from '../services/api';
import * as T from '../src/types/schema';

export const MARKET_WATCHER_KEY = ['marketWatcher'];

/**
 * 获取市场监控服务状态
 */
export function useMarketWatcherStatus() {
  return useQuery({
    queryKey: [...MARKET_WATCHER_KEY, 'status'],
    queryFn: getMarketWatcherStatus,
    staleTime: 60 * 1000, // 1分钟
  });
}

/**
 * 获取市场概览（包含所有指数和情绪）
 */
export function useMarketWatcherOverview(forceRefresh: boolean = false) {
  return useQuery({
    queryKey: [...MARKET_WATCHER_KEY, 'overview', forceRefresh],
    queryFn: () => getMarketWatcherOverview(forceRefresh),
    staleTime: 60 * 1000, // 1分钟
    refetchInterval: 5 * 60 * 1000, // 5分钟自动刷新
  });
}

/**
 * 获取市场指数列表
 */
export function useMarketIndices(region?: T.MarketRegion, forceRefresh: boolean = false) {
  return useQuery({
    queryKey: [...MARKET_WATCHER_KEY, 'indices', region, forceRefresh],
    queryFn: () => getMarketIndices(region, forceRefresh),
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });
}

/**
 * 获取单个指数详情
 */
export function useMarketIndex(code: string) {
  return useQuery({
    queryKey: [...MARKET_WATCHER_KEY, 'index', code],
    queryFn: () => getMarketIndex(code),
    enabled: !!code,
    staleTime: 60 * 1000,
  });
}

/**
 * 获取市场情绪
 */
export function useMarketSentiment() {
  return useQuery({
    queryKey: [...MARKET_WATCHER_KEY, 'sentiment'],
    queryFn: getMarketSentiment,
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });
}

/**
 * 刷新市场指数数据
 */
export function useRefreshMarketIndices() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: refreshMarketIndices,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MARKET_WATCHER_KEY });
    },
  });
}
