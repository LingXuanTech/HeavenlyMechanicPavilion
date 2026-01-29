/**
 * 设置页面
 *
 * 完整功能的应用程序设置，包含账户、通知、安全、系统健康等模块
 * 使用 narrow 布局变体适合配置类页面
 */
import React, { useState } from 'react';
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
} from '../hooks';
import type { HealthStatus, ComponentHealth, ErrorRecord } from '../types';

// === 类型定义 ===

interface SettingsSection {
  id: string;
  icon: React.ElementType;
  title: string;
  description: string;
  iconColor?: string;
}

// === 辅助组件 ===

const StatusBadge: React.FC<{ status: HealthStatus }> = ({ status }) => {
  const config: Record<HealthStatus, { bg: string; text: string; icon: React.ElementType }> = {
    healthy: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', icon: CheckCircle },
    degraded: { bg: 'bg-amber-500/20', text: 'text-amber-400', icon: AlertTriangle },
    unhealthy: { bg: 'bg-red-500/20', text: 'text-red-400', icon: AlertCircle },
    unknown: { bg: 'bg-gray-500/20', text: 'text-gray-400', icon: AlertCircle },
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
    blue: 'bg-blue-500',
    green: 'bg-emerald-500',
    yellow: 'bg-amber-500',
    red: 'bg-red-500',
  };
  const barColor = value > 90 ? colorMap.red : value > 70 ? colorMap.yellow : colorMap[color];

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-gray-400">{label}</span>
        <span className="text-white font-medium">{value.toFixed(1)}{unit}</span>
      </div>
      <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
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
    { id: 'account', icon: User, title: 'Account', description: '账户信息与登录设置', iconColor: 'text-blue-400' },
    { id: 'notifications', icon: Bell, title: 'Notifications', description: '通知和提醒配置', iconColor: 'text-amber-400' },
    { id: 'security', icon: Shield, title: 'Security', description: '安全和隐私设置', iconColor: 'text-emerald-400' },
    { id: 'health', icon: Activity, title: 'System Health', description: '系统运行状态监控', iconColor: 'text-purple-400' },
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
          <div className="flex items-center gap-4 p-4 bg-gray-800/50 rounded-lg border border-gray-700">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-2xl font-bold text-white">
              {user.display_name?.[0]?.toUpperCase() || user.email[0].toUpperCase()}
            </div>
            <div className="flex-1">
              <h4 className="text-white font-medium">{user.display_name || '未设置昵称'}</h4>
              <p className="text-sm text-gray-400 flex items-center gap-1">
                <Mail className="w-3.5 h-3.5" />
                {user.email}
              </p>
              <p className="text-xs text-gray-500 mt-1">
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
            <button className="w-full flex items-center justify-between px-4 py-3 bg-gray-800/30 hover:bg-gray-800/50 rounded-lg text-sm text-gray-300 transition-colors">
              <span>修改昵称</span>
              <ChevronRight className="w-4 h-4 text-gray-600" />
            </button>
            <button className="w-full flex items-center justify-between px-4 py-3 bg-gray-800/30 hover:bg-gray-800/50 rounded-lg text-sm text-gray-300 transition-colors">
              <span>修改密码</span>
              <ChevronRight className="w-4 h-4 text-gray-600" />
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
          <p className="text-gray-400 mb-4">未登录</p>
          <button
            onClick={() => navigate('/login')}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm transition-colors"
          >
            前往登录
          </button>
        </div>
      )}
    </div>
  );

  const renderNotificationsSection = () => (
    <div className="space-y-3">
      <NotificationToggle label="分析完成通知" description="当 AI 分析完成时发送通知" defaultChecked />
      <NotificationToggle label="价格预警" description="股价达到设定阈值时提醒" defaultChecked />
      <NotificationToggle label="市场动态推送" description="重要市场新闻实时推送" />
      <NotificationToggle label="定时报告" description="每日/每周分析报告汇总" />
    </div>
  );

  const renderSecuritySection = () => (
    <div className="space-y-4">
      <div className="p-4 bg-gray-800/30 rounded-lg border border-gray-700">
        <div className="flex items-center gap-3 mb-3">
          <Key className="w-5 h-5 text-emerald-400" />
          <div>
            <h4 className="text-white font-medium">Passkey 管理</h4>
            <p className="text-xs text-gray-500">使用生物识别或安全密钥登录</p>
          </div>
        </div>
        <button className="w-full py-2 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 rounded-lg text-sm transition-colors border border-emerald-600/30">
          添加 Passkey
        </button>
      </div>

      <div className="p-4 bg-gray-800/30 rounded-lg border border-gray-700">
        <h4 className="text-white font-medium mb-2">第三方账号绑定</h4>
        <p className="text-xs text-gray-500 mb-3">关联第三方账号以快速登录</p>
        <div className="space-y-2">
          <OAuthBindingRow provider="Google" connected={false} />
          <OAuthBindingRow provider="GitHub" connected={false} />
        </div>
      </div>

      <button className="w-full flex items-center justify-between px-4 py-3 bg-gray-800/30 hover:bg-gray-800/50 rounded-lg text-sm text-gray-300 transition-colors">
        <span>登录历史</span>
        <ChevronRight className="w-4 h-4 text-gray-600" />
      </button>
    </div>
  );

  const renderHealthSection = () => (
    <div className="space-y-4">
      {/* 总体状态 */}
      <div className="flex items-center justify-between p-4 bg-gray-800/50 rounded-lg border border-gray-700">
        <div className="flex items-center gap-3">
          <Activity className="w-5 h-5 text-purple-400" />
          <div>
            <h4 className="text-white font-medium">系统状态</h4>
            <p className="text-xs text-gray-500">
              {uptimeData ? `运行时间: ${uptimeData.uptime_formatted}` : '加载中...'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isHealthLoading ? (
            <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
          ) : (
            <StatusBadge status={healthReport?.overall_status || 'unknown'} />
          )}
          <button
            onClick={() => refetchHealth()}
            className="p-1.5 hover:bg-gray-700 rounded transition-colors"
            title="刷新"
          >
            <RefreshCw className="w-4 h-4 text-gray-400" />
          </button>
        </div>
      </div>

      {/* 系统指标 */}
      {metrics && (
        <div className="p-4 bg-gray-800/30 rounded-lg border border-gray-700 space-y-3">
          <h4 className="text-sm font-medium text-white flex items-center gap-2">
            <Cpu className="w-4 h-4 text-blue-400" />
            系统资源
          </h4>
          <MetricBar label="CPU 使用率" value={metrics.cpu_percent} color="blue" />
          <MetricBar label="内存使用率" value={metrics.memory_percent} color="green" />
          <div className="text-xs text-gray-500">
            {metrics.memory_used_mb.toFixed(0)} MB / {metrics.memory_total_mb.toFixed(0)} MB
          </div>
          <MetricBar label="磁盘使用率" value={metrics.disk_percent} color="cyan" />
          <div className="text-xs text-gray-500">
            {metrics.disk_used_gb.toFixed(1)} GB / {metrics.disk_total_gb.toFixed(1)} GB
          </div>
        </div>
      )}

      {/* 组件状态 */}
      {healthReport?.components && healthReport.components.length > 0 && (
        <div className="p-4 bg-gray-800/30 rounded-lg border border-gray-700">
          <h4 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
            <HardDrive className="w-4 h-4 text-cyan-400" />
            组件状态
          </h4>
          <div className="space-y-2">
            {healthReport.components.map((comp: ComponentHealth) => (
              <div key={comp.name} className="flex items-center justify-between text-sm">
                <span className="text-gray-300">{comp.name}</span>
                <div className="flex items-center gap-2">
                  {comp.latency_ms !== undefined && (
                    <span className="text-xs text-gray-500">{comp.latency_ms}ms</span>
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
        <div className="p-4 bg-gray-800/30 rounded-lg border border-gray-700">
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
            {errorsData.errors.map((err: ErrorRecord, idx: number) => (
              <div key={idx} className="text-xs p-2 bg-red-900/20 rounded border border-red-900/30">
                <div className="flex justify-between text-red-300">
                  <span>{err.component}</span>
                  <span>{new Date(err.timestamp).toLocaleTimeString()}</span>
                </div>
                <p className="text-gray-400 mt-1 truncate">{err.message}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  const renderDataSection = () => (
    <div className="space-y-3">
      <button className="w-full flex items-center justify-between px-4 py-3 bg-gray-800/30 hover:bg-gray-800/50 rounded-lg text-sm text-gray-300 transition-colors">
        <span className="flex items-center gap-2">
          <Trash2 className="w-4 h-4 text-gray-500" />
          清除本地缓存
        </span>
        <ChevronRight className="w-4 h-4 text-gray-600" />
      </button>
      <button className="w-full flex items-center justify-between px-4 py-3 bg-gray-800/30 hover:bg-gray-800/50 rounded-lg text-sm text-gray-300 transition-colors">
        <span className="flex items-center gap-2">
          <Database className="w-4 h-4 text-gray-500" />
          导出分析数据
        </span>
        <ChevronRight className="w-4 h-4 text-gray-600" />
      </button>
      <button className="w-full flex items-center justify-between px-4 py-3 bg-gray-800/30 hover:bg-gray-800/50 rounded-lg text-sm text-gray-300 transition-colors">
        <span className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-gray-500" />
          查看分析历史
        </span>
        <ChevronRight className="w-4 h-4 text-gray-600" />
      </button>
    </div>
  );

  const renderSectionContent = (id: string) => {
    switch (id) {
      case 'account': return renderAccountSection();
      case 'notifications': return renderNotificationsSection();
      case 'security': return renderSecuritySection();
      case 'health': return renderHealthSection();
      case 'data': return renderDataSection();
      default: return null;
    }
  };

  return (
    <PageLayout
      title="Settings"
      subtitle="应用程序设置"
      icon={Settings}
      iconColor="text-gray-400"
      iconBgColor="bg-gray-500/10"
      variant="narrow"
    >
      <div className="space-y-3">
        {sections.map((section) => (
          <div
            key={section.id}
            className="bg-gray-800/50 rounded-xl border border-gray-700 overflow-hidden"
          >
            {/* Section Header */}
            <button
              onClick={() => toggleSection(section.id)}
              className="w-full p-4 flex items-center justify-between hover:bg-gray-800/30 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 bg-gray-700 rounded-lg">
                  <section.icon className={`w-5 h-5 ${section.iconColor || 'text-gray-400'}`} />
                </div>
                <div className="text-left">
                  <h3 className="font-medium text-white">{section.title}</h3>
                  <p className="text-xs text-gray-500">{section.description}</p>
                </div>
              </div>
              {expandedSection === section.id ? (
                <ChevronDown className="w-5 h-5 text-gray-500" />
              ) : (
                <ChevronRight className="w-5 h-5 text-gray-500" />
              )}
            </button>

            {/* Section Content */}
            {expandedSection === section.id && (
              <div className="px-4 pb-4 border-t border-gray-700/50 pt-4">
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

const NotificationToggle: React.FC<{
  label: string;
  description: string;
  defaultChecked?: boolean;
}> = ({ label, description, defaultChecked = false }) => {
  const [checked, setChecked] = useState(defaultChecked);

  return (
    <div className="flex items-center justify-between p-3 bg-gray-800/30 rounded-lg">
      <div>
        <p className="text-sm text-gray-200">{label}</p>
        <p className="text-xs text-gray-500">{description}</p>
      </div>
      <button
        onClick={() => setChecked(!checked)}
        className={`relative w-11 h-6 rounded-full transition-colors ${
          checked ? 'bg-blue-600' : 'bg-gray-700'
        }`}
      >
        <span
          className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
            checked ? 'translate-x-6' : 'translate-x-1'
          }`}
        />
      </button>
    </div>
  );
};

const OAuthBindingRow: React.FC<{ provider: string; connected: boolean }> = ({ provider, connected }) => (
  <div className="flex items-center justify-between py-2">
    <span className="text-sm text-gray-300">{provider}</span>
    {connected ? (
      <button className="text-xs text-red-400 hover:text-red-300 px-2 py-1 rounded hover:bg-red-900/20 transition-colors">
        解绑
      </button>
    ) : (
      <button className="text-xs text-blue-400 hover:text-blue-300 px-2 py-1 rounded hover:bg-blue-900/20 transition-colors">
        绑定
      </button>
    )}
  </div>
);

export default SettingsPage;
