/**
 * SubGraph A/B 指标 Hooks
 *
 * 提供 SubGraph vs Monolith 的对比数据和灰度控制
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { request } from '../services/api';

export const SUBGRAPH_METRICS_KEY = ['subgraph-metrics'];

// 类型定义
export interface ModeStats {
  count: number;
  avg_elapsed_seconds: number | null;
  success_rate: number | null;
  avg_confidence: number | null;
  failed_count: number;
  completed_count: number;
}

export interface Recommendation {
  action: 'needs_more_data' | 'subgraph_ready' | 'monolith_better';
  reason: string;
  suggested_rollout: number;
}

export interface SubgraphComparison {
  period_days: number;
  cutoff: string;
  monolith: ModeStats;
  subgraph: ModeStats;
  recommendation: Recommendation;
  current_rollout_percentage: number;
}

export interface RolloutUpdateResult {
  previous: number;
  current: number;
  message: string;
}

/**
 * 获取 SubGraph vs Monolith 对比数据
 */
export function useSubgraphComparison(days: number = 7) {
  return useQuery({
    queryKey: [...SUBGRAPH_METRICS_KEY, 'comparison', days],
    queryFn: () => request<SubgraphComparison>(`/subgraph-metrics/comparison?days=${days}`),
    staleTime: 60 * 1000, // 1 分钟
    refetchInterval: 5 * 60 * 1000, // 5 分钟自动刷新
  });
}

/**
 * 更新灰度比例
 */
export function useUpdateRollout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (percentage: number) =>
      request<RolloutUpdateResult>('/subgraph-metrics/rollout', {
        method: 'POST',
        body: JSON.stringify({ percentage }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SUBGRAPH_METRICS_KEY });
    },
  });
}
