/**
 * 统一页面布局组件
 *
 * 提供一致的页面结构，支持多种布局变体：
 * - dashboard: 全宽监控布局，可带侧边栏
 * - wide: 宽幅数据仪表板 (max-w-7xl)
 * - standard: 标准内容布局 (max-w-5xl)
 * - narrow: 窄幅配置/设置布局 (max-w-3xl)
 * - split: 主从面板布局（左侧列表 + 右侧详情）
 */
import React, { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, LucideIcon, Loader2 } from 'lucide-react';

// === 类型定义 ===

export type PageLayoutVariant = 'dashboard' | 'wide' | 'standard' | 'narrow' | 'split';

export interface PageHeaderAction {
  label: string;
  icon?: LucideIcon;
  onClick: () => void;
  loading?: boolean;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'ghost';
}

export interface PageLayoutProps {
  /** 页面标题 */
  title: string;
  /** 副标题/描述 */
  subtitle?: string | ReactNode;
  /** 标题图标 */
  icon?: LucideIcon;
  /** 图标颜色 */
  iconColor?: string;
  /** 图标背景色 */
  iconBgColor?: string;
  /** 布局变体 */
  variant?: PageLayoutVariant;
  /** 是否显示返回按钮 */
  showBack?: boolean;
  /** 自定义返回路径 */
  backPath?: string;
  /** 页面内容 */
  children: ReactNode;
  /** Header 右侧操作按钮 */
  actions?: PageHeaderAction[];
  /** Header 右侧自定义内容 */
  headerRight?: ReactNode;
  /** Split 布局的左侧面板宽度 */
  splitLeftWidth?: string;
  /** Split 布局的左侧内容 */
  splitLeft?: ReactNode;
  /** 内容区域的自定义类名 */
  contentClassName?: string;
  /** 是否有内边距 */
  noPadding?: boolean;
}

// === 宽度配置 ===

const VARIANT_MAX_WIDTH: Record<PageLayoutVariant, string> = {
  dashboard: '', // 全宽
  wide: 'max-w-7xl',
  standard: 'max-w-5xl',
  narrow: 'max-w-3xl',
  split: '', // 全宽 split
};

// === 按钮变体样式 ===

const ACTION_BUTTON_STYLES = {
  primary: 'bg-blue-600 hover:bg-blue-500 text-white',
  secondary: 'bg-gray-700 hover:bg-gray-600 text-white',
  ghost: 'text-gray-400 hover:text-white hover:bg-gray-800',
};

// === 主组件 ===

const PageLayout: React.FC<PageLayoutProps> = ({
  title,
  subtitle,
  icon: Icon,
  iconColor = 'text-blue-400',
  iconBgColor = 'bg-blue-500/10',
  variant = 'standard',
  showBack = true,
  backPath = '/',
  children,
  actions = [],
  headerRight,
  splitLeftWidth = 'w-80',
  splitLeft,
  contentClassName = '',
  noPadding = false,
}) => {
  const navigate = useNavigate();

  // 渲染操作按钮
  const renderActions = () => (
    <div className="flex items-center gap-2">
      {actions.map((action, index) => {
        const ActionIcon = action.icon;
        const buttonStyle = ACTION_BUTTON_STYLES[action.variant || 'secondary'];

        return (
          <button
            key={index}
            onClick={action.onClick}
            disabled={action.disabled || action.loading}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 ${buttonStyle}`}
          >
            {action.loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : ActionIcon ? (
              <ActionIcon className="w-4 h-4" />
            ) : null}
            {action.label}
          </button>
        );
      })}
      {headerRight}
    </div>
  );

  // 渲染 Header
  const renderHeader = () => (
    <header className="shrink-0 px-6 py-4 border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          {showBack && (
            <button
              onClick={() => navigate(backPath)}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400 hover:text-white"
              aria-label="返回"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
          )}
          <div className="flex items-center gap-3">
            {Icon && (
              <div className={`p-2 rounded-lg ${iconBgColor}`}>
                <Icon className={`w-5 h-5 ${iconColor}`} />
              </div>
            )}
            <div>
              <h1 className="text-xl font-bold text-white">{title}</h1>
              {subtitle && (
                <div className="text-xs text-gray-500">
                  {typeof subtitle === 'string' ? subtitle : subtitle}
                </div>
              )}
            </div>
          </div>
        </div>

        {(actions.length > 0 || headerRight) && renderActions()}
      </div>
    </header>
  );

  // Split 布局
  if (variant === 'split') {
    return (
      <div className="flex flex-col h-full">
        {renderHeader()}
        <div className="flex-1 flex overflow-hidden">
          {/* 左侧面板 */}
          <div className={`${splitLeftWidth} border-r border-gray-800 flex flex-col shrink-0 overflow-hidden`}>
            {splitLeft}
          </div>
          {/* 右侧内容 */}
          <div className={`flex-1 flex flex-col overflow-hidden ${contentClassName}`}>
            {children}
          </div>
        </div>
      </div>
    );
  }

  // 其他布局
  const maxWidth = VARIANT_MAX_WIDTH[variant];
  const padding = noPadding ? '' : 'p-6';

  return (
    <div className="flex flex-col h-full">
      {renderHeader()}
      <main className={`flex-1 overflow-y-auto ${padding} custom-scrollbar`}>
        <div className={`${maxWidth} mx-auto ${contentClassName}`}>
          {children}
        </div>
      </main>
    </div>
  );
};

// === 辅助组件：页面区块 ===

interface PageSectionProps {
  title?: string;
  subtitle?: string;
  icon?: LucideIcon;
  iconColor?: string;
  children: ReactNode;
  className?: string;
  action?: ReactNode;
}

export const PageSection: React.FC<PageSectionProps> = ({
  title,
  subtitle,
  icon: Icon,
  iconColor = 'text-gray-400',
  children,
  className = '',
  action,
}) => (
  <section className={`bg-gray-800/30 rounded-xl border border-gray-700 overflow-hidden ${className}`}>
    {(title || action) && (
      <div className="px-5 py-4 border-b border-gray-700/50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {Icon && <Icon className={`w-5 h-5 ${iconColor}`} />}
          <div>
            {title && <h3 className="font-medium text-white">{title}</h3>}
            {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
          </div>
        </div>
        {action}
      </div>
    )}
    <div className="p-5">{children}</div>
  </section>
);

// === 辅助组件：统计卡片 ===

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  iconColor?: string;
  valueColor?: string;
  trend?: 'up' | 'down' | 'neutral';
  subtitle?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  icon: Icon,
  iconColor = 'text-gray-400',
  valueColor = 'text-white',
  subtitle,
}) => (
  <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
    <div className="flex items-center justify-between mb-2">
      <span className="text-sm text-gray-400">{label}</span>
      {Icon && <Icon className={`w-4 h-4 ${iconColor}`} />}
    </div>
    <div className={`text-2xl font-bold ${valueColor}`}>{value}</div>
    {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
  </div>
);

// === 辅助组件：空状态 ===

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  title,
  description,
  action,
}) => (
  <div className="flex flex-col items-center justify-center py-16 text-gray-500">
    {Icon && <Icon className="w-12 h-12 mb-4 opacity-50" />}
    <p className="text-lg font-medium">{title}</p>
    {description && <p className="text-sm mt-1 text-gray-600">{description}</p>}
    {action && <div className="mt-4">{action}</div>}
  </div>
);

// === 辅助组件：加载状态 ===

interface LoadingStateProps {
  message?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({ message = '加载中...' }) => (
  <div className="flex flex-col items-center justify-center py-16 text-gray-500">
    <Loader2 className="w-8 h-8 animate-spin mb-4" />
    <p className="text-sm">{message}</p>
  </div>
);

export default PageLayout;
