/**
 * 宏观经济分析 Hooks
 *
 * 提供宏观经济数据和影响分析
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getMacroOverview,
  getMacroImpactAnalysis,
  refreshMacro,
} from '../services/api';

export const MACRO_KEY = ['macro'];

/**
 * 获取宏观经济概览
 */
export function useMacroOverview() {
  return useQuery({
    queryKey: [...MACRO_KEY, 'overview'],
    queryFn: getMacroOverview,
    staleTime: 30 * 60 * 1000, // 30分钟
    refetchInterval: 60 * 60 * 1000, // 1小时自动刷新
  });
}

/**
 * 获取宏观影响分析
 */
export function useMacroImpactAnalysis(market: string = 'US') {
  return useQuery({
    queryKey: [...MACRO_KEY, 'impact', market],
    queryFn: () => getMacroImpactAnalysis(market),
    staleTime: 30 * 60 * 1000,
  });
}

/**
 * 刷新宏观数据
 */
export function useRefreshMacro() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: refreshMacro,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MACRO_KEY });
    },
  });
}
