import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '../services/api';
import type * as T from '../src/types/schema';

const INITIAL_STOCKS: T.Watchlist[] = [
  { symbol: '600276.SH', name: 'Jiangsu Hengrui', market: 'CN' },
  { symbol: '603993.SH', name: 'China Moly', market: 'CN' },
  { symbol: '00700.HK', name: 'Tencent', market: 'HK' },
  { symbol: 'AAPL', name: 'Apple Inc.', market: 'US' },
  { symbol: 'NVDA', name: 'NVIDIA Corp', market: 'US' },
  { symbol: '000002.SZ', name: 'China Vanke', market: 'CN' },
];

export const WATCHLIST_KEY = ['watchlist'];

/**
 * 获取 Watchlist 数据
 * - 5分钟 staleTime 减少不必要的重新请求
 * - 初次加载时自动填充初始数据
 */
export function useWatchlist() {
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: WATCHLIST_KEY,
    queryFn: async () => {
      const data = await api.getWatchlist();
      if (data.length === 0) {
        // 如果为空，初始化默认股票
        for (const s of INITIAL_STOCKS) {
          await api.addToWatchlist(s.symbol);
        }
        return api.getWatchlist();
      }
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5分钟
    gcTime: 30 * 60 * 1000, // 30分钟
    placeholderData: INITIAL_STOCKS,
  });
}

/**
 * 添加股票到 Watchlist
 */
export function useAddStock() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (symbol: string) => {
      return api.addToWatchlist(symbol);
    },
    onSuccess: (newStock) => {
      queryClient.setQueryData<T.Watchlist[]>(WATCHLIST_KEY, (old) => {
        if (!old) return [newStock];
        // 避免重复
        if (old.some((s) => s.symbol === newStock.symbol)) return old;
        return [...old, newStock];
      });
    },
  });
}

/**
 * 从 Watchlist 移除股票
 */
export function useRemoveStock() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (symbol: string) => {
      await api.removeFromWatchlist(symbol);
      return symbol;
    },
    onSuccess: (symbol) => {
      queryClient.setQueryData<T.Watchlist[]>(WATCHLIST_KEY, (old) => {
        if (!old) return [];
        return old.filter((s) => s.symbol !== symbol);
      });
    },
  });
}
