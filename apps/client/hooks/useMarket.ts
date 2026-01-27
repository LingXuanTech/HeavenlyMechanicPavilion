import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import * as api from '../services/api';
import { GlobalMarketAnalysis, FlashNews } from '../types';

export const GLOBAL_MARKET_KEY = ['globalMarket'];
export const FLASH_NEWS_KEY = ['flashNews'];

/**
 * 获取全球市场数据
 */
export function useGlobalMarket() {
  return useQuery({
    queryKey: GLOBAL_MARKET_KEY,
    queryFn: async (): Promise<GlobalMarketAnalysis> => {
      const globalData = await api.getGlobalMarket();
      return {
        sentiment: globalData.sentiment || 'Neutral',
        summary: globalData.summary || 'Market data from backend',
        indices: globalData.indices.map((idx: any) => ({
          name: idx.name,
          value: idx.value,
          change: idx.change,
          changePercent: idx.change_percent,
        })),
        lastUpdated: new Date().toLocaleTimeString(),
      };
    },
    staleTime: 2 * 60 * 1000, // 2分钟
    refetchOnWindowFocus: true,
  });
}

/**
 * 获取闪讯数据
 */
export function useFlashNews() {
  return useQuery({
    queryKey: FLASH_NEWS_KEY,
    queryFn: async (): Promise<FlashNews[]> => {
      return api.getFlashNews();
    },
    staleTime: 5 * 60 * 1000, // 5分钟
    refetchInterval: 5 * 60 * 1000, // 每5分钟自动刷新
  });
}

/**
 * 市场状态管理
 */
export function useMarketStatus() {
  const queryClient = useQueryClient();

  const refreshGlobalMarket = useCallback(() => {
    return queryClient.invalidateQueries({ queryKey: GLOBAL_MARKET_KEY });
  }, [queryClient]);

  const refreshFlashNews = useCallback(() => {
    return queryClient.invalidateQueries({ queryKey: FLASH_NEWS_KEY });
  }, [queryClient]);

  return {
    refreshGlobalMarket,
    refreshFlashNews,
  };
}
