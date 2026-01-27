/**
 * 记忆服务 Hooks
 *
 * 提供分析记忆的存储、检索和反思功能
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getMemoryStatus,
  getMemoryRetrieve,
  getReflection,
  storeMemory,
  clearMemory,
  searchMemory,
} from '../services/api';
import type { AnalysisMemory, MemoryRetrievalResult, ReflectionReport } from '../types';

export const MEMORY_KEY = ['memory'];

/**
 * 获取记忆服务状态
 */
export function useMemoryStatus() {
  return useQuery({
    queryKey: [...MEMORY_KEY, 'status'],
    queryFn: getMemoryStatus,
    staleTime: 5 * 60 * 1000, // 5分钟
  });
}

/**
 * 检索股票的历史分析记忆
 */
export function useMemoryRetrieve(
  symbol: string,
  nResults: number = 5,
  maxDays: number = 365
) {
  return useQuery({
    queryKey: [...MEMORY_KEY, 'retrieve', symbol, nResults, maxDays],
    queryFn: () => getMemoryRetrieve(symbol, nResults, maxDays),
    enabled: !!symbol,
    staleTime: 10 * 60 * 1000, // 10分钟
  });
}

/**
 * 获取股票的反思报告
 */
export function useReflection(symbol: string) {
  return useQuery({
    queryKey: [...MEMORY_KEY, 'reflection', symbol],
    queryFn: () => getReflection(symbol),
    enabled: !!symbol,
    staleTime: 30 * 60 * 1000, // 30分钟
  });
}

/**
 * 搜索记忆
 */
export function useMemorySearch(query: string, nResults: number = 10) {
  return useQuery({
    queryKey: [...MEMORY_KEY, 'search', query, nResults],
    queryFn: () => searchMemory(query, nResults),
    enabled: query.length > 0,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * 存储分析记忆
 */
export function useStoreMemory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (memory: AnalysisMemory) => storeMemory(memory),
    onSuccess: (_, variables) => {
      // 使该股票的记忆查询失效
      queryClient.invalidateQueries({
        queryKey: [...MEMORY_KEY, 'retrieve', variables.symbol],
      });
      queryClient.invalidateQueries({
        queryKey: [...MEMORY_KEY, 'reflection', variables.symbol],
      });
      queryClient.invalidateQueries({
        queryKey: [...MEMORY_KEY, 'status'],
      });
    },
  });
}

/**
 * 清除记忆
 */
export function useClearMemory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (symbol?: string) => clearMemory(symbol),
    onSuccess: () => {
      // 使所有记忆查询失效
      queryClient.invalidateQueries({ queryKey: MEMORY_KEY });
    },
  });
}
