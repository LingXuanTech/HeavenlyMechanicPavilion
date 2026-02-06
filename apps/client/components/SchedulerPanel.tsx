/**
 * 调度器管理面板
 *
 * 展示调度任务状态、下次运行时间，支持手动触发分析
 */
import React, { useMemo } from 'react';
import {
  X,
  Clock,
  Play,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Loader,
  Timer,
  Zap,
} from 'lucide-react';
import {
  useSchedulerStatus,
  useSchedulerJobs,
  useTriggerDailyAnalysis,
  useRefreshScheduler,
} from '../hooks/useScheduler';
import type { SchedulerJob } from '../hooks/useScheduler';

interface SchedulerPanelProps {
  onClose: () => void;
}

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
    // e.g. "interval[0:05:00]" -> "Every 5 min"
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
  if (id.includes('market')) return 'text-accent';
  if (id.includes('price') || id.includes('watchlist')) return 'text-green-400';
  if (id.includes('analysis')) return 'text-amber-400';
  return 'text-stone-400';
}

const JobCard: React.FC<{ job: SchedulerJob }> = ({ job }) => {
  const nextRunText = formatNextRun(job.next_run_time);
  const triggerText = parseTriggerInfo(job.trigger);
  const jobName = formatJobName(job.id);
  const color = getJobColor(job.id);

  return (
    <div className="bg-surface-overlay/50 border border-border-strong/50 rounded-lg p-4 hover:border-border-strong transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <Timer className={`w-4 h-4 ${color}`} />
          <span className="text-sm font-semibold text-white">{jobName}</span>
        </div>
        <span className="text-[10px] bg-surface-muted text-stone-300 px-2 py-0.5 rounded-full">
          {triggerText}
        </span>
      </div>

      <div className="flex items-center gap-2 text-xs text-stone-400">
        <Clock className="w-3 h-3" />
        <span>Next: </span>
        <span className={nextRunText === 'Overdue' ? 'text-red-400' : 'text-stone-300'}>
          {nextRunText}
        </span>
      </div>

      {job.next_run_time && (
        <div className="text-[10px] text-stone-500 mt-1 ml-5">
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

const SchedulerPanel: React.FC<SchedulerPanelProps> = ({ onClose }) => {
  const { data: status, isLoading: isStatusLoading } = useSchedulerStatus();
  const { data: jobsData, isLoading: isJobsLoading } = useSchedulerJobs();
  const triggerMutation = useTriggerDailyAnalysis();
  const { refresh } = useRefreshScheduler();

  const jobs = useMemo(() => jobsData?.jobs || [], [jobsData]);
  const isLoading = isStatusLoading || isJobsLoading;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-surface-raised border border-border-strong rounded-xl w-full max-w-lg shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-accent/10 rounded-lg">
              <Zap className="w-5 h-5 text-accent" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Scheduler</h2>
              <p className="text-xs text-stone-400">Manage background tasks</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={refresh}
              className="p-2 text-stone-400 hover:text-stone-50 hover:bg-surface-overlay rounded-lg transition-colors"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="p-2 text-stone-400 hover:text-stone-50 hover:bg-surface-overlay rounded-lg transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Status Summary */}
        <div className="px-5 pt-4 pb-3">
          <div className="grid grid-cols-3 gap-3">
            {/* Running Status */}
            <div className="bg-surface-overlay/50 rounded-lg p-3 text-center">
              <div className="flex items-center justify-center mb-1">
                {status?.running ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-red-400" />
                )}
              </div>
              <div className="text-xs text-stone-400">Status</div>
              <div
                className={`text-sm font-bold ${status?.running ? 'text-emerald-400' : 'text-red-400'}`}
              >
                {isLoading ? '...' : status?.running ? 'Running' : 'Stopped'}
              </div>
            </div>

            {/* Analysis Progress */}
            <div className="bg-surface-overlay/50 rounded-lg p-3 text-center">
              <div className="flex items-center justify-center mb-1">
                {status?.analysis_in_progress ? (
                  <Loader className="w-5 h-5 text-amber-400 animate-spin" />
                ) : (
                  <Play className="w-5 h-5 text-stone-500" />
                )}
              </div>
              <div className="text-xs text-stone-400">Analysis</div>
              <div
                className={`text-sm font-bold ${status?.analysis_in_progress ? 'text-amber-400' : 'text-stone-500'}`}
              >
                {isLoading ? '...' : status?.analysis_in_progress ? 'Running' : 'Idle'}
              </div>
            </div>

            {/* Jobs Count */}
            <div className="bg-surface-overlay/50 rounded-lg p-3 text-center">
              <div className="flex items-center justify-center mb-1">
                <Clock className="w-5 h-5 text-accent" />
              </div>
              <div className="text-xs text-stone-400">Jobs</div>
              <div className="text-sm font-bold text-accent">
                {isLoading ? '...' : status?.jobs_count ?? 0}
              </div>
            </div>
          </div>
        </div>

        {/* Job List */}
        <div className="px-5 pb-3">
          <div className="text-xs text-stone-500 uppercase font-bold mb-2">Scheduled Jobs</div>
          {isLoading ? (
            <div className="flex items-center justify-center py-8 text-stone-500">
              <Loader className="w-5 h-5 animate-spin" />
            </div>
          ) : jobs.length === 0 ? (
            <div className="text-center py-8 text-stone-500 text-sm">No scheduled jobs</div>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
              {jobs.map((job) => (
                <JobCard key={job.id} job={job} />
              ))}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="px-5 pb-5 pt-2 border-t border-border">
          <button
            onClick={() => triggerMutation.mutate()}
            disabled={triggerMutation.isPending || status?.analysis_in_progress}
            className="w-full bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white py-2.5 rounded-lg text-sm font-bold disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
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
    </div>
  );
};

export default SchedulerPanel;
