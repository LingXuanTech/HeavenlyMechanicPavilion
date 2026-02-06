import React, { useState, useCallback } from 'react';

/**
 * 时间周期配置
 */
export type TimePeriod = '1D' | '1W' | '1M' | '3M' | '6M' | '1Y' | '3Y' | 'ALL';

/**
 * 指标配置
 */
export type IndicatorType = 'ma5' | 'ma10' | 'ma20' | 'ma60' | 'ma120' | 'bollinger';

interface ChartToolbarProps {
  /** 当前选中的时间周期 */
  activePeriod: TimePeriod;
  /** 时间周期变更回调 */
  onPeriodChange: (period: TimePeriod) => void;
  /** 当前选中的指标列表 */
  activeIndicators: IndicatorType[];
  /** 指标变更回调 */
  onIndicatorsChange: (indicators: IndicatorType[]) => void;
  /** 是否显示成交量 */
  showVolume: boolean;
  /** 成交量切换回调 */
  onVolumeToggle: () => void;
  /** 是否全屏 */
  isFullscreen: boolean;
  /** 全屏切换回调 */
  onFullscreenToggle: () => void;
  /** 自定义类名 */
  className?: string;
}

/**
 * 时间周期选项
 */
const PERIOD_OPTIONS: { value: TimePeriod; label: string }[] = [
  { value: '1D', label: '日' },
  { value: '1W', label: '周' },
  { value: '1M', label: '月' },
  { value: '3M', label: '3月' },
  { value: '6M', label: '半年' },
  { value: '1Y', label: '1年' },
  { value: '3Y', label: '3年' },
  { value: 'ALL', label: '全部' },
];

/**
 * 指标选项
 */
const INDICATOR_OPTIONS: { value: IndicatorType; label: string; color: string }[] = [
  { value: 'ma5', label: 'MA5', color: '#f7931a' },
  { value: 'ma10', label: 'MA10', color: '#627eea' },
  { value: 'ma20', label: 'MA20', color: '#00d4aa' },
  { value: 'ma60', label: 'MA60', color: '#ff6b6b' },
  { value: 'ma120', label: 'MA120', color: '#a855f7' },
  { value: 'bollinger', label: 'BOLL', color: '#9c27b0' },
];

/**
 * 图表工具栏组件
 *
 * 提供时间周期切换、技术指标选择、成交量切换、全屏等功能。
 */
export const ChartToolbar: React.FC<ChartToolbarProps> = ({
  activePeriod,
  onPeriodChange,
  activeIndicators,
  onIndicatorsChange,
  showVolume,
  onVolumeToggle,
  isFullscreen,
  onFullscreenToggle,
  className = '',
}) => {
  const [showIndicatorPanel, setShowIndicatorPanel] = useState(false);

  const toggleIndicator = useCallback(
    (indicator: IndicatorType) => {
      const newIndicators = activeIndicators.includes(indicator)
        ? activeIndicators.filter((i) => i !== indicator)
        : [...activeIndicators, indicator];
      onIndicatorsChange(newIndicators);
    },
    [activeIndicators, onIndicatorsChange]
  );

  return (
    <div className={`flex items-center justify-between gap-2 px-3 py-1.5 bg-surface-raised/80 border-b border-border ${className}`}>
      {/* 左侧：时间周期 */}
      <div className="flex items-center gap-0.5">
        {PERIOD_OPTIONS.map((option) => (
          <button
            key={option.value}
            onClick={() => onPeriodChange(option.value)}
            className={`px-2 py-0.5 text-xs rounded transition-colors ${
              activePeriod === option.value
                ? 'bg-accent text-white'
                : 'text-stone-400 hover:text-white hover:bg-surface-muted'
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>

      {/* 中间：技术指标 */}
      <div className="flex items-center gap-1">
        {/* 快捷指标按钮 */}
        {INDICATOR_OPTIONS.slice(0, 3).map((option) => (
          <button
            key={option.value}
            onClick={() => toggleIndicator(option.value)}
            className={`px-1.5 py-0.5 text-[10px] font-mono rounded transition-colors ${
              activeIndicators.includes(option.value)
                ? 'text-white'
                : 'text-stone-500 hover:text-stone-300'
            }`}
            style={
              activeIndicators.includes(option.value)
                ? { backgroundColor: `${option.color}40`, color: option.color }
                : undefined
            }
          >
            {option.label}
          </button>
        ))}

        {/* 更多指标面板 */}
        <div className="relative">
          <button
            onClick={() => setShowIndicatorPanel(!showIndicatorPanel)}
            className={`px-1.5 py-0.5 text-[10px] rounded transition-colors ${
              showIndicatorPanel
                ? 'bg-surface-muted text-white'
                : 'text-stone-500 hover:text-stone-300'
            }`}
          >
            指标 ▾
          </button>

          {showIndicatorPanel && (
            <div className="absolute top-full right-0 mt-1 bg-surface-overlay border border-border-strong rounded-lg shadow-xl z-50 p-2 min-w-[160px]">
              <div className="text-[10px] text-stone-400 mb-1 px-1">技术指标</div>
              {INDICATOR_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => toggleIndicator(option.value)}
                  className="w-full flex items-center gap-2 px-2 py-1 text-xs rounded hover:bg-surface-muted transition-colors"
                >
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: option.color }}
                  />
                  <span className={activeIndicators.includes(option.value) ? 'text-white' : 'text-stone-400'}>
                    {option.label}
                  </span>
                  {activeIndicators.includes(option.value) && (
                    <span className="ml-auto text-green-400">✓</span>
                  )}
                </button>
              ))}

              <div className="border-t border-border-strong mt-1 pt-1">
                <button
                  onClick={onVolumeToggle}
                  className="w-full flex items-center gap-2 px-2 py-1 text-xs rounded hover:bg-surface-muted transition-colors"
                >
                  <span className="w-2 h-2 rounded-full bg-accent" />
                  <span className={showVolume ? 'text-white' : 'text-stone-400'}>成交量</span>
                  {showVolume && <span className="ml-auto text-green-400">✓</span>}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 右侧：全屏等功能 */}
      <div className="flex items-center gap-1">
        <button
          onClick={onFullscreenToggle}
          className="px-1.5 py-0.5 text-[10px] text-stone-500 hover:text-white rounded hover:bg-surface-muted transition-colors"
          title={isFullscreen ? '退出全屏' : '全屏'}
        >
          {isFullscreen ? '⤓' : '⤢'}
        </button>
      </div>
    </div>
  );
};

ChartToolbar.displayName = 'ChartToolbar';

export default ChartToolbar;
