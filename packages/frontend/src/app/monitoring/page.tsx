"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { monitoringAPI, HealthStatus, QueueMetrics, AlertHistory } from "@/lib/api/monitoring";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock,
  Database,
  Wifi,
  XCircle,
  RefreshCw,
} from "lucide-react";

export default function MonitoringPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [queues, setQueues] = useState<QueueMetrics | null>(null);
  const [alerts, setAlerts] = useState<AlertHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchData = async () => {
    try {
      const [healthData, queueData, alertData] = await Promise.all([
        monitoringAPI.getHealth(),
        monitoringAPI.getQueueMetrics(),
        monitoringAPI.getAlertHistory(10),
      ]);
      setHealth(healthData);
      setQueues(queueData);
      setAlerts(alertData);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to fetch monitoring data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(fetchData, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "healthy":
      case "ok":
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case "degraded":
      case "warning":
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
      case "error":
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Activity className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      healthy: "default",
      ok: "default",
      degraded: "secondary",
      warning: "secondary",
      error: "destructive",
    };
    
    return (
      <Badge variant={variants[status] || "outline"}>
        {status.toUpperCase()}
      </Badge>
    );
  };

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${days}d ${hours}h ${minutes}m`;
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">System Monitoring</h1>
          <p className="text-gray-500 mt-1">Real-time health and metrics dashboard</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant={autoRefresh ? "default" : "outline"}
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            <Activity className="h-4 w-4 mr-2" />
            {autoRefresh ? "Auto-refresh ON" : "Auto-refresh OFF"}
          </Button>
          <Button variant="outline" size="sm" onClick={fetchData}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Overall Status */}
      {health && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  {getStatusIcon(health.status)}
                  System Status
                </CardTitle>
                <CardDescription>
                  Overall system health and uptime
                </CardDescription>
              </div>
              {getStatusBadge(health.status)}
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="flex items-center gap-3">
                <Clock className="h-8 w-8 text-blue-500" />
                <div>
                  <p className="text-sm text-gray-500">Uptime</p>
                  <p className="text-lg font-semibold">
                    {formatUptime(health.uptime_seconds)}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Activity className="h-8 w-8 text-green-500" />
                <div>
                  <p className="text-sm text-gray-500">Last Updated</p>
                  <p className="text-lg font-semibold">
                    {new Date(health.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <CheckCircle2 className="h-8 w-8 text-green-500" />
                <div>
                  <p className="text-sm text-gray-500">Status</p>
                  <p className="text-lg font-semibold capitalize">{health.status}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Service Status */}
      {health && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Database */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Database className="h-5 w-5" />
                  Database
                </CardTitle>
                {getStatusIcon(health.services.database.status)}
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">Status</span>
                  {getStatusBadge(health.services.database.status)}
                </div>
                {health.services.database.latency_ms !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-500">Latency</span>
                    <span className="text-sm font-medium">
                      {health.services.database.latency_ms.toFixed(2)}ms
                    </span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Redis */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Wifi className="h-5 w-5" />
                  Redis
                </CardTitle>
                {getStatusIcon(health.services.redis.status)}
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">Status</span>
                  {getStatusBadge(health.services.redis.status)}
                </div>
                {health.services.redis.enabled && health.services.redis.latency_ms !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-500">Latency</span>
                    <span className="text-sm font-medium">
                      {health.services.redis.latency_ms.toFixed(2)}ms
                    </span>
                  </div>
                )}
                {health.services.redis.used_memory_mb !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-500">Memory</span>
                    <span className="text-sm font-medium">
                      {health.services.redis.used_memory_mb.toFixed(1)}MB
                    </span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Vendors */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Vendors</CardTitle>
                {getStatusIcon(health.services.vendors.status)}
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">Status</span>
                  {getStatusBadge(health.services.vendors.status)}
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">Healthy</span>
                  <span className="text-sm font-medium">
                    {health.services.vendors.healthy_vendors} / {health.services.vendors.total_vendors}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Workers */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Workers</CardTitle>
                {getStatusIcon(health.services.workers.status)}
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">Status</span>
                  {getStatusBadge(health.services.workers.status)}
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">Running</span>
                  <span className="text-sm font-medium">
                    {health.services.workers.running_workers} / {health.services.workers.total_workers}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Vendor Details */}
      {health && health.services.vendors.vendors && (
        <Card>
          <CardHeader>
            <CardTitle>Vendor Error Rates</CardTitle>
            <CardDescription>Error rates and request statistics for each vendor</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(health.services.vendors.vendors).map(([name, vendor]) => (
                <div key={name} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(vendor.status)}
                    <div>
                      <p className="font-medium">{name}</p>
                      <p className="text-sm text-gray-500">{vendor.provider}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <p className="text-sm text-gray-500">Requests</p>
                      <p className="font-medium">{vendor.total_requests}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-500">Errors</p>
                      <p className="font-medium">{vendor.total_errors}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-500">Error Rate</p>
                      <p className={`font-medium ${vendor.error_rate_percent > 20 ? 'text-red-500' : 'text-green-500'}`}>
                        {vendor.error_rate_percent.toFixed(1)}%
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Queue Metrics */}
      {queues && queues.status === "ok" && (
        <Card>
          <CardHeader>
            <CardTitle>Queue Backlogs</CardTitle>
            <CardDescription>Current queue sizes and pending tasks</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(queues.queues).map(([name, size]) => (
                <div key={name} className="flex items-center justify-between p-3 border rounded-lg">
                  <span className="font-medium">{name}</span>
                  <Badge variant={size > 10 ? "destructive" : "default"}>
                    {size} items
                  </Badge>
                </div>
              ))}
              {Object.keys(queues.queues).length === 0 && (
                <p className="text-sm text-gray-500 text-center py-4">No active queues</p>
              )}
            </div>
            <div className="mt-4 pt-4 border-t">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-500">Total Items</span>
                <span className="text-lg font-bold">{queues.total_items}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Alerts */}
      {alerts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recent Alerts</CardTitle>
            <CardDescription>Latest system alerts and notifications</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {alerts.map((alert, index) => (
                <Alert
                  key={index}
                  variant={alert.level === "error" || alert.level === "critical" ? "destructive" : "default"}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge>{alert.level.toUpperCase()}</Badge>
                        <span className="font-medium">{alert.title}</span>
                      </div>
                      <AlertDescription>{alert.message}</AlertDescription>
                      <p className="text-xs text-gray-500 mt-2">
                        {new Date(alert.timestamp).toLocaleString()}
                      </p>
                    </div>
                  </div>
                </Alert>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
