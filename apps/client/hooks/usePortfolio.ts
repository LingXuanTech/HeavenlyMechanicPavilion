/**
 * Portfolio 分析 Hooks
 *
 * 提供组合相关性分析和风险评估
 */
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  getPortfolioCorrelation,
  getPortfolioAnalysis,
  getQuickPortfolioCheck,
} from '../services/api';

export const PORTFOLIO_KEY = ['portfolio'];


/**
 * 计算组合相关性
 */
export function usePortfolioCorrelation() {
  return useMutation({
    mutationFn: (symbols: string[]) => getPortfolioCorrelation(symbols),
  });
}

/**
 * 完整组合分析
 */
export function usePortfolioAnalysis() {
  return useMutation({
    mutationFn: (symbols: string[]) => getPortfolioAnalysis(symbols),
  });
}

/**
 * 快速组合检查
 */
export function useQuickPortfolioCheck(symbols: string[]) {
  return useQuery({
    queryKey: [...PORTFOLIO_KEY, 'quick', symbols.sort().join(',')],
    queryFn: () => getQuickPortfolioCheck(symbols),
    enabled: symbols.length >= 2,
    staleTime: 5 * 60 * 1000, // 5分钟
  });
}
