/**
 * Backtest 相关 Hooks
 */
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  runBacktest,
  runBacktestInBackground,
  getBacktestHistory,
  type BacktestRunRequest,
} from '../services/api';

export const BACKTEST_KEY = ['backtest'];

/**
 * 立即执行回测（同步返回结果）
 */
export function useRunBacktest() {
  return useMutation({
    mutationFn: (payload: BacktestRunRequest) => runBacktest(payload),
  });
}

/**
 * 后台执行回测（快速返回 accepted）
 */
export function useRunBacktestInBackground() {
  return useMutation({
    mutationFn: (payload: BacktestRunRequest) => runBacktestInBackground(payload),
  });
}

/**
 * 获取回测历史
 */
export function useBacktestHistory(symbol: string, limit: number = 10) {
  return useQuery({
    queryKey: [...BACKTEST_KEY, 'history', symbol, limit],
    queryFn: () => getBacktestHistory(symbol, limit),
    enabled: Boolean(symbol),
    staleTime: 30_000,
  });
}
