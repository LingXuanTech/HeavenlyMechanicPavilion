/**
 * 调度器管理页面
 *
 * 展示调度任务状态、下次运行时间，支持手动触发分析
 * 使用 standard 布局，结构化展示任务信息
 */
import React, { useMemo } from 'react';
import {
  Clock,
  Play,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Timer,
  Zap,
  Calendar,
  Loader2,
  Activity,
} from 'lucide-react';
import PageLayout, { PageSection, StatCard, LoadingState, EmptyState } from '../components/layout/PageLayout';
import { useToast } from '../components/Toast';
import {
  useSchedulerStatus,
  useSchedulerJobs,
  useTriggerDailyAnalysis,
  useRefreshScheduler,
} from '../hooks/useScheduler';
import type { SchedulerJob } from '../hooks/useScheduler';

// === 辅助函数 ===

function formatNextRun(isoString: string | null): string {
  if (!isoString) return '未调度';

  const next = new Date(isoString);
  const now = new Date();
  const diffMs = next.getTime() - now.getTime();

  if (diffMs < 0) return '已过期';

  const diffMin = Math.floor(diffMs / 60000);
  const diffHour = Math.floor(diffMin / 60);

  if (diffMin < 1) return '即将执行';
  if (diffMin < 60) return `${diffMin} 分钟后`;
  if (diffHour < 24) return `${diffHour} 小时 ${diffMin % 60} 分钟后`;
  return `${Math.floor(diffHour / 24)} 天后`;
}

function parseTriggerInfo(trigger: string): string {
  if (trigger.includes('interval')) {
    const match = trigger.match(/interval\[(\d+):(\d+):(\d+)\]/);
    if (match) {
      const hours = parseInt(match[1], 10);
      const minutes = parseInt(match[2], 10);
      if (hours > 0) return `每 ${hours}h ${minutes}m`;
      return `每 ${minutes} 分钟`;
    }
  }
  if (trigger.includes('cron')) {
    return '每日定时';
  }
  return trigger;
}

function formatJobName(id: string): string {
  const nameMap: Record<string, string> = {
    update_market_indices: '市场指数更新',
    update_watchlist_prices: '关注列表价格',
    run_daily_analysis: '每日 AI 分析',
  };
  return nameMap[id] || id.replace(/_/g, ' ');
}

function getJobIcon(id: string): { icon: React.ElementType; color: string; bgColor: string } {
  if (id.includes('market')) return { icon: Activity, color: 'text-blue-400', bgColor: 'bg-blue-500/10' };
  if (id.includes('price') || id.includes('watchlist')) return { icon: RefreshCw, color: 'text-green-400', bgColor: 'bg-green-500/10' };
  if (id.includes('analysis')) return { icon: Zap, color: 'text-amber-400', bgColor: 'bg-amber-500/10' };
  return { icon: Timer, color: 'text-gray-400', bgColor: 'bg-gray-500/10' };
}

// === 任务卡片组件 ===

const JobCard: React.FC<{ job: SchedulerJob }> = ({ job }) => {
  const nextRunText = formatNextRun(job.next_run_time);
  const triggerText = parseTriggerInfo(job.trigger);
  const jobName = formatJobName(job.id);
  const { icon: Icon, color, bgColor } = getJobIcon(job.id);
  const isOverdue = nextRunText === '已过期';

  return (
    <div className="flex items-center gap-4 p-4 bg-gray-800/50 border border-gray-700 rounded-xl hover:border-gray-600 transition-colors">
      <div className={`p-3 rounded-lg ${bgColor}`}>
        <Icon className={`w-5 h-5 ${color}`} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-medium text-white">{jobName}</span>
          <span className="text-xs px-2 py-0.5 bg-gray-700 text-gray-400 rounded-full">
            {triggerText}
          </span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <Clock className="w-3.5 h-3.5 text-gray-500" />
          <span className="text-gray-500">下次执行:</span>
          <span className={isOverdue ? 'text-red-400' : 'text-gray-300'}>
            {nextRunText}
          </span>
        </div>
      </div>

      {job.next_run_time && (
        <div className="text-right">
          <div className="text-xs text-gray-500">
            {new Date(job.next_run_time).toLocaleDateString('zh-CN', {
              month: 'short',
              day: 'numeric',
            })}
          </div>
          <div className="text-sm text-gray-400">
            {new Date(job.next_run_time).toLocaleTimeString('zh-CN', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </div>
        </div>
      )}
    </div>
  );
};

// === 主组件 ===

const SchedulerPage: React.FC = () => {
  const toast = useToast();
  const { data: status, isLoading: isStatusLoading } = useSchedulerStatus();
  const { data: jobsData, isLoading: isJobsLoading } = useSchedulerJobs();
  const triggerMutation = useTriggerDailyAnalysis();
  const { refresh } = useRefreshScheduler();

  const jobs = useMemo(() => jobsData?.jobs || [], [jobsData]);
  const isLoading = isStatusLoading || isJobsLoading;

  const handleTrigger = async () => {
    try {
      await triggerMutation.mutateAsync();
      toast.success('每日分析任务已触发');
    } catch {
      toast.error('触发失败，请检查 API Key 配置');
    }
  };

  const handleRefresh = () => {
    refresh();
    toast.info('正在刷新...');
  };

  return (
    <PageLayout
      title="Scheduler"
      subtitle="后台任务调度管理"
      icon={Calendar}
      iconColor="text-amber-400"
      iconBgColor="bg-amber-500/10"
      variant="standard"
      actions={[
        {
          label: '刷新',
          icon: RefreshCw,
          onClick: handleRefresh,
          variant: 'ghost',
        },
      ]}
    >
      <div className="space-y-6">
        {/* 状态概览 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard
            label="调度器状态"
            value={isLoading ? '...' : status?.running ? '运行中' : '已停止'}
            icon={status?.running ? CheckCircle2 : AlertCircle}
            iconColor={status?.running ? 'text-emerald-400' : 'text-red-400'}
            valueColor={status?.running ? 'text-emerald-400' : 'text-red-400'}
          />

          <StatCard
            label="分析任务"
            value={isLoading ? '...' : status?.analysis_in_progress ? '执行中' : '空闲'}
            icon={status?.analysis_in_progress ? Loader2 : Play}
            iconColor={status?.analysis_in_progress ? 'text-amber-400' : 'text-gray-500'}
            valueColor={status?.analysis_in_progress ? 'text-amber-400' : 'text-gray-400'}
            subtitle={status?.analysis_in_progress ? '正在运行 AI 分析' : undefined}
          />

          <StatCard
            label="计划任务"
            value={isLoading ? '...' : status?.jobs_count ?? 0}
            icon={Clock}
            iconColor="text-blue-400"
            valueColor="text-blue-400"
            subtitle={`${jobs.length} 个任务已调度`}
          />
        </div>

        {/* 任务列表 */}
        <PageSection
          title="计划任务列表"
          subtitle="定时执行的后台任务"
          icon={Timer}
          iconColor="text-cyan-400"
        >
          {isLoading ? (
            <LoadingState message="加载任务列表..." />
          ) : jobs.length === 0 ? (
            <EmptyState
              icon={Clock}
              title="暂无计划任务"
              description="调度器当前没有配置任何定时任务"
            />
          ) : (
            <div className="space-y-3">
              {jobs.map((job) => (
                <JobCard key={job.id} job={job} />
              ))}
            </div>
          )}
        </PageSection>

        {/* 手动操作 */}
        <PageSection
          title="手动操作"
          subtitle="立即执行任务"
          icon={Zap}
          iconColor="text-amber-400"
        >
          <div className="space-y-4">
            <div className="p-4 bg-gradient-to-r from-amber-900/20 to-orange-900/20 rounded-lg border border-amber-700/30">
              <div className="flex items-start gap-3 mb-3">
                <Zap className="w-5 h-5 text-amber-400 mt-0.5" />
                <div>
                  <h4 className="font-medium text-white">手动触发每日分析</h4>
                  <p className="text-sm text-gray-400 mt-1">
                    立即对关注列表中的所有股票运行 AI 分析。此操作会消耗 API 配额。
                  </p>
                </div>
              </div>

              <button
                onClick={handleTrigger}
                disabled={triggerMutation.isPending || status?.analysis_in_progress}
                className="w-full bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white py-3 rounded-lg text-sm font-bold disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
              >
                {triggerMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    触发中...
                  </>
                ) : status?.analysis_in_progress ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    分析进行中...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    触发每日分析
                  </>
                )}
              </button>
            </div>

            {/* 说明 */}
            <div className="text-xs text-gray-500 space-y-1">
              <p>• 每日分析会分析关注列表中的所有股票</p>
              <p>• 分析结果会通过 SSE 实时推送到 Dashboard</p>
              <p>• 请确保 AI 提供商配置正确后再触发</p>
            </div>
          </div>
        </PageSection>
      </div>
    </PageLayout>
  );
};

export default SchedulerPage;
