/**
 * 设置页面
 *
 * 完整功能的应用程序设置，包含账户、通知、安全、系统健康等模块
 * 使用 narrow 布局变体适合配置类页面
 */
import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Settings,
  User,
  Bell,
  Shield,
  Activity,
  Database,
  ChevronRight,
  ChevronDown,
  LogOut,
  Cpu,
  HardDrive,
  Clock,
  AlertCircle,
  CheckCircle,
  AlertTriangle,
  Trash2,
  RefreshCw,
  Mail,
  Key,
  Loader2,
  Send,
  MessageCircle,
} from 'lucide-react';
import PageLayout from '../components/layout/PageLayout';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../components/Toast';
import {
  useHealthReport,
  useHealthMetrics,
  useHealthErrors,
  useClearHealthErrors,
  useSystemUptime,
  useSubgraphComparison,
  useUpdateRollout,
  useNotificationConfigs,
  useUpsertNotificationConfig,
  useDeleteNotificationConfig,
  useNotificationLogs,
  useTestNotification,
} from '../hooks';
import type * as T from '../src/types/schema';

// === 类型定义 ===

interface SettingsSection {
  id: string;
  icon: React.ElementType;
  title: string;
  description: string;
  iconColor?: string;
}

// === 辅助组件 ===

const StatusBadge: React.FC<{ status: T.HealthStatus }> = ({ status }) => {
  const config: Record<T.HealthStatus, { bg: string; text: string; icon: React.ElementType }> = {
    healthy: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', icon: CheckCircle },
    degraded: { bg: 'bg-amber-500/20', text: 'text-amber-400', icon: AlertTriangle },
    unhealthy: { bg: 'bg-red-500/20', text: 'text-red-400', icon: AlertCircle },
    unknown: { bg: 'bg-stone-500/20', text: 'text-stone-400', icon: AlertCircle },
  };
  const cfg = config[status] || config.unknown;
  const Icon = cfg.icon;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${cfg.bg} ${cfg.text}`}>
      <Icon className="w-3.5 h-3.5" />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
};

const MetricBar: React.FC<{ label: string; value: number; unit?: string; color?: string }> = ({
  label,
  value,
  unit = '%',
  color = 'blue',
}) => {
  const colorMap: Record<string, string> = {
    blue: 'bg-accent',
    green: 'bg-emerald-500',
    yellow: 'bg-amber-500',
    red: 'bg-red-500',
  };
  const barColor = value > 90 ? colorMap.red : value > 70 ? colorMap.yellow : colorMap[color];

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-stone-400">{label}</span>
        <span className="text-white font-medium">{value.toFixed(1)}{unit}</span>
      </div>
      <div className="h-1.5 bg-surface-muted rounded-full overflow-hidden">
        <div className={`h-full ${barColor} rounded-full transition-all`} style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
    </div>
  );
};

// === 主组件 ===

const SettingsPage: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout, isAuthenticated } = useAuth();
  const toast = useToast();

  // 展开状态
  const [expandedSection, setExpandedSection] = useState<string | null>('account');

  // 健康监控数据
  const { data: healthReport, isLoading: isHealthLoading, refetch: refetchHealth } = useHealthReport();
  const { data: metrics } = useHealthMetrics();
  const { data: errorsData } = useHealthErrors(5);
  const { data: uptimeData } = useSystemUptime();
  const clearErrors = useClearHealthErrors();

  // 处理登出
  const handleLogout = async () => {
    try {
      await logout();
      toast.success('已退出登录');
      navigate('/login');
    } catch {
      toast.error('登出失败');
    }
  };

  // 清除错误记录
  const handleClearErrors = async () => {
    try {
      await clearErrors.mutateAsync();
      toast.success('错误记录已清除');
    } catch {
      toast.error('清除失败');
    }
  };

  // 设置分区配置
  const sections: SettingsSection[] = [
    { id: 'account', icon: User, title: 'Account', description: '账户信息与登录设置', iconColor: 'text-accent' },
    { id: 'notifications', icon: Bell, title: 'Notifications', description: '通知和提醒配置', iconColor: 'text-amber-400' },
    { id: 'security', icon: Shield, title: 'Security', description: '安全和隐私设置', iconColor: 'text-emerald-400' },
    { id: 'health', icon: Activity, title: 'System Health', description: '系统运行状态监控', iconColor: 'text-purple-400' },
    { id: 'rollout', icon: RefreshCw, title: 'Rollout', description: '灰度发布与架构切换', iconColor: 'text-orange-400' },
    { id: 'data', icon: Database, title: 'Data', description: '数据存储和缓存管理', iconColor: 'text-cyan-400' },
  ];

  const toggleSection = (id: string) => {
    setExpandedSection(expandedSection === id ? null : id);
  };

  // === 渲染各分区内容 ===

  const renderAccountSection = () => (
    <div className="space-y-4">
      {isAuthenticated && user ? (
        <>
          {/* 用户信息卡片 */}
          <div className="flex items-center gap-4 p-4 bg-surface-overlay/50 rounded-lg border border-border-strong">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-amber-500 to-purple-600 flex items-center justify-center text-2xl font-bold text-white">
              {user.display_name?.[0]?.toUpperCase() || user.email[0].toUpperCase()}
            </div>
            <div className="flex-1">
              <h4 className="text-white font-medium">{user.display_name || '未设置昵称'}</h4>
              <p className="text-sm text-stone-400 flex items-center gap-1">
                <Mail className="w-3.5 h-3.5" />
                {user.email}
              </p>
              <p className="text-xs text-stone-500 mt-1">
                {user.email_verified ? (
                  <span className="text-emerald-400 flex items-center gap-1"><CheckCircle className="w-3 h-3" />邮箱已验证</span>
                ) : (
                  <span className="text-amber-400 flex items-center gap-1"><AlertTriangle className="w-3 h-3" />邮箱未验证</span>
                )}
              </p>
            </div>
          </div>

          {/* 账户操作 */}
          <div className="space-y-2">
            <button className="w-full flex items-center justify-between px-4 py-3 bg-surface-overlay/30 hover:bg-surface-overlay/50 rounded-lg text-sm text-stone-300 transition-colors">
              <span>修改昵称</span>
              <ChevronRight className="w-4 h-4 text-stone-600" />
            </button>
            <button className="w-full flex items-center justify-between px-4 py-3 bg-surface-overlay/30 hover:bg-surface-overlay/50 rounded-lg text-sm text-stone-300 transition-colors">
              <span>修改密码</span>
              <ChevronRight className="w-4 h-4 text-stone-600" />
            </button>
            <button
              onClick={handleLogout}
              className="w-full flex items-center justify-between px-4 py-3 bg-red-900/20 hover:bg-red-900/30 rounded-lg text-sm text-red-400 transition-colors border border-red-900/30"
            >
              <span className="flex items-center gap-2">
                <LogOut className="w-4 h-4" />
                退出登录
              </span>
            </button>
          </div>
        </>
      ) : (
        <div className="text-center py-8">
          <p className="text-stone-400 mb-4">未登录</p>
          <button
            onClick={() => navigate('/login')}
            className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg text-sm transition-colors"
          >
            前往登录
          </button>
        </div>
      )}
    </div>
  );

  const renderNotificationsSection = () => {
    const { accessToken } = useAuth();
    const { data: configs, isLoading: configsLoading } = useNotificationConfigs(accessToken);
    const upsertMutation = useUpsertNotificationConfig(accessToken);
    const deleteMutation = useDeleteNotificationConfig(accessToken);
    const testMutation = useTestNotification(accessToken);
    const { data: logs } = useNotificationLogs(accessToken, 20);

    const telegramConfig = configs?.find((c) => c.channel === 'telegram');

    const [chatId, setChatId] = useState(telegramConfig?.channel_user_id ?? '');
    const [threshold, setThreshold] = useState(telegramConfig?.signal_threshold ?? 'STRONG_BUY');
    const [quietStart, setQuietStart] = useState<number | null>(telegramConfig?.quiet_hours_start ?? null);
    const [quietEnd, setQuietEnd] = useState<number | null>(telegramConfig?.quiet_hours_end ?? null);
    const [enabled, setEnabled] = useState(telegramConfig?.is_enabled ?? true);

    // 当配置加载完成后同步本地状态
    const syncedRef = React.useRef(false);
    React.useEffect(() => {
      if (telegramConfig && !syncedRef.current) {
        setChatId(telegramConfig.channel_user_id ?? '');
        setThreshold(telegramConfig.signal_threshold);
        setQuietStart(telegramConfig.quiet_hours_start);
        setQuietEnd(telegramConfig.quiet_hours_end);
        setEnabled(telegramConfig.is_enabled);
        syncedRef.current = true;
      }
    }, [telegramConfig]);

    const handleSave = useCallback(() => {
      upsertMutation.mutate({
        channel: 'telegram',
        channel_user_id: chatId || null,
        is_enabled: enabled,
        signal_threshold: threshold,
        quiet_hours_start: quietStart,
        quiet_hours_end: quietEnd,
      });
    }, [chatId, enabled, threshold, quietStart, quietEnd, upsertMutation]);

    const handleTest = useCallback(() => {
      if (!chatId) return;
      testMutation.mutate({ channel: 'telegram', channel_user_id: chatId });
    }, [chatId, testMutation]);

    if (configsLoading) {
      return (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-5 h-5 animate-spin text-stone-400" />
        </div>
      );
    }

    return (
      <div className="space-y-4">
        {/* Telegram 配置 */}
        <div className="p-4 bg-surface-overlay/30 rounded-lg border border-border-strong">
          <div className="flex items-center gap-3 mb-4">
            <MessageCircle className="w-5 h-5 text-blue-400" />
            <div className="flex-1">
              <h4 className="text-white font-medium">Telegram 推送</h4>
              <p className="text-xs text-stone-500">通过 Telegram Bot 接收分析通知</p>
            </div>
            <button
              onClick={() => { setEnabled(!enabled); }}
              className={`relative w-11 h-6 rounded-full transition-colors ${
                enabled ? 'bg-accent' : 'bg-surface-muted'
              }`}
            >
              <span
                className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                  enabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* Chat ID */}
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-stone-400 mb-1">Chat ID</label>
              <input
                type="text"
                value={chatId}
                onChange={(e) => setChatId(e.target.value)}
                placeholder="输入 Telegram Chat ID"
                className="w-full px-3 py-2 bg-surface-muted rounded-lg text-sm text-white border border-border focus:border-accent focus:outline-none"
              />
            </div>

            {/* 信号阈值 */}
            <div>
              <label className="block text-xs text-stone-400 mb-1">信号阈值</label>
              <div className="flex gap-2">
                {(['STRONG_BUY', 'BUY', 'ALL'] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setThreshold(t)}
                    className={`flex-1 py-1.5 text-xs rounded-lg border transition-colors ${
                      threshold === t
                        ? 'bg-accent/20 border-accent text-accent'
                        : 'bg-surface-muted border-border text-stone-400 hover:text-stone-300'
                    }`}
                  >
                    {t === 'STRONG_BUY' ? '强烈信号' : t === 'BUY' ? '买卖信号' : '全部'}
                  </button>
                ))}
              </div>
            </div>

            {/* 静默时段 */}
            <div>
              <label className="block text-xs text-stone-400 mb-1">静默时段（不推送）</label>
              <div className="flex items-center gap-2">
                <select
                  value={quietStart ?? ''}
                  onChange={(e) => setQuietStart(e.target.value ? Number(e.target.value) : null)}
                  className="flex-1 px-2 py-1.5 bg-surface-muted rounded-lg text-sm text-white border border-border focus:border-accent focus:outline-none"
                >
                  <option value="">不设置</option>
                  {Array.from({ length: 24 }, (_, i) => (
                    <option key={i} value={i}>{String(i).padStart(2, '0')}:00</option>
                  ))}
                </select>
                <span className="text-stone-500 text-xs">至</span>
                <select
                  value={quietEnd ?? ''}
                  onChange={(e) => setQuietEnd(e.target.value ? Number(e.target.value) : null)}
                  className="flex-1 px-2 py-1.5 bg-surface-muted rounded-lg text-sm text-white border border-border focus:border-accent focus:outline-none"
                >
                  <option value="">不设置</option>
                  {Array.from({ length: 24 }, (_, i) => (
                    <option key={i} value={i}>{String(i).padStart(2, '0')}:00</option>
                  ))}
                </select>
              </div>
            </div>

            {/* 操作按钮 */}
            <div className="flex gap-2 pt-1">
              <button
                onClick={handleSave}
                disabled={upsertMutation.isPending}
                className="flex-1 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg text-sm transition-colors disabled:opacity-50"
              >
                {upsertMutation.isPending ? '保存中...' : '保存配置'}
              </button>
              <button
                onClick={handleTest}
                disabled={!chatId || testMutation.isPending}
                className="px-4 py-2 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 rounded-lg text-sm transition-colors border border-blue-600/30 disabled:opacity-50 flex items-center gap-1.5"
              >
                <Send className="w-3.5 h-3.5" />
                {testMutation.isPending ? '发送中...' : '测试'}
              </button>
              {telegramConfig && (
                <button
                  onClick={() => deleteMutation.mutate('telegram')}
                  disabled={deleteMutation.isPending}
                  className="px-3 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg text-sm transition-colors border border-red-600/30 disabled:opacity-50"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* 状态反馈 */}
            {upsertMutation.isSuccess && (
              <p className="text-xs text-green-400 flex items-center gap-1">
                <CheckCircle className="w-3 h-3" /> 配置已保存
              </p>
            )}
            {testMutation.isSuccess && (
              <p className="text-xs text-green-400 flex items-center gap-1">
                <CheckCircle className="w-3 h-3" /> 测试通知已发送
              </p>
            )}
            {testMutation.isError && (
              <p className="text-xs text-red-400 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" /> 发送失败，请检查 Bot Token 和 Chat ID
              </p>
            )}
          </div>
        </div>

        {/* 发送日志 */}
        {logs && logs.length > 0 && (
          <div className="p-4 bg-surface-overlay/30 rounded-lg border border-border-strong">
            <h4 className="text-white font-medium text-sm mb-3">发送日志</h4>
            <div className="space-y-2 max-h-48 overflow-y-auto custom-scrollbar">
              {logs.map((log) => (
                <div
                  key={log.id}
                  className="flex items-center justify-between text-xs py-1.5 border-b border-border/50 last:border-0"
                >
                  <div className="flex-1 min-w-0">
                    <span className="text-stone-300 truncate block">{log.title}</span>
                    <span className="text-stone-500">
                      {new Date(log.sent_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <span className={`ml-2 shrink-0 ${log.delivered ? 'text-green-400' : 'text-red-400'}`}>
                    {log.delivered ? '✓ 已送达' : '✗ 失败'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderSecuritySection = () => (
    <div className="space-y-4">
      <div className="p-4 bg-surface-overlay/30 rounded-lg border border-border-strong">
        <div className="flex items-center gap-3 mb-3">
          <Key className="w-5 h-5 text-emerald-400" />
          <div>
            <h4 className="text-white font-medium">Passkey 管理</h4>
            <p className="text-xs text-stone-500">使用生物识别或安全密钥登录</p>
          </div>
        </div>
        <button className="w-full py-2 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 rounded-lg text-sm transition-colors border border-emerald-600/30">
          添加 Passkey
        </button>
      </div>

      <div className="p-4 bg-surface-overlay/30 rounded-lg border border-border-strong">
        <h4 className="text-white font-medium mb-2">第三方账号绑定</h4>
        <p className="text-xs text-stone-500 mb-3">关联第三方账号以快速登录</p>
        <div className="space-y-2">
          <OAuthBindingRow provider="Google" connected={false} />
          <OAuthBindingRow provider="GitHub" connected={false} />
        </div>
      </div>

      <button className="w-full flex items-center justify-between px-4 py-3 bg-surface-overlay/30 hover:bg-surface-overlay/50 rounded-lg text-sm text-stone-300 transition-colors">
        <span>登录历史</span>
        <ChevronRight className="w-4 h-4 text-stone-600" />
      </button>
    </div>
  );

  const renderHealthSection = () => (
    <div className="space-y-4">
      {/* 总体状态 */}
      <div className="flex items-center justify-between p-4 bg-surface-overlay/50 rounded-lg border border-border-strong">
        <div className="flex items-center gap-3">
          <Activity className="w-5 h-5 text-purple-400" />
          <div>
            <h4 className="text-white font-medium">系统状态</h4>
            <p className="text-xs text-stone-500">
              {uptimeData ? `运行时间: ${uptimeData.uptime_formatted}` : '加载中...'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isHealthLoading ? (
            <Loader2 className="w-4 h-4 animate-spin text-stone-400" />
          ) : (
            <StatusBadge status={healthReport?.overall_status || 'unknown'} />
          )}
          <button
            onClick={() => refetchHealth()}
            className="p-1.5 hover:bg-surface-muted rounded transition-colors"
            title="刷新"
          >
            <RefreshCw className="w-4 h-4 text-stone-400" />
          </button>
        </div>
      </div>

      {/* 系统指标 */}
      {metrics && (
        <div className="p-4 bg-surface-overlay/30 rounded-lg border border-border-strong space-y-3">
          <h4 className="text-sm font-medium text-white flex items-center gap-2">
            <Cpu className="w-4 h-4 text-accent" />
            系统资源
          </h4>
          <MetricBar label="CPU 使用率" value={metrics.cpu_percent} color="blue" />
          <MetricBar label="内存使用率" value={metrics.memory_percent} color="green" />
          <div className="text-xs text-stone-500">
            {metrics.memory_used_mb.toFixed(0)} MB / {metrics.memory_total_mb.toFixed(0)} MB
          </div>
          <MetricBar label="磁盘使用率" value={metrics.disk_percent} color="cyan" />
          <div className="text-xs text-stone-500">
            {metrics.disk_used_gb.toFixed(1)} GB / {metrics.disk_total_gb.toFixed(1)} GB
          </div>
        </div>
      )}

      {/* 组件状态 */}
      {healthReport?.components && healthReport.components.length > 0 && (
        <div className="p-4 bg-surface-overlay/30 rounded-lg border border-border-strong">
          <h4 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
            <HardDrive className="w-4 h-4 text-cyan-400" />
            组件状态
          </h4>
          <div className="space-y-2">
            {healthReport.components.map((comp: T.ComponentHealth) => (
              <div key={comp.name} className="flex items-center justify-between text-sm">
                <span className="text-stone-300">{comp.name}</span>
                <div className="flex items-center gap-2">
                  {comp.latency_ms !== null && comp.latency_ms !== undefined && (
                    <span className="text-xs text-stone-500">{comp.latency_ms}ms</span>
                  )}
                  <StatusBadge status={comp.status} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 最近错误 */}
      {errorsData?.errors && errorsData.errors.length > 0 && (
        <div className="p-4 bg-surface-overlay/30 rounded-lg border border-border-strong">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-medium text-white flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-400" />
              最近错误 ({errorsData.total})
            </h4>
            <button
              onClick={handleClearErrors}
              disabled={clearErrors.isPending}
              className="text-xs text-red-400 hover:text-red-300 flex items-center gap-1 disabled:opacity-50"
            >
              {clearErrors.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />}
              清除
            </button>
          </div>
          <div className="space-y-2 max-h-40 overflow-y-auto custom-scrollbar">
            {errorsData.errors.map((err: T.ErrorRecord, idx: number) => (
              <div key={idx} className="text-xs p-2 bg-red-900/20 rounded border border-red-900/30">
                <div className="flex justify-between text-red-300">
                  <span>{err.component}</span>
                  <span>{new Date(err.timestamp).toLocaleTimeString()}</span>
                </div>
                <p className="text-stone-400 mt-1 truncate">{err.message}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  const renderDataSection = () => (
    <div className="space-y-3">
      <button className="w-full flex items-center justify-between px-4 py-3 bg-surface-overlay/30 hover:bg-surface-overlay/50 rounded-lg text-sm text-stone-300 transition-colors">
        <span className="flex items-center gap-2">
          <Trash2 className="w-4 h-4 text-stone-500" />
          清除本地缓存
        </span>
        <ChevronRight className="w-4 h-4 text-stone-600" />
      </button>
      <button className="w-full flex items-center justify-between px-4 py-3 bg-surface-overlay/30 hover:bg-surface-overlay/50 rounded-lg text-sm text-stone-300 transition-colors">
        <span className="flex items-center gap-2">
          <Database className="w-4 h-4 text-stone-500" />
          导出分析数据
        </span>
        <ChevronRight className="w-4 h-4 text-stone-600" />
      </button>
      <button className="w-full flex items-center justify-between px-4 py-3 bg-surface-overlay/30 hover:bg-surface-overlay/50 rounded-lg text-sm text-stone-300 transition-colors">
        <span className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-stone-500" />
          查看分析历史
        </span>
        <ChevronRight className="w-4 h-4 text-stone-600" />
      </button>
    </div>
  );

  const renderRolloutSection = () => {
    // 使用真实的 hooks
    const { data: comparison, isLoading: isComparisonLoading, refetch: refetchComparison } = useSubgraphComparison(7);
    const updateRollout = useUpdateRollout();
    const [localRollout, setLocalRollout] = useState<number>(0);
    const [forceUsers, setForceUsers] = useState<string>('');

    // 同步服务端数据到本地状态
    React.useEffect(() => {
      if (comparison?.current_rollout_percentage !== undefined) {
        setLocalRollout(comparison.current_rollout_percentage);
      }
    }, [comparison?.current_rollout_percentage]);

    const handleSaveRollout = async () => {
      try {
        await updateRollout.mutateAsync(localRollout);
        toast.success('灰度配置已更新');
        refetchComparison();
      } catch {
        toast.error('更新失败');
      }
    };

    // 推荐操作的颜色和图标
    const getRecommendationStyle = (action: string) => {
      switch (action) {
        case 'subgraph_ready':
          return { bg: 'bg-emerald-500/20', border: 'border-emerald-500/30', text: 'text-emerald-400', icon: CheckCircle };
        case 'monolith_better':
          return { bg: 'bg-red-500/20', border: 'border-red-500/30', text: 'text-red-400', icon: AlertTriangle };
        default:
          return { bg: 'bg-amber-500/20', border: 'border-amber-500/30', text: 'text-amber-400', icon: AlertCircle };
      }
    };

    return (
      <div className="space-y-4">
        {/* A/B 对比数据卡片 */}
        {isComparisonLoading ? (
          <div className="p-4 bg-surface-overlay/30 rounded-lg border border-border-strong flex items-center justify-center">
            <Loader2 className="w-5 h-5 animate-spin text-stone-400" />
            <span className="ml-2 text-stone-400 text-sm">加载对比数据...</span>
          </div>
        ) : comparison ? (
          <>
            {/* 推荐操作 */}
            {comparison.recommendation && (
              <div className={`p-4 rounded-lg border ${getRecommendationStyle(comparison.recommendation.action).bg} ${getRecommendationStyle(comparison.recommendation.action).border}`}>
                <div className="flex items-start gap-3">
                  {React.createElement(getRecommendationStyle(comparison.recommendation.action).icon, {
                    className: `w-5 h-5 ${getRecommendationStyle(comparison.recommendation.action).text} flex-shrink-0 mt-0.5`
                  })}
                  <div className="flex-1">
                    <h4 className={`font-medium ${getRecommendationStyle(comparison.recommendation.action).text}`}>
                      {comparison.recommendation.action === 'subgraph_ready' && '✓ SubGraph 已就绪'}
                      {comparison.recommendation.action === 'monolith_better' && '⚠ Monolith 表现更优'}
                      {comparison.recommendation.action === 'needs_more_data' && '⏳ 需要更多数据'}
                    </h4>
                    <p className="text-xs text-stone-400 mt-1">{comparison.recommendation.reason}</p>
                    <p className="text-xs text-stone-500 mt-2">
                      建议灰度比例: <span className="text-orange-400 font-mono">{comparison.recommendation.suggested_rollout}%</span>
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Monolith vs SubGraph 对比 */}
            <div className="grid grid-cols-2 gap-3">
              {/* Monolith 统计 */}
              <div className="p-4 bg-surface-overlay/30 rounded-lg border border-border-strong">
                <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-blue-400" />
                  Monolith
                </h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-stone-400">样本数</span>
                    <span className="text-white font-mono">{comparison.monolith.count}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-stone-400">成功率</span>
                    <span className={`font-mono ${(comparison.monolith.success_rate ?? 0) >= 90 ? 'text-emerald-400' : 'text-amber-400'}`}>
                      {comparison.monolith.success_rate?.toFixed(1) ?? '-'}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-stone-400">平均耗时</span>
                    <span className="text-white font-mono">{comparison.monolith.avg_elapsed_seconds?.toFixed(1) ?? '-'}s</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-stone-400">平均置信度</span>
                    <span className="text-white font-mono">{comparison.monolith.avg_confidence?.toFixed(0) ?? '-'}</span>
                  </div>
                </div>
              </div>

              {/* SubGraph 统计 */}
              <div className="p-4 bg-surface-overlay/30 rounded-lg border border-orange-500/30">
                <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-orange-400" />
                  SubGraph
                </h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-stone-400">样本数</span>
                    <span className="text-white font-mono">{comparison.subgraph.count}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-stone-400">成功率</span>
                    <span className={`font-mono ${(comparison.subgraph.success_rate ?? 0) >= 90 ? 'text-emerald-400' : 'text-amber-400'}`}>
                      {comparison.subgraph.success_rate?.toFixed(1) ?? '-'}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-stone-400">平均耗时</span>
                    <span className="text-white font-mono">{comparison.subgraph.avg_elapsed_seconds?.toFixed(1) ?? '-'}s</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-stone-400">平均置信度</span>
                    <span className="text-white font-mono">{comparison.subgraph.avg_confidence?.toFixed(0) ?? '-'}</span>
                  </div>
                </div>
              </div>
            </div>

            <p className="text-xs text-stone-500 text-center">
              统计周期: 最近 {comparison.period_days} 天
            </p>
          </>
        ) : null}

        {/* 灰度比例滑块 */}
        <div className="p-4 bg-surface-overlay/30 rounded-lg border border-border-strong">
          <h4 className="text-white font-medium mb-2">SubGraph 架构灰度比例</h4>
          <div className="flex items-center gap-4">
            <input
              type="range"
              min="0"
              max="100"
              value={localRollout}
              onChange={(e) => setLocalRollout(parseInt(e.target.value))}
              className="flex-1 h-2 bg-surface-muted rounded-lg appearance-none cursor-pointer accent-orange-500"
            />
            <span className="text-orange-400 font-mono w-12 text-right">{localRollout}%</span>
          </div>
          <p className="text-xs text-stone-500 mt-2">
            控制多少比例的请求将路由到新的 SubGraph 模块化架构。
          </p>
        </div>

        {/* 强制启用用户 */}
        <div className="p-4 bg-surface-overlay/30 rounded-lg border border-border-strong">
          <h4 className="text-white font-medium mb-2">强制启用用户</h4>
          <textarea
            value={forceUsers}
            onChange={(e) => setForceUsers(e.target.value)}
            placeholder="用户 ID，逗号分隔"
            className="w-full h-20 px-3 py-2 bg-surface-muted border border-stone-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
          />
        </div>

        {/* 保存按钮 */}
        <button
          onClick={handleSaveRollout}
          disabled={updateRollout.isPending}
          className="w-full py-2 bg-orange-600 hover:bg-orange-500 text-white rounded-lg text-sm transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {updateRollout.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
          保存灰度配置
        </button>
      </div>
    );
  };

  const renderSectionContent = (id: string) => {
    switch (id) {
      case 'account': return renderAccountSection();
      case 'notifications': return renderNotificationsSection();
      case 'security': return renderSecuritySection();
      case 'health': return renderHealthSection();
      case 'rollout': return renderRolloutSection();
      case 'data': return renderDataSection();
      default: return null;
    }
  };

  return (
    <PageLayout
      title="Settings"
      subtitle="应用程序设置"
      icon={Settings}
      iconColor="text-stone-400"
      iconBgColor="bg-stone-500/10"
      variant="narrow"
    >
      <div className="space-y-3">
        {sections.map((section) => (
          <div
            key={section.id}
            className="bg-surface-overlay/50 rounded-xl border border-border-strong overflow-hidden"
          >
            {/* Section Header */}
            <button
              onClick={() => toggleSection(section.id)}
              className="w-full p-4 flex items-center justify-between hover:bg-surface-overlay/30 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 bg-surface-muted rounded-lg">
                  <section.icon className={`w-5 h-5 ${section.iconColor || 'text-stone-400'}`} />
                </div>
                <div className="text-left">
                  <h3 className="font-medium text-white">{section.title}</h3>
                  <p className="text-xs text-stone-500">{section.description}</p>
                </div>
              </div>
              {expandedSection === section.id ? (
                <ChevronDown className="w-5 h-5 text-stone-500" />
              ) : (
                <ChevronRight className="w-5 h-5 text-stone-500" />
              )}
            </button>

            {/* Section Content */}
            {expandedSection === section.id && (
              <div className="px-4 pb-4 border-t border-border-strong/50 pt-4">
                {renderSectionContent(section.id)}
              </div>
            )}
          </div>
        ))}
      </div>
    </PageLayout>
  );
};

// === 辅助组件 ===

const OAuthBindingRow: React.FC<{ provider: string; connected: boolean }> = ({ provider, connected }) => (
  <div className="flex items-center justify-between py-2">
    <span className="text-sm text-stone-300">{provider}</span>
    {connected ? (
      <button className="text-xs text-red-400 hover:text-red-300 px-2 py-1 rounded hover:bg-red-900/20 transition-colors">
        解绑
      </button>
    ) : (
      <button className="text-xs text-accent hover:text-amber-300 px-2 py-1 rounded hover:bg-amber-900/20 transition-colors">
        绑定
      </button>
    )}
  </div>
);

export default SettingsPage;
