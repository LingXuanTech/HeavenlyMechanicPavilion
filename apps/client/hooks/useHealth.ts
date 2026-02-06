/**
 * 健康监控 Hooks
 *
 * 提供系统健康状态监控功能
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getHealthQuick,
  getHealthReport,
  getHealthComponents,
  getHealthMetrics,
  getHealthErrors,
  clearHealthErrors,
  getSystemUptime,
  checkLiveness,
  checkReadiness,
  resetCircuitBreaker,
} from '../services/api';

export const HEALTH_KEY = ['health'];

/**
 * 快速健康检查
 */
export function useHealthQuick() {
  return useQuery({
    queryKey: [...HEALTH_KEY, 'quick'],
    queryFn: getHealthQuick,
    staleTime: 30 * 1000, // 30秒
    refetchInterval: 60 * 1000, // 1分钟自动刷新
  });
}

/**
 * 获取完整健康报告
 */
export function useHealthReport(forceRefresh: boolean = false) {
  return useQuery({
    queryKey: [...HEALTH_KEY, 'report', forceRefresh],
    queryFn: () => getHealthReport(forceRefresh),
    staleTime: 30 * 1000,
    refetchInterval: 2 * 60 * 1000, // 2分钟自动刷新
  });
}

/**
 * 获取组件健康状态
 */
export function useHealthComponents() {
  return useQuery({
    queryKey: [...HEALTH_KEY, 'components'],
    queryFn: getHealthComponents,
    staleTime: 30 * 1000,
  });
}

/**
 * 获取系统指标
 */
export function useHealthMetrics() {
  return useQuery({
    queryKey: [...HEALTH_KEY, 'metrics'],
    queryFn: getHealthMetrics,
    staleTime: 15 * 1000, // 15秒
    refetchInterval: 30 * 1000, // 30秒自动刷新
  });
}

/**
 * 获取最近错误记录
 */
export function useHealthErrors(limit: number = 10) {
  return useQuery({
    queryKey: [...HEALTH_KEY, 'errors', limit],
    queryFn: () => getHealthErrors(limit),
    staleTime: 60 * 1000,
  });
}

/**
 * 获取系统运行时间
 */
export function useSystemUptime() {
  return useQuery({
    queryKey: [...HEALTH_KEY, 'uptime'],
    queryFn: getSystemUptime,
    staleTime: 60 * 1000,
    refetchInterval: 60 * 1000,
  });
}

/**
 * Liveness 探针
 */
export function useLiveness() {
  return useQuery({
    queryKey: [...HEALTH_KEY, 'liveness'],
    queryFn: checkLiveness,
    staleTime: 10 * 1000,
  });
}

/**
 * Readiness 探针
 */
export function useReadiness() {
  return useQuery({
    queryKey: [...HEALTH_KEY, 'readiness'],
    queryFn: checkReadiness,
    staleTime: 10 * 1000,
  });
}

/**
 * 清除错误记录
 */
export function useClearHealthErrors() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: clearHealthErrors,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...HEALTH_KEY, 'errors'] });
      queryClient.invalidateQueries({ queryKey: [...HEALTH_KEY, 'report'] });
    },
  });
}

/**
 * 重置熔断状态
 */
export function useResetCircuitBreaker() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (provider: string) => resetCircuitBreaker(provider),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...HEALTH_KEY, 'report'] });
    },
  });
}
