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
  signal_threshold: 'STRONG_BUY' | 'BUY' | 'ALL';
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

export interface NotificationLogsPageResponse {
  items: NotificationLog[];
  total: number;
  limit: number;
  offset: number;
}

export interface UpsertNotificationConfigParams {
  channel?: 'telegram';
  channel_user_id?: string | null;
  is_enabled?: boolean;
  signal_threshold?: 'STRONG_BUY' | 'BUY' | 'ALL';
  quiet_hours_start?: number | null;
  quiet_hours_end?: number | null;
}

export interface TestNotificationParams {
  channel: 'telegram';
  channel_user_id: string;
}

export interface NotificationLogQueryParams {
  limit?: number;
  offset?: number;
  symbol?: string;
  delivered?: boolean;
  sent_after?: string;
  sent_before?: string;
}

export interface ClearNotificationLogsResponse {
  ok: boolean;
  deleted: number;
}

export interface NotificationStats {
  total_sent: number;
  total_failed: number;
  success_rate: number;
  channels_count: number;
  enabled_channels_count: number;
  last_sent_at: string | null;
}

export interface TestAllNotificationResultItem {
  channel: string;
  channel_user_id: string;
  delivered: boolean;
}

export interface TestAllNotificationsResponse {
  total: number;
  delivered: number;
  results: TestAllNotificationResultItem[];
}

// ============ Query Keys ============

export const NOTIFICATION_KEY = 'notifications';

function buildLogQueryString(params: NotificationLogQueryParams): string {
  const query = new URLSearchParams();
  query.set('limit', String(params.limit ?? 50));
  query.set('offset', String(params.offset ?? 0));
  if (params.symbol) {
    query.set('symbol', params.symbol);
  }
  if (typeof params.delivered === 'boolean') {
    query.set('delivered', String(params.delivered));
  }
  if (params.sent_after) {
    query.set('sent_after', params.sent_after);
  }
  if (params.sent_before) {
    query.set('sent_before', params.sent_before);
  }
  return query.toString();
}

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
  return useNotificationLogsWithParams(token, { limit });
}

export function useNotificationLogsWithParams(
  token: string | null,
  params: NotificationLogQueryParams = {},
) {
  const queryString = buildLogQueryString(params);
  return useQuery({
    queryKey: [NOTIFICATION_KEY, 'logs', params],
    queryFn: () =>
      request<NotificationLogsPageResponse>(`/notifications/logs?${queryString}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      }),
    enabled: !!token,
    staleTime: 60 * 1000,
  });
}

export function useNotificationStats(token: string | null) {
  return useQuery({
    queryKey: [NOTIFICATION_KEY, 'stats'],
    queryFn: () =>
      request<NotificationStats>('/notifications/stats', {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      }),
    enabled: !!token,
    staleTime: 60 * 1000,
  });
}

export function useClearNotificationLogs(token: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (
      params: Pick<
        NotificationLogQueryParams,
        'symbol' | 'delivered' | 'sent_after' | 'sent_before'
      > = {},
    ) => {
      const query = new URLSearchParams();
      if (params.symbol) {
        query.set('symbol', params.symbol);
      }
      if (typeof params.delivered === 'boolean') {
        query.set('delivered', String(params.delivered));
      }
      if (params.sent_after) {
        query.set('sent_after', params.sent_after);
      }
      if (params.sent_before) {
        query.set('sent_before', params.sent_before);
      }
      const queryString = query.toString();
      return request<ClearNotificationLogsResponse>(
        queryString ? `/notifications/logs?${queryString}` : '/notifications/logs',
        {
          method: 'DELETE',
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        },
      );
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [NOTIFICATION_KEY, 'logs'] });
      qc.invalidateQueries({ queryKey: [NOTIFICATION_KEY, 'stats'] });
    },
  });
}

/**
 * 发送测试通知
 */
export function useTestNotification(token: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: TestNotificationParams) =>
      request<{ ok: boolean; message: string }>('/notifications/test', {
        method: 'POST',
        body: JSON.stringify(params),
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [NOTIFICATION_KEY, 'logs'] });
      qc.invalidateQueries({ queryKey: [NOTIFICATION_KEY, 'stats'] });
    },
  });
}

export function useTestAllNotifications(token: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      request<TestAllNotificationsResponse>('/notifications/test-all', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [NOTIFICATION_KEY, 'logs'] });
      qc.invalidateQueries({ queryKey: [NOTIFICATION_KEY, 'stats'] });
    },
  });
}
