/**
 * 健康监控页面
 *
 * 展示系统组件状态、数据源健康度、系统指标和错误日志
 */
import React, { useState } from 'react';
import {
  useHealthReport,
  useResetCircuitBreaker,
  useClearHealthErrors,
} from '../hooks';
import PageLayout from '../components/layout/PageLayout';
import type { ProviderStatus } from '../src/types/schema';
import {
  Activity,
  CheckCircle2,
  AlertCircle,
  Clock,
  Database,
  Cpu,
  RefreshCw,
  ShieldAlert,
  Zap,
  BarChart3,
  Trash2,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

const HealthPage: React.FC = () => {
  const [forceRefresh, setForceRefresh] = useState(false);
  const { data: report, isLoading, isFetching, refetch } = useHealthReport(forceRefresh);
  const resetCircuitBreaker = useResetCircuitBreaker();
  const clearErrors = useClearHealthErrors();

  const handleRefresh = () => {
    setForceRefresh(true);
    refetch().finally(() => setForceRefresh(false));
  };

  const handleResetCB = async (provider: string) => {
    try {
      await resetCircuitBreaker.mutateAsync(provider);
    } catch (e) {
      console.error('Failed to reset circuit breaker', e);
    }
  };

  const handleClearErrors = async () => {
    if (window.confirm('确定要清除所有错误记录吗？')) {
      await clearErrors.mutateAsync();
    }
  };

  if (isLoading) {
    return (
      <PageLayout title="系统健康监控">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 animate-spin text-accent" />
          <span className="ml-3 text-stone-400">正在加载健康报告...</span>
        </div>
      </PageLayout>
    );
  }

  // 准备图表数据
  const providerChartData = report?.data_providers ? Object.entries(report.data_providers).map(([name, stats]) => ({
    name,
    successRate: stats.total_requests > 0 
      ? Math.round((stats.successful_requests / stats.total_requests) * 100) 
      : 100,
    latency: stats.avg_latency_ms,
  })) : [];

  return (
    <PageLayout 
      title="系统健康监控" 
      subtitle={`最后检查时间: ${report ? new Date(report.timestamp).toLocaleString() : '-'}`}
      actions={[
        {
          label: isFetching ? '正在刷新...' : '强制刷新',
          onClick: handleRefresh,
          icon: RefreshCw,
          loading: isFetching,
          disabled: isFetching,
          variant: 'primary'
        }
      ]}
    >
      <div className="space-y-8 pb-12">
        {/* 概览卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatusCard
            title="整体状态"
            value={report?.overall_status === 'healthy' ? '健康' : report?.overall_status === 'degraded' ? '降级' : '异常'}
            icon={<Activity className={report?.overall_status === 'healthy' ? 'text-green-500' : 'text-yellow-500'} />}
            status={report?.overall_status}
          />
          <StatusCard
            title="运行时间"
            value={report?.uptime_formatted || '-'}
            icon={<Clock className="text-accent" />}
          />
          <StatusCard
            title="CPU 使用率"
            value={`${report?.metrics.cpu_percent}%`}
            icon={<Cpu className="text-purple-500" />}
            progress={report?.metrics.cpu_percent}
          />
          <StatusCard
            title="内存使用率"
            value={`${report?.metrics.memory_percent}%`}
            icon={<Database className="text-orange-500" />}
            progress={report?.metrics.memory_percent}
            subtitle={`${report?.metrics.memory_used_mb.toFixed(0)} / ${report?.metrics.memory_total_mb.toFixed(0)} MB`}
          />
        </div>

        {/* 数据源健康度 */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold flex items-center">
              <Zap className="w-5 h-5 mr-2 text-yellow-500" />
              数据源健康度
            </h2>
            <button 
              onClick={() => handleResetCB('all')}
              className="text-sm text-accent hover:text-amber-300 flex items-center"
            >
              <RefreshCw className="w-3 h-3 mr-1" />
              重置所有熔断
            </button>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {report?.data_providers && Object.entries(report.data_providers).map(([name, stats]) => (
              <ProviderCard 
                key={name} 
                name={name} 
                stats={stats} 
                onReset={() => handleResetCB(name)}
              />
            ))}
          </div>
        </section>

        {/* 可视化图表 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-surface-raised/50 border border-border rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-6 flex items-center">
              <CheckCircle2 className="w-5 h-5 mr-2 text-green-500" />
              请求成功率 (%)
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={providerChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#44403c" vertical={false} />
                  <XAxis dataKey="name" stroke="#9CA3AF" />
                  <YAxis stroke="#9CA3AF" domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1c1917', border: '1px solid #44403c' }}
                    itemStyle={{ color: '#10B981' }}
                  />
                  <Bar dataKey="successRate" name="成功率">
                    {providerChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.successRate > 90 ? '#10B981' : entry.successRate > 70 ? '#F59E0B' : '#EF4444'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-surface-raised/50 border border-border rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-6 flex items-center">
              <BarChart3 className="w-5 h-5 mr-2 text-accent" />
              平均延迟 (ms)
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={providerChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#44403c" vertical={false} />
                  <XAxis dataKey="name" stroke="#9CA3AF" />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1c1917', border: '1px solid #44403c' }}
                    itemStyle={{ color: '#D97706' }}
                  />
                  <Bar dataKey="latency" fill="#D97706" name="延迟" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* 组件状态列表 */}
        <section>
          <h2 className="text-xl font-bold mb-4 flex items-center">
            <ShieldAlert className="w-5 h-5 mr-2 text-accent" />
            核心组件状态
          </h2>
          <div className="bg-surface-raised/50 border border-border rounded-xl overflow-hidden">
            <table className="w-full text-left">
              <thead className="bg-surface-overlay/50 text-stone-400 text-sm">
                <tr>
                  <th className="px-6 py-3 font-medium">组件名称</th>
                  <th className="px-6 py-3 font-medium">状态</th>
                  <th className="px-6 py-3 font-medium">延迟</th>
                  <th className="px-6 py-3 font-medium">详细信息</th>
                  <th className="px-6 py-3 font-medium">最后检查</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {report?.components.map((comp) => (
                  <tr key={comp.name} className="hover:bg-surface-overlay/30 transition-colors">
                    <td className="px-6 py-4 font-medium text-stone-200 capitalize">{comp.name.replace('_', ' ')}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        comp.status === 'healthy' ? 'bg-green-500/10 text-green-500' :
                        comp.status === 'degraded' ? 'bg-yellow-500/10 text-yellow-500' :
                        'bg-red-500/10 text-red-500'
                      }`}>
                        {comp.status === 'healthy' ? '正常' : comp.status === 'degraded' ? '降级' : '异常'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-stone-400 text-sm">
                      {comp.latency_ms ? `${comp.latency_ms}ms` : '-'}
                    </td>
                    <td className="px-6 py-4 text-stone-400 text-sm truncate max-w-xs">
                      {comp.message || '-'}
                    </td>
                    <td className="px-6 py-4 text-stone-500 text-xs">
                      {new Date(comp.last_check).toLocaleTimeString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* 最近错误 */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold flex items-center text-red-400">
              <AlertCircle className="w-5 h-5 mr-2" />
              最近错误日志
            </h2>
            {report && report.recent_errors.length > 0 && (
              <button 
                onClick={handleClearErrors}
                className="text-sm text-stone-400 hover:text-red-400 flex items-center transition-colors"
              >
                <Trash2 className="w-3 h-3 mr-1" />
                清除日志
              </button>
            )}
          </div>
          <div className="bg-surface-raised/50 border border-border rounded-xl overflow-hidden">
            {report?.recent_errors.length === 0 ? (
              <div className="p-8 text-center text-stone-500">
                暂无错误记录，系统运行良好
              </div>
            ) : (
              <div className="divide-y divide-border">
                {report?.recent_errors.map((err, idx) => (
                  <div key={idx} className="p-4 hover:bg-surface-overlay/30 transition-colors flex items-start">
                    <div className="mt-1 mr-4">
                      <AlertCircle className="w-5 h-5 text-red-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-stone-200">{err.component}</span>
                        <span className="text-xs text-stone-500">{new Date(err.timestamp).toLocaleString()}</span>
                      </div>
                      <div className="text-sm text-red-400 font-medium mb-1">{err.error_type}</div>
                      <p className="text-sm text-stone-400 break-words">{err.message}</p>
                      {err.count > 1 && (
                        <div className="mt-2 inline-flex items-center px-2 py-0.5 rounded bg-red-500/10 text-red-500 text-xs">
                          出现次数: {err.count}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      </div>
    </PageLayout>
  );
};

// --- 辅助组件 ---

interface StatusCardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  status?: string;
  progress?: number;
  subtitle?: string;
}

const StatusCard: React.FC<StatusCardProps> = ({ title, value, icon, progress, subtitle }) => (
  <div className="bg-surface-raised/50 border border-border rounded-xl p-5 flex flex-col">
    <div className="flex items-center justify-between mb-3">
      <span className="text-stone-400 text-sm font-medium">{title}</span>
      <div className="p-2 bg-surface-overlay rounded-lg">{icon}</div>
    </div>
    <div className="text-2xl font-bold text-stone-100 mb-1">{value}</div>
    {subtitle && <div className="text-xs text-stone-500 mb-2">{subtitle}</div>}
    {progress !== undefined && (
      <div className="mt-auto pt-2">
        <div className="w-full bg-surface-overlay rounded-full h-1.5">
          <div 
            className={`h-1.5 rounded-full ${progress > 80 ? 'bg-red-500' : progress > 60 ? 'bg-yellow-500' : 'bg-accent'}`}
            style={{ width: `${progress}%` }}
          ></div>
        </div>
      </div>
    )}
  </div>
);

interface ProviderCardProps {
  name: string;
  stats: ProviderStatus;
  onReset: () => void;
}

const ProviderCard: React.FC<ProviderCardProps> = ({ name, stats, onReset }) => {
  const successRate = stats.total_requests > 0 
    ? (stats.successful_requests / stats.total_requests) * 100 
    : 100;

  return (
    <div className={`bg-surface-raised/50 border rounded-xl p-5 transition-all ${
      !stats.available ? 'border-red-500/50 bg-red-500/5' : 'border-border'
    }`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          <div className={`w-2.5 h-2.5 rounded-full mr-2 ${
            stats.available ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]' : 'bg-red-500 animate-pulse'
          }`} />
          <h3 className="font-bold text-stone-100 capitalize">{name}</h3>
        </div>
        {!stats.available && (
          <button 
            onClick={onReset}
            className="text-xs bg-red-500/20 hover:bg-red-500/30 text-red-400 px-2 py-1 rounded border border-red-500/30 transition-colors"
          >
            手动重置
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <div className="text-xs text-stone-500 mb-1">成功率</div>
          <div className={`text-lg font-semibold ${
            successRate > 90 ? 'text-green-400' : successRate > 70 ? 'text-yellow-400' : 'text-red-400'
          }`}>
            {successRate.toFixed(1)}%
          </div>
        </div>
        <div>
          <div className="text-xs text-stone-500 mb-1">平均延迟</div>
          <div className="text-lg font-semibold text-accent">
            {stats.avg_latency_ms.toFixed(0)}ms
          </div>
        </div>
      </div>

      <div className="space-y-2 text-xs text-stone-400">
        <div className="flex justify-between">
          <span>总请求数:</span>
          <span className="text-stone-200">{stats.total_requests}</span>
        </div>
        <div className="flex justify-between">
          <span>连续失败:</span>
          <span className={stats.failure_count > 0 ? 'text-red-400' : 'text-stone-200'}>
            {stats.failure_count} / {stats.threshold}
          </span>
        </div>
        {stats.last_failure && (
          <div className="pt-2 border-t border-border mt-2">
            <div className="text-stone-500 mb-1">最后失败:</div>
            <div className="text-red-400/80 truncate" title={stats.last_error || ''}>
              {stats.last_error || '未知错误'}
            </div>
            <div className="text-[10px] text-stone-600 mt-1">
              {new Date(stats.last_failure).toLocaleString()}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default HealthPage;
