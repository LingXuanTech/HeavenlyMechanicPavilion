import { useQuery, useQueries } from '@tanstack/react-query';
import * as api from '../services/api';
import type * as T from '../src/types/schema';

export const PRICE_KEY = (symbol: string) => ['price', symbol];
export const HISTORY_KEY = (symbol: string) => ['history', symbol];

/**
 * 获取单个股票的价格数据
 */
export function useStockPrice(symbol: string) {
  return useQuery({
    queryKey: PRICE_KEY(symbol),
    queryFn: async () => {
      const data = await api.getMarketPrice(symbol);
      return {
        price: data.price,
        change: data.change,
        changePercent: data.change_percent,
      };
    },
    staleTime: 30 * 1000, // 30秒
    // 禁用自动轮询，改为用户手动刷新（减少 API 调用）
    // refetchInterval: 30 * 1000,
    enabled: !!symbol,
  });
}

/**
 * 获取单个股票的历史数据
 */
export function useStockHistory(symbol: string) {
  return useQuery({
    queryKey: HISTORY_KEY(symbol),
    queryFn: async () => {
      const history = await api.getMarketHistory(symbol);
      return history.map((h: T.KlineData) => ({
        time: new Date(h.datetime).toLocaleDateString(),
        value: h.close,
      }));
    },
    staleTime: 5 * 60 * 1000, // 5分钟
    enabled: !!symbol,
  });
}

/**
 * 获取多个股票的价格数据（并行请求）
 */
export function useStockPrices(stocks: Array<{ symbol: string }>) {
  return useQueries({
    queries: stocks.map((stock) => ({
      queryKey: PRICE_KEY(stock.symbol),
      queryFn: async () => {
        const data = await api.getMarketPrice(stock.symbol);
        const history = await api.getMarketHistory(stock.symbol);
        return {
          symbol: stock.symbol,
          price: data.price,
          change: data.change,
          change_percent: data.change_percent,
          market: data.market,
          history: history.map((h: T.KlineData) => ({
            time: new Date(h.datetime).toLocaleDateString(),
            value: h.close,
          })),
        };
      },
      staleTime: 30 * 1000,
      // 禁用自动轮询，改为用户手动刷新（减少 API 调用）
      // refetchInterval: 30 * 1000,
    })),
    combine: (results) => {
      const prices: Record<string, T.StockPrice & { history: any[] }> = {};
      const isLoading = results.some((r) => r.isLoading);
      const errors = results.filter((r) => r.error);

      results.forEach((result) => {
        if (result.data) {
          const { symbol, ...priceData } = result.data;
          prices[symbol] = priceData as any;
        }
      });

      return { prices, isLoading, errors };
    },
  });
}
