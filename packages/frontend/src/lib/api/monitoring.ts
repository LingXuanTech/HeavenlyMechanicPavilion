import { APIError } from './client';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new APIError(
      errorData.detail || `Request failed with status ${response.status}`,
      response.status,
      errorData
    );
  }

  if (response.status === 204) {
    return null as T;
  }

  const text = await response.text();
  if (!text) {
    return null as T;
  }

  return JSON.parse(text) as T;
}

export interface HealthStatus {
  status: string;
  timestamp: string;
  uptime_seconds: number;
  services: {
    database: ServiceHealth;
    redis: ServiceHealth;
    vendors: VendorHealth;
    workers: WorkerHealth;
  };
}

export interface ServiceHealth {
  status: string;
  latency_ms?: number;
  message?: string;
  enabled?: boolean;
  connected_clients?: number;
  used_memory_mb?: number;
  uptime_days?: number;
}

export interface VendorHealth {
  status: string;
  total_vendors: number;
  healthy_vendors: number;
  vendors: Record<string, VendorStatus>;
}

export interface VendorStatus {
  status: string;
  provider: string;
  total_requests: number;
  total_errors: number;
  error_rate_percent: number;
  rate_limits: Record<string, any>;
}

export interface WorkerHealth {
  status: string;
  total_workers: number;
  running_workers: number;
  workers: Record<string, WorkerStatus>;
  watchdog?: WatchdogStatus;
}

export interface WorkerStatus {
  status: string;
  tasks_processed: number;
  current_tasks: number;
}

export interface WatchdogStatus {
  enabled: boolean;
  tracked_workers: Record<string, TrackedWorkerStatus>;
}

export interface TrackedWorkerStatus {
  last_seen_seconds_ago: number;
  current_tasks: number;
  status: string;
}

export interface QueueMetrics {
  status: string;
  total_items: number;
  queues: Record<string, number>;
  message?: string;
}

export interface AlertHistory {
  title: string;
  message: string;
  level: string;
  details: Record<string, any>;
  timestamp: string;
}

export interface UptimeInfo {
  uptime_seconds: number;
  uptime_formatted: string;
  uptime_days: number;
}

export const monitoringAPI = {
  getHealth: () => fetchAPI<HealthStatus>("/monitoring/health"),
  getMetrics: () => fetch(`${API_BASE_URL}/monitoring/metrics`).then(r => r.text()),
  getVendorStatus: () => fetchAPI<VendorHealth>("/monitoring/vendors"),
  getWorkerStatus: () => fetchAPI<WorkerHealth>("/monitoring/workers"),
  getQueueMetrics: () => fetchAPI<QueueMetrics>("/monitoring/queues"),
  getDatabaseMetrics: () => fetchAPI<ServiceHealth>("/monitoring/database"),
  getRedisMetrics: () => fetchAPI<ServiceHealth>("/monitoring/redis"),
  getAlertHistory: (limit?: number) => 
    fetchAPI<AlertHistory[]>(`/monitoring/alerts/history${limit ? `?limit=${limit}` : ''}`),
  sendTestAlert: () => 
    fetchAPI<{ success: boolean; message: string }>("/monitoring/alerts/test", { method: "POST" }),
  getUptime: () => fetchAPI<UptimeInfo>("/monitoring/uptime"),
};
