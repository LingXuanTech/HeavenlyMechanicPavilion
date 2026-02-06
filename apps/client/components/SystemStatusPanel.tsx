/**
 * 系统状态面板
 *
 * 显示系统健康状态、资源使用和运行时间
 */
import React from 'react';
import {
  Activity,
  Server,
  Database,
  Clock,
  Cpu,
  HardDrive,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  RefreshCw,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { useHealthReport, useHealthMetrics, useSystemUptime, useClearHealthErrors } from '../hooks';
import type * as T from '../src/types/schema';

interface SystemStatusPanelProps {
  expanded?: boolean;
  onToggle?: () => void;
}

const getStatusColor = (status: T.HealthStatus): string => {
  switch (status) {
    case 'healthy': return 'text-green-400';
    case 'degraded': return 'text-yellow-400';
    case 'unhealthy': return 'text-red-400';
    default: return 'text-stone-400';
  }
};

const getStatusIcon = (status: T.HealthStatus | 'unknown') => {
  switch (status) {
    case 'healthy': return <CheckCircle2 className="w-4 h-4 text-green-400" />;
    case 'degraded': return <AlertTriangle className="w-4 h-4 text-yellow-400" />;
    case 'unhealthy': return <XCircle className="w-4 h-4 text-red-400" />;
    default: return <Activity className="w-4 h-4 text-stone-400" />;
  }
};

const getProgressColor = (percent: number): string => {
  if (percent < 50) return 'bg-green-500';
  if (percent < 80) return 'bg-yellow-500';
  return 'bg-red-500';
};

const SystemStatusPanel: React.FC<SystemStatusPanelProps> = ({ expanded = false, onToggle }) => {
  const { data: report, isLoading: reportLoading, refetch: refetchReport } = useHealthReport();
  const { data: metrics } = useHealthMetrics();
  const { data: uptime } = useSystemUptime();
  const clearErrors = useClearHealthErrors();

  const handleRefresh = () => {
    refetchReport();
  };

  const handleClearErrors = () => {
    if (confirm('确定要清除所有错误记录吗？')) {
      clearErrors.mutate();
    }
  };

  // 紧凑模式 - 只显示状态指示
  if (!expanded) {
    return (
      <div
        onClick={onToggle}
        className="flex items-center gap-2 px-3 py-2 bg-surface-raised border border-border rounded-lg cursor-pointer hover:border-border-strong transition-colors"
      >
        {reportLoading ? (
          <RefreshCw className="w-4 h-4 text-stone-400 animate-spin" />
        ) : (
          getStatusIcon(report?.overall_status || 'unknown')
        )}
        <span className="text-xs text-stone-400">System</span>
        <ChevronDown className="w-3 h-3 text-stone-500" />
      </div>
    );
  }

  return (
    <div className="bg-surface-raised border border-border rounded-lg overflow-hidden">
      {/* Header */}
      <div
        onClick={onToggle}
        className="flex items-center justify-between px-4 py-3 bg-surface/50 border-b border-border cursor-pointer hover:bg-surface/70 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Server className="w-4 h-4 text-accent" />
          <span className="text-sm font-semibold text-white">System Status</span>
          {report && (
            <span className={`text-xs font-medium ${getStatusColor(report.overall_status)}`}>
              {report.overall_status.toUpperCase()}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => { e.stopPropagation(); handleRefresh(); }}
            className="p-1 hover:bg-surface-overlay rounded transition-colors"
            title="刷新状态"
          >
            <RefreshCw className={`w-3 h-3 text-stone-400 ${reportLoading ? 'animate-spin' : ''}`} />
          </button>
          <ChevronUp className="w-4 h-4 text-stone-500" />
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Uptime */}
        {uptime && (
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 text-stone-400">
              <Clock className="w-3 h-3" />
              <span>Uptime</span>
            </div>
            <span className="font-mono text-green-400">{uptime.uptime_formatted}</span>
          </div>
        )}

        {/* Resource Usage */}
        {metrics && (
          <div className="space-y-3">
            {/* CPU */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 text-stone-400">
                  <Cpu className="w-3 h-3" />
                  <span>CPU</span>
                </div>
                <span className="font-mono text-stone-300">{metrics.cpu_percent.toFixed(1)}%</span>
              </div>
              <div className="h-1.5 bg-surface-overlay rounded-full overflow-hidden">
                <div
                  className={`h-full ${getProgressColor(metrics.cpu_percent)} transition-all`}
                  style={{ width: `${metrics.cpu_percent}%` }}
                />
              </div>
            </div>

            {/* Memory */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 text-stone-400">
                  <Activity className="w-3 h-3" />
                  <span>Memory</span>
                </div>
                <span className="font-mono text-stone-300">
                  {metrics.memory_used_mb.toFixed(0)} / {metrics.memory_total_mb.toFixed(0)} MB
                </span>
              </div>
              <div className="h-1.5 bg-surface-overlay rounded-full overflow-hidden">
                <div
                  className={`h-full ${getProgressColor(metrics.memory_percent)} transition-all`}
                  style={{ width: `${metrics.memory_percent}%` }}
                />
              </div>
            </div>

            {/* Disk */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 text-stone-400">
                  <HardDrive className="w-3 h-3" />
                  <span>Disk</span>
                </div>
                <span className="font-mono text-stone-300">
                  {metrics.disk_used_gb.toFixed(1)} / {metrics.disk_total_gb.toFixed(1)} GB
                </span>
              </div>
              <div className="h-1.5 bg-surface-overlay rounded-full overflow-hidden">
                <div
                  className={`h-full ${getProgressColor(metrics.disk_percent)} transition-all`}
                  style={{ width: `${metrics.disk_percent}%` }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Components */}
        {report?.components && report.components.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs text-stone-400">
              <Database className="w-3 h-3" />
              <span>Components</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {report.components.map((comp) => (
                <div
                  key={comp.name}
                  className="flex items-center justify-between px-2 py-1.5 bg-surface/50 rounded border border-border"
                >
                  <span className="text-xs text-stone-300 truncate">{comp.name}</span>
                  {getStatusIcon(comp.status)}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent Errors */}
        {report?.recent_errors && report.recent_errors.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs text-stone-400">
                <AlertTriangle className="w-3 h-3" />
                <span>Recent Errors ({report.recent_errors.length})</span>
              </div>
              <button
                onClick={handleClearErrors}
                className="text-[10px] text-red-400 hover:text-red-300 transition-colors"
              >
                Clear All
              </button>
            </div>
            <div className="max-h-24 overflow-y-auto space-y-1">
              {report.recent_errors.slice(0, 3).map((err, i) => (
                <div
                  key={i}
                  className="text-xs p-2 bg-red-950/20 border border-red-900/30 rounded"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-red-400 font-medium">{err.component}</span>
                    <span className="text-stone-500 text-[10px]">x{err.count}</span>
                  </div>
                  <p className="text-stone-400 truncate mt-0.5">{err.message}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Timestamp */}
        {report && (
          <div className="text-[10px] text-stone-500 text-right">
            Last checked: {new Date(report.timestamp).toLocaleTimeString()}
          </div>
        )}
      </div>
    </div>
  );
};

export default SystemStatusPanel;
