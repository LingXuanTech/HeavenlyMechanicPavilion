/**
 * 调度器管理 Hook
 *
 * 提供调度任务状态查询和操作功能
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getSchedulerJobs, getSchedulerStatus, triggerDailyAnalysis } from '../services/api';

// ============ 类型定义 ============

export interface SchedulerJob {
  id: string;
  next_run_time: string | null;
  trigger: string;
}

export interface SchedulerStatus {
  running: boolean;
  analysis_in_progress: boolean;
  jobs_count: number;
}

export interface SchedulerJobsResponse {
  jobs: SchedulerJob[];
}

// ============ Query Keys ============

export const SCHEDULER_KEY = ['scheduler'] as const;

// ============ Hooks ============

/**
 * 获取调度器状态
 */
export function useSchedulerStatus() {
  return useQuery<SchedulerStatus>({
    queryKey: [...SCHEDULER_KEY, 'status'],
    queryFn: getSchedulerStatus,
    staleTime: 30 * 1000, // 30秒
    refetchInterval: 60 * 1000, // 每分钟刷新
  });
}

/**
 * 获取所有调度任务
 */
export function useSchedulerJobs() {
  return useQuery<SchedulerJobsResponse>({
    queryKey: [...SCHEDULER_KEY, 'jobs'],
    queryFn: getSchedulerJobs,
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  });
}

/**
 * 触发每日分析
 */
export function useTriggerDailyAnalysis() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: triggerDailyAnalysis,
    onSuccess: () => {
      // 立即刷新状态
      queryClient.invalidateQueries({ queryKey: [...SCHEDULER_KEY, 'status'] });
    },
  });
}

/**
 * 刷新调度器数据
 */
export function useRefreshScheduler() {
  const queryClient = useQueryClient();

  return {
    refresh: () => {
      queryClient.invalidateQueries({ queryKey: SCHEDULER_KEY });
    },
  };
}
