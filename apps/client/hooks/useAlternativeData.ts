/**
 * 另类数据 Hooks — AH 溢价 + 专利监控
 */

import { useQuery } from '@tanstack/react-query';
import { API_BASE } from '../services/api';
import type * as T from '../src/types/schema';

// ============ Query Keys ============

export const alternativeDataKeys = {
  all: ['alternative-data'] as const,
  ahPremium: () => [...alternativeDataKeys.all, 'ah-premium'] as const,
  ahPremiumList: (sortBy?: string) => [...alternativeDataKeys.ahPremium(), 'list', sortBy] as const,
  ahPremiumDetail: (symbol: string) => [...alternativeDataKeys.ahPremium(), 'detail', symbol] as const,
  patents: (symbol: string) => [...alternativeDataKeys.all, 'patents', symbol] as const,
};

// ============ Re-export Types ============
export type {
  AHPremiumStock,
  AHPremiumStats,
  AHPremiumListResponse,
  ArbitrageSignal,
  AHPremiumDetailResponse,
  PatentNewsItem,
  PatentAnalysisResponse,
} from '../src/types/schema';

// ============ Fetch Functions ============

async function fetchJSON<R>(endpoint: string): Promise<R> {
  const response = await fetch(`${API_BASE}${endpoint}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

// ============ Hooks ============

/**
 * 获取 AH 溢价排行榜
 */
export function useAHPremiumList(sortBy: string = 'premium_rate', limit: number = 50) {
  return useQuery({
    queryKey: alternativeDataKeys.ahPremiumList(sortBy),
    queryFn: () =>
      fetchJSON<T.AHPremiumListResponse>(
        `/alternative/ah-premium?sort_by=${sortBy}&limit=${limit}`
      ),
    staleTime: 5 * 60 * 1000, // 5 分钟
    refetchInterval: 5 * 60 * 1000,
  });
}

/**
 * 获取个股 AH 溢价详情
 */
export function useAHPremiumDetail(symbol: string) {
  return useQuery({
    queryKey: alternativeDataKeys.ahPremiumDetail(symbol),
    queryFn: () =>
      fetchJSON<T.AHPremiumDetailResponse>(`/alternative/ah-premium/${encodeURIComponent(symbol)}`),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * 获取公司专利分析
 */
export function usePatentAnalysis(symbol: string, companyName?: string) {
  return useQuery({
    queryKey: alternativeDataKeys.patents(symbol),
    queryFn: () => {
      const params = new URLSearchParams();
      if (companyName) params.append('company_name', companyName);
      const query = params.toString() ? `?${params.toString()}` : '';
      return fetchJSON<T.PatentAnalysisResponse>(
        `/alternative/patents/${encodeURIComponent(symbol)}${query}`
      );
    },
    enabled: !!symbol,
    staleTime: 60 * 60 * 1000, // 1 小时
  });
}
