/**
 * 分析进度可视化组件
 *
 * 展示分析任务的阶段性进度：
 * 1. 初始化 (starting)
 * 2. 分析师团队 (stage_analyst)
 * 3. 多空辩论 (stage_debate)
 * 4. 风险评估 (stage_risk)
 * 5. 最终合成 (stage_final)
 */
import React, { memo, useMemo } from 'react';
import {
  PlayCircle,
  Users,
  Scale,
  Shield,
  CheckCircle2,
  Loader2,
  AlertCircle,
} from 'lucide-react';

export type AnalysisStage =
  | 'starting'
  | 'stage_analyst'
  | 'stage_debate'
  | 'stage_risk'
  | 'stage_final'
  | 'error'
  | 'cancelled';

interface StageConfig {
  id: AnalysisStage;
  label: string;
  shortLabel: string;
  icon: React.ElementType;
  color: string;
  description: string;
}

const STAGES: StageConfig[] = [
  {
    id: 'starting',
    label: '初始化',
    shortLabel: '初始',
    icon: PlayCircle,
    color: 'blue',
    description: '准备分析任务',
  },
  {
    id: 'stage_analyst',
    label: '分析师团队',
    shortLabel: '分析',
    icon: Users,
    color: 'cyan',
    description: 'Market / News / Fundamentals / Macro',
  },
  {
    id: 'stage_debate',
    label: '多空辩论',
    shortLabel: '辩论',
    icon: Scale,
    color: 'purple',
    description: 'Bull vs Bear 对抗性研究',
  },
  {
    id: 'stage_risk',
    label: '风险评估',
    shortLabel: '风控',
    icon: Shield,
    color: 'orange',
    description: '三方风险辩论',
  },
  {
    id: 'stage_final',
    label: '完成',
    shortLabel: '完成',
    icon: CheckCircle2,
    color: 'green',
    description: '合成最终报告',
  },
];

// 获取阶段索引（用于计算进度）
function getStageIndex(stage: string): number {
  // 处理带有额外信息的阶段名（如 "starting (快速扫描)"）
  const normalizedStage = stage.split(' ')[0] as AnalysisStage;
  const index = STAGES.findIndex((s) => s.id === normalizedStage);
  return index >= 0 ? index : 0;
}

// 根据颜色名获取 Tailwind 类
function getColorClasses(color: string, variant: 'bg' | 'text' | 'border') {
  const colorMap: Record<string, Record<string, string>> = {
    blue: { bg: 'bg-blue-500', text: 'text-blue-400', border: 'border-blue-500' },
    cyan: { bg: 'bg-cyan-500', text: 'text-cyan-400', border: 'border-cyan-500' },
    purple: { bg: 'bg-purple-500', text: 'text-purple-400', border: 'border-purple-500' },
    orange: { bg: 'bg-orange-500', text: 'text-orange-400', border: 'border-orange-500' },
    green: { bg: 'bg-green-500', text: 'text-green-400', border: 'border-green-500' },
  };
  return colorMap[color]?.[variant] || 'bg-gray-500';
}

interface AnalysisProgressBarProps {
  /** 当前阶段 */
  currentStage: string;
  /** 是否显示详细标签（默认只在较大视图显示） */
  showLabels?: boolean;
  /** 是否是紧凑模式（用于卡片内） */
  compact?: boolean;
  /** 是否有错误 */
  hasError?: boolean;
  /** 错误信息 */
  errorMessage?: string;
}

const AnalysisProgressBarComponent: React.FC<AnalysisProgressBarProps> = ({
  currentStage,
  showLabels = false,
  compact = false,
  hasError = false,
  errorMessage,
}) => {
  const currentIndex = useMemo(() => getStageIndex(currentStage), [currentStage]);

  // 计算进度百分比
  const progressPercent = useMemo(() => {
    if (hasError) return 0;
    if (currentStage === 'stage_final') return 100;
    // 每个阶段占 25%
    return Math.min(100, (currentIndex / (STAGES.length - 1)) * 100);
  }, [currentIndex, currentStage, hasError]);

  if (hasError) {
    return (
      <div className={`flex items-center gap-2 ${compact ? 'py-1' : 'py-2'}`}>
        <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
        <span className="text-xs text-red-400 truncate">{errorMessage || '分析失败'}</span>
      </div>
    );
  }

  // 紧凑模式：只显示进度条和当前阶段
  if (compact) {
    const currentConfig = STAGES[currentIndex] || STAGES[0];
    const Icon = currentConfig.icon;
    const isCompleted = currentStage === 'stage_final';

    return (
      <div className="space-y-1.5">
        {/* 进度条 */}
        <div className="relative h-1 bg-gray-800 rounded-full overflow-hidden">
          <div
            className={`absolute inset-y-0 left-0 transition-all duration-500 ease-out rounded-full ${
              isCompleted ? 'bg-green-500' : getColorClasses(currentConfig.color, 'bg')
            }`}
            style={{ width: `${progressPercent}%` }}
          />
          {/* 动画脉冲（进行中） */}
          {!isCompleted && (
            <div
              className={`absolute inset-y-0 w-8 animate-pulse ${getColorClasses(
                currentConfig.color,
                'bg'
              )} opacity-50 blur-sm`}
              style={{ left: `calc(${progressPercent}% - 1rem)` }}
            />
          )}
        </div>

        {/* 当前阶段指示 */}
        <div className="flex items-center justify-between text-[10px]">
          <div className="flex items-center gap-1">
            {isCompleted ? (
              <CheckCircle2 className="w-3 h-3 text-green-400" />
            ) : (
              <Icon className={`w-3 h-3 ${getColorClasses(currentConfig.color, 'text')} animate-pulse`} />
            )}
            <span className={isCompleted ? 'text-green-400' : 'text-gray-400'}>
              {currentConfig.shortLabel}
            </span>
          </div>
          <span className="text-gray-500 tabular-nums">{Math.round(progressPercent)}%</span>
        </div>
      </div>
    );
  }

  // 完整模式：显示所有阶段
  return (
    <div className="space-y-3">
      {/* 阶段指示器 */}
      <div className="flex items-center justify-between relative">
        {/* 连接线（背景） */}
        <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-gray-800 -translate-y-1/2 z-0" />

        {/* 进度线（前景） */}
        <div
          className="absolute top-1/2 left-0 h-0.5 bg-gradient-to-r from-blue-500 via-purple-500 to-green-500 -translate-y-1/2 z-0 transition-all duration-500"
          style={{ width: `${progressPercent}%` }}
        />

        {/* 阶段节点 */}
        {STAGES.map((stage, index) => {
          const Icon = stage.icon;
          const isActive = index === currentIndex;
          const isCompleted = index < currentIndex || currentStage === 'stage_final';
          const isPending = index > currentIndex;

          return (
            <div
              key={stage.id}
              className="relative z-10 flex flex-col items-center"
              title={`${stage.label}: ${stage.description}`}
            >
              {/* 节点圆圈 */}
              <div
                className={`
                  w-8 h-8 rounded-full flex items-center justify-center
                  transition-all duration-300 border-2
                  ${
                    isCompleted
                      ? 'bg-green-500/20 border-green-500'
                      : isActive
                      ? `${getColorClasses(stage.color, 'bg')}/20 ${getColorClasses(
                          stage.color,
                          'border'
                        )} ring-2 ring-offset-2 ring-offset-gray-900 ${getColorClasses(
                          stage.color,
                          'border'
                        ).replace('border-', 'ring-')}/30`
                      : 'bg-gray-900 border-gray-700'
                  }
                `}
              >
                {isActive && !isCompleted ? (
                  <Loader2
                    className={`w-4 h-4 animate-spin ${getColorClasses(stage.color, 'text')}`}
                  />
                ) : isCompleted ? (
                  <CheckCircle2 className="w-4 h-4 text-green-400" />
                ) : (
                  <Icon className={`w-4 h-4 ${isPending ? 'text-gray-600' : getColorClasses(stage.color, 'text')}`} />
                )}
              </div>

              {/* 标签 */}
              {showLabels && (
                <span
                  className={`
                    text-[10px] mt-1.5 whitespace-nowrap
                    ${
                      isCompleted
                        ? 'text-green-400'
                        : isActive
                        ? getColorClasses(stage.color, 'text')
                        : 'text-gray-600'
                    }
                  `}
                >
                  {stage.shortLabel}
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* 当前阶段描述 */}
      <div className="text-center">
        <p className="text-xs text-gray-400">
          {STAGES[currentIndex]?.description || '准备中...'}
        </p>
      </div>
    </div>
  );
};

export const AnalysisProgressBar = memo(AnalysisProgressBarComponent);
export default AnalysisProgressBar;
