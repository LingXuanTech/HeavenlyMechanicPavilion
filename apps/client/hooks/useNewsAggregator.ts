/**
 * 新闻聚合 Hooks
 *
 * 提供新闻聚合和快讯功能
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getNewsAggregatorStatus,
  getAggregatedNews,
  getNewsFlashAggregated,
  getNewsByCategory,
  getNewsBySymbol,
  refreshAggregatedNews,
  getNewsSources,
} from '../services/api';
import * as T from '../src/types/schema';

export const NEWS_AGGREGATOR_KEY = ['newsAggregator'];

/**
 * 获取新闻聚合服务状态
 */
export function useNewsAggregatorStatus() {
  return useQuery({
    queryKey: [...NEWS_AGGREGATOR_KEY, 'status'],
    queryFn: getNewsAggregatorStatus,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * 获取所有聚合新闻
 */
export function useAggregatedNews(forceRefresh: boolean = false) {
  return useQuery({
    queryKey: [...NEWS_AGGREGATOR_KEY, 'all', forceRefresh],
    queryFn: () => getAggregatedNews(forceRefresh),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 10 * 60 * 1000, // 10分钟自动刷新
  });
}

/**
 * 获取快讯新闻
 */
export function useNewsFlash(limit: number = 10) {
  return useQuery({
    queryKey: [...NEWS_AGGREGATOR_KEY, 'flash', limit],
    queryFn: () => getNewsFlashAggregated(limit),
    staleTime: 2 * 60 * 1000, // 2分钟
    refetchInterval: 5 * 60 * 1000, // 5分钟自动刷新
  });
}

/**
 * 按分类获取新闻
 */
export function useNewsByCategory(category: T.NewsCategory, limit: number = 20) {
  return useQuery({
    queryKey: [...NEWS_AGGREGATOR_KEY, 'category', category, limit],
    queryFn: () => getNewsByCategory(category, limit),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * 获取股票相关新闻
 */
export function useNewsBySymbol(symbol: string, limit: number = 20) {
  return useQuery({
    queryKey: [...NEWS_AGGREGATOR_KEY, 'symbol', symbol, limit],
    queryFn: () => getNewsBySymbol(symbol, limit),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * 获取新闻来源列表
 */
export function useNewsSources() {
  return useQuery({
    queryKey: [...NEWS_AGGREGATOR_KEY, 'sources'],
    queryFn: getNewsSources,
    staleTime: 30 * 60 * 1000, // 30分钟
  });
}

/**
 * 刷新聚合新闻
 */
export function useRefreshNews() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: refreshAggregatedNews,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: NEWS_AGGREGATOR_KEY });
    },
  });
}
