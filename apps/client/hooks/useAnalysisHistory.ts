/**
 * 分析历史与对比 Hook
 *
 * 支持：
 * 1. 获取股票分析历史列表
 * 2. 加载指定分析的完整报告
 * 3. 多个分析并排对比
 */
import { useQuery, useQueries } from '@tanstack/react-query';
import { useState, useCallback, useMemo } from 'react';
import * as api from '../services/api';
import type * as T from '../src/types/schema';

// 导出类型供组件使用
export type AnalysisDetail = T.AnalysisDetailResponse;

export const ANALYSIS_HISTORY_KEY = (symbol: string) => ['analysis', 'history', symbol];
export const ANALYSIS_DETAIL_KEY = (id: number) => ['analysis', 'detail', id];


/**
 * 获取股票分析历史列表
 */
export function useAnalysisHistory(symbol: string, limit: number = 10) {
  return useQuery({
    queryKey: ANALYSIS_HISTORY_KEY(symbol),
    queryFn: async () => {
      const data = (await api.getAnalysisHistory(symbol, limit)) as {
        items: T.AnalysisHistoryItem[];
        total: number;
      };
      return {
        items: data.items,
        total: data.total,
      };
    },
    staleTime: 5 * 60 * 1000, // 5 分钟
    enabled: !!symbol,
  });
}

/**
 * 获取指定分析的完整报告
 */
export function useAnalysisDetail(analysisId: number | null) {
  return useQuery({
    queryKey: ANALYSIS_DETAIL_KEY(analysisId ?? 0),
    queryFn: async () => {
      if (!analysisId) return null;
      return (await api.getAnalysisDetail(analysisId)) as T.AnalysisDetailResponse;
    },
    staleTime: Infinity, // 历史分析不会变
    enabled: !!analysisId,
  });
}

/**
 * 分析对比 Hook
 *
 * 管理对比选择和数据加载
 */
export function useAnalysisComparison(symbol: string) {
  // 选中的分析 ID 列表（最多 3 个）
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  // 获取历史列表
  const historyQuery = useAnalysisHistory(symbol, 20);

  // 批量加载选中的完整报告
  const detailQueries = useQueries({
    queries: selectedIds.map((id) => ({
      queryKey: ANALYSIS_DETAIL_KEY(id),
      queryFn: () => api.getAnalysisDetail(id) as Promise<T.AnalysisDetailResponse>,
      staleTime: Infinity,
      enabled: !!id,
    })),
  });

  // 切换选中
  const toggleSelected = useCallback((id: number) => {
    setSelectedIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((x) => x !== id);
      }
      // 最多选 3 个
      if (prev.length >= 3) {
        return [...prev.slice(1), id];
      }
      return [...prev, id];
    });
  }, []);

  // 清除所有选中
  const clearSelection = useCallback(() => {
    setSelectedIds([]);
  }, []);

  // 已加载的完整报告
  const loadedDetails = useMemo(() => {
    return detailQueries
      .filter((q) => q.isSuccess && q.data)
      .map((q) => q.data as T.AnalysisDetailResponse);
  }, [detailQueries]);

  // 是否有报告在加载中
  const isLoading = detailQueries.some((q) => q.isLoading);

  return {
    historyQuery,
    selectedIds,
    toggleSelected,
    clearSelection,
    loadedDetails,
    isLoading,
    canCompare: selectedIds.length >= 2,
  };
}
