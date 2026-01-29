/**
 * 调度器管理页面
 *
 * 展示调度任务状态、下次运行时间，支持手动触发分析
 */
import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Clock,
  Play,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Loader,
  Timer,
  Zap,
  Calendar,
} from 'lucide-react';
import {
  useSchedulerStatus,
  useSchedulerJobs,
  useTriggerDailyAnalysis,
  useRefreshScheduler,
} from '../hooks/useScheduler';
import type { SchedulerJob } from '../hooks/useScheduler';

/**
 * 格式化下次运行时间为相对时间
 */
function formatNextRun(isoString: string | null): string {
  if (!isoString) return 'Not scheduled';

  const next = new Date(isoString);
  const now = new Date();
  const diffMs = next.getTime() - now.getTime();

  if (diffMs < 0) return 'Overdue';

  const diffMin = Math.floor(diffMs / 60000);
  const diffHour = Math.floor(diffMin / 60);

  if (diffMin < 1) return 'Less than a minute';
  if (diffMin < 60) return `${diffMin}m`;
  if (diffHour < 24) return `${diffHour}h ${diffMin % 60}m`;
  return `${Math.floor(diffHour / 24)}d ${diffHour % 24}h`;
}

/**
 * 解析 trigger 字符串中的有用信息
 */
function parseTriggerInfo(trigger: string): string {
  if (trigger.includes('interval')) {
    const match = trigger.match(/interval\[(\d+):(\d+):(\d+)\]/);
    if (match) {
      const hours = parseInt(match[1], 10);
      const minutes = parseInt(match[2], 10);
      if (hours > 0) return `Every ${hours}h ${minutes}m`;
      return `Every ${minutes}m`;
    }
  }
  if (trigger.includes('cron')) {
    return 'Daily (cron)';
  }
  return trigger;
}

/**
 * 将 job id 转为更友好的显示名称
 */
function formatJobName(id: string): string {
  const nameMap: Record<string, string> = {
    update_market_indices: 'Market Indices',
    update_watchlist_prices: 'Watchlist Prices',
    run_daily_analysis: 'Daily Analysis',
  };
  return nameMap[id] || id.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * 获取 job 的图标颜色
 */
function getJobColor(id: string): string {
  if (id.includes('market')) return 'text-blue-400';
  if (id.includes('price') || id.includes('watchlist')) return 'text-green-400';
  if (id.includes('analysis')) return 'text-amber-400';
  return 'text-gray-400';
}

const JobCard: React.FC<{ job: SchedulerJob }> = ({ job }) => {
  const nextRunText = formatNextRun(job.next_run_time);
  const triggerText = parseTriggerInfo(job.trigger);
  const jobName = formatJobName(job.id);
  const color = getJobColor(job.id);

  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4 hover:border-gray-600 transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <Timer className={`w-4 h-4 ${color}`} />
          <span className="text-sm font-semibold text-white">{jobName}</span>
        </div>
        <span className="text-[10px] bg-gray-700 text-gray-300 px-2 py-0.5 rounded-full">
          {triggerText}
        </span>
      </div>

      <div className="flex items-center gap-2 text-xs text-gray-400">
        <Clock className="w-3 h-3" />
        <span>Next: </span>
        <span className={nextRunText === 'Overdue' ? 'text-red-400' : 'text-gray-300'}>
          {nextRunText}
        </span>
      </div>

      {job.next_run_time && (
        <div className="text-[10px] text-gray-500 mt-1 ml-5">
          {new Date(job.next_run_time).toLocaleString('zh-CN', {
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
          })}
        </div>
      )}
    </div>
  );
};

const SchedulerPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: status, isLoading: isStatusLoading } = useSchedulerStatus();
  const { data: jobsData, isLoading: isJobsLoading } = useSchedulerJobs();
  const triggerMutation = useTriggerDailyAnalysis();
  const { refresh } = useRefreshScheduler();

  const jobs = useMemo(() => jobsData?.jobs || [], [jobsData]);
  const isLoading = isStatusLoading || isJobsLoading;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="shrink-0 px-6 py-4 border-b border-gray-800 bg-gray-900/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/')}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400 hover:text-white"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-500/10 rounded-lg">
                <Calendar className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Scheduler</h1>
                <p className="text-xs text-gray-500">Manage background tasks</p>
              </div>
            </div>
          </div>

          <button
            onClick={refresh}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl mx-auto space-y-6">
          {/* Status Summary */}
          <div className="grid grid-cols-3 gap-4">
            {/* Running Status */}
            <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700 text-center">
              <div className="flex items-center justify-center mb-2">
                {status?.running ? (
                  <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                ) : (
                  <AlertCircle className="w-6 h-6 text-red-400" />
                )}
              </div>
              <div className="text-xs text-gray-400">Status</div>
              <div
                className={`text-lg font-bold ${status?.running ? 'text-emerald-400' : 'text-red-400'}`}
              >
                {isLoading ? '...' : status?.running ? 'Running' : 'Stopped'}
              </div>
            </div>

            {/* Analysis Progress */}
            <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700 text-center">
              <div className="flex items-center justify-center mb-2">
                {status?.analysis_in_progress ? (
                  <Loader className="w-6 h-6 text-amber-400 animate-spin" />
                ) : (
                  <Play className="w-6 h-6 text-gray-500" />
                )}
              </div>
              <div className="text-xs text-gray-400">Analysis</div>
              <div
                className={`text-lg font-bold ${status?.analysis_in_progress ? 'text-amber-400' : 'text-gray-500'}`}
              >
                {isLoading ? '...' : status?.analysis_in_progress ? 'Running' : 'Idle'}
              </div>
            </div>

            {/* Jobs Count */}
            <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700 text-center">
              <div className="flex items-center justify-center mb-2">
                <Clock className="w-6 h-6 text-blue-400" />
              </div>
              <div className="text-xs text-gray-400">Jobs</div>
              <div className="text-lg font-bold text-blue-400">
                {isLoading ? '...' : status?.jobs_count ?? 0}
              </div>
            </div>
          </div>

          {/* Job List */}
          <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700">
            <div className="text-xs text-gray-500 uppercase font-bold mb-3">Scheduled Jobs</div>
            {isLoading ? (
              <div className="flex items-center justify-center py-8 text-gray-500">
                <Loader className="w-5 h-5 animate-spin" />
              </div>
            ) : jobs.length === 0 ? (
              <div className="text-center py-8 text-gray-500 text-sm">No scheduled jobs</div>
            ) : (
              <div className="space-y-2">
                {jobs.map((job) => (
                  <JobCard key={job.id} job={job} />
                ))}
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700">
            <div className="text-xs text-gray-500 uppercase font-bold mb-3">Actions</div>
            <button
              onClick={() => triggerMutation.mutate()}
              disabled={triggerMutation.isPending || status?.analysis_in_progress}
              className="w-full bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white py-3 rounded-lg text-sm font-bold disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
            >
              {triggerMutation.isPending ? (
                <>
                  <Loader className="w-4 h-4 animate-spin" />
                  Triggering...
                </>
              ) : status?.analysis_in_progress ? (
                <>
                  <Loader className="w-4 h-4 animate-spin" />
                  Analysis in progress...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Trigger Daily Analysis
                </>
              )}
            </button>

            {triggerMutation.isSuccess && (
              <p className="text-xs text-emerald-400 text-center mt-2">
                Daily analysis triggered successfully
              </p>
            )}

            {triggerMutation.isError && (
              <p className="text-xs text-red-400 text-center mt-2">
                Failed to trigger analysis. Check API key configuration.
              </p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default SchedulerPage;
