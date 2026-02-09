/**
 * 推送通知 Hooks
 *
 * 管理 Telegram 等渠道的通知配置、日志查询和测试发送
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { request } from '../services/api';

// ============ 类型定义 ============

export interface NotificationConfig {
  id: number;
  channel: string;
  channel_user_id: string | null;
  is_enabled: boolean;
  signal_threshold: string;
  quiet_hours_start: number | null;
  quiet_hours_end: number | null;
  created_at: string;
  updated_at: string;
}

export interface NotificationLog {
  id: number;
  channel: string;
  title: string;
  body: string;
  signal: string | null;
  symbol: string | null;
  sent_at: string;
  delivered: boolean;
  error: string | null;
}

export interface UpsertNotificationConfigParams {
  channel?: string;
  channel_user_id?: string | null;
  is_enabled?: boolean;
  signal_threshold?: string;
  quiet_hours_start?: number | null;
  quiet_hours_end?: number | null;
}

export interface TestNotificationParams {
  channel: string;
  channel_user_id: string;
}

// ============ Query Keys ============

export const NOTIFICATION_KEY = 'notifications';

// ============ Hooks ============

/**
 * 获取当前用户的通知配置列表
 */
export function useNotificationConfigs(token: string | null) {
  return useQuery({
    queryKey: [NOTIFICATION_KEY, 'config'],
    queryFn: () =>
      request<NotificationConfig[]>('/notifications/config', {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      }),
    enabled: !!token,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * 创建/更新通知配置
 */
export function useUpsertNotificationConfig(token: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: UpsertNotificationConfigParams) =>
      request<NotificationConfig>('/notifications/config', {
        method: 'PUT',
        body: JSON.stringify(params),
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [NOTIFICATION_KEY, 'config'] });
    },
  });
}

/**
 * 删除指定渠道的通知配置
 */
export function useDeleteNotificationConfig(token: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (channel: string) =>
      request<{ ok: boolean }>(`/notifications/config/${channel}`, {
        method: 'DELETE',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [NOTIFICATION_KEY, 'config'] });
    },
  });
}

/**
 * 获取通知发送日志
 */
export function useNotificationLogs(token: string | null, limit = 50) {
  return useQuery({
    queryKey: [NOTIFICATION_KEY, 'logs', limit],
    queryFn: () =>
      request<NotificationLog[]>(`/notifications/logs?limit=${limit}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      }),
    enabled: !!token,
    staleTime: 60 * 1000,
  });
}

/**
 * 发送测试通知
 */
export function useTestNotification(token: string | null) {
  return useMutation({
    mutationFn: (params: TestNotificationParams) =>
      request<{ ok: boolean; message: string }>('/notifications/test', {
        method: 'POST',
        body: JSON.stringify(params),
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      }),
  });
}
