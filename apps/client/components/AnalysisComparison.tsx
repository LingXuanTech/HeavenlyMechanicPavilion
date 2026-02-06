/**
 * 历史分析对比组件
 *
 * 支持选择 2-3 个历史分析进行并排对比，
 * 可视化关键指标差异（信号、置信度、风险、辩论等）
 */
import * as React from 'react';
import { useState, memo } from 'react';
import {
  GitCompareArrows,
  ChevronDown,
  ChevronUp,
  Check,
  X,
  TrendingUp,
  TrendingDown,
  Minus,
  Clock,
  Loader2,
} from 'lucide-react';
import { useAnalysisComparison } from '../hooks/useAnalysisHistory';
import type * as T from '../src/types/schema';

// 使用从 schema 导出的统一类型
type AnalysisDetail = T.AnalysisDetailResponse;

interface AnalysisComparisonProps {
  symbol: string;
}

/** 信号数值映射（用于比较） */
const SIGNAL_VALUE: Record<string, number> = {
  'Strong Buy': 5,
  'Buy': 4,
  'Hold': 3,
  'Sell': 2,
  'Strong Sell': 1,
};

/** 信号颜色 */
const SIGNAL_COLOR: Record<string, string> = {
  'Strong Buy': 'text-green-400 bg-green-500/10',
  'Buy': 'text-green-300 bg-green-500/5',
  'Hold': 'text-yellow-400 bg-yellow-500/10',
  'Sell': 'text-red-300 bg-red-500/5',
  'Strong Sell': 'text-red-400 bg-red-500/10',
};

/** 指标变化箭头 */
const ChangeIndicator: React.FC<{ current: number; previous: number; suffix?: string }> = ({
  current,
  previous,
  suffix = '',
}) => {
  const diff = current - previous;
  if (Math.abs(diff) < 0.01) {
    return <Minus className="w-3 h-3 text-stone-500 inline" />;
  }
  return diff > 0 ? (
    <span className="text-green-400 text-[10px] font-mono">
      <TrendingUp className="w-3 h-3 inline" /> +{diff.toFixed(1)}{suffix}
    </span>
  ) : (
    <span className="text-red-400 text-[10px] font-mono">
      <TrendingDown className="w-3 h-3 inline" /> {diff.toFixed(1)}{suffix}
    </span>
  );
};

/** 单列分析摘要 */
const AnalysisColumn: React.FC<{
  detail: AnalysisDetail;
  prevDetail?: AnalysisDetail;
  index: number;
}> = ({ detail, prevDetail }) => {
  const report = detail.full_report;
  const signal = report?.signal as string;
  const signalColorClass = SIGNAL_COLOR[signal] || 'text-stone-400';
  const riskScore = report?.risk_assessment?.score ?? 0;
  const confidence = report?.confidence ?? 0;

  return (
    <div className="flex-1 min-w-[180px] space-y-3">
      {/* 日期头 */}
      <div className="text-center border-b border-border pb-2">
        <div className="text-xs text-stone-500 flex items-center justify-center gap-1">
          <Clock className="w-3 h-3" />
          {detail.date}
        </div>
        <div className="text-[10px] text-stone-600 mt-0.5">
          {new Date(detail.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>

      {/* 信号 */}
      <div className={`text-center py-2 rounded-lg ${signalColorClass}`}>
        <div className="text-sm font-bold">{signal || 'N/A'}</div>
        {prevDetail && (
          <div className="mt-1">
            <ChangeIndicator
              current={SIGNAL_VALUE[signal] ?? 3}
              previous={SIGNAL_VALUE[prevDetail.full_report?.signal as string] ?? 3}
            />
          </div>
        )}
      </div>

      {/* 置信度 */}
      <div className="space-y-1">
        <div className="flex justify-between text-[10px] text-stone-500">
          <span>置信度</span>
          <span className="font-mono text-white">{confidence}%</span>
        </div>
        <div className="h-1.5 bg-surface-overlay rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              confidence >= 70 ? 'bg-green-500' : confidence >= 50 ? 'bg-yellow-500' : 'bg-red-500'
            }`}
            style={{ width: `${confidence}%` }}
          />
        </div>
        {prevDetail && (
          <ChangeIndicator current={confidence} previous={prevDetail.full_report?.confidence ?? 0} suffix="%" />
        )}
      </div>

      {/* 风险评分 */}
      <div className="space-y-1">
        <div className="flex justify-between text-[10px] text-stone-500">
          <span>风险评分</span>
          <span
            className={`font-mono ${
              riskScore >= 7 ? 'text-red-400' : riskScore >= 4 ? 'text-yellow-400' : 'text-green-400'
            }`}
          >
            {riskScore}/10
          </span>
        </div>
        <div className="h-1.5 bg-surface-overlay rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              riskScore >= 7 ? 'bg-red-500' : riskScore >= 4 ? 'bg-yellow-500' : 'bg-green-500'
            }`}
            style={{ width: `${riskScore * 10}%` }}
          />
        </div>
        {prevDetail && (
          <ChangeIndicator current={riskScore} previous={prevDetail.full_report?.risk_assessment?.score ?? 0} />
        )}
      </div>

      {/* 辩论赢家 */}
      {report?.debate && (
        <div className="text-center">
          <div className="text-[10px] text-stone-500 mb-1">辩论赢家</div>
          <span
            className={`text-xs font-bold px-2 py-0.5 rounded-full ${
              report.debate.winner === 'Bull'
                ? 'bg-green-500/20 text-green-400'
                : report.debate.winner === 'Bear'
                ? 'bg-red-500/20 text-red-400'
                : 'bg-stone-500/20 text-stone-400'
            }`}
          >
            {report.debate.winner}
          </span>
        </div>
      )}

      {/* 价格水平 */}
      {report?.price_levels && (
        <div className="text-[10px] space-y-0.5">
          <div className="flex justify-between">
            <span className="text-stone-500">支撑</span>
            <span className="text-green-400 font-mono">{report.price_levels.support}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-stone-500">阻力</span>
            <span className="text-red-400 font-mono">{report.price_levels.resistance}</span>
          </div>
        </div>
      )}

      {/* 耗时 */}
      <div className="text-center text-[10px] text-stone-600">
        耗时 {detail.elapsed_seconds?.toFixed(1) ?? '?'}s
      </div>
    </div>
  );
};

const AnalysisComparisonComponent: React.FC<AnalysisComparisonProps> = ({ symbol }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const {
    historyQuery,
    selectedIds,
    toggleSelected,
    clearSelection,
    loadedDetails,
    isLoading,
    canCompare,
  } = useAnalysisComparison(symbol);

  const historyItems = historyQuery.data?.items || [];

  if (!historyItems.length) {
    return null; // 无历史记录不显示
  }

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      {/* 折叠头 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-surface-raised/50 hover:bg-surface-raised transition-colors"
      >
        <div className="flex items-center gap-2 text-sm">
          <GitCompareArrows className="w-4 h-4 text-accent" />
          <span className="text-stone-300 font-medium">历史分析对比</span>
          <span className="text-[10px] text-stone-600 bg-surface-overlay px-1.5 py-0.5 rounded">
            {historyItems.length} 条记录
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-stone-500" />
        ) : (
          <ChevronDown className="w-4 h-4 text-stone-500" />
        )}
      </button>

      {isExpanded && (
        <div className="p-4 space-y-4">
          {/* 历史列表（选择） */}
          <div className="space-y-1">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-stone-500">选择要对比的分析（最多 3 个）</span>
              {selectedIds.length > 0 && (
                <button
                  onClick={clearSelection}
                  className="text-[10px] text-stone-500 hover:text-stone-300 flex items-center gap-0.5"
                >
                  <X className="w-3 h-3" /> 清除
                </button>
              )}
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
              {historyItems.map((item) => {
                const isSelected = selectedIds.includes(item.id);
                return (
                  <button
                    key={item.id}
                    onClick={() => toggleSelected(item.id)}
                    className={`
                      text-left px-3 py-2 rounded-lg border transition-all text-xs
                      ${
                        isSelected
                          ? 'border-accent bg-accent/10'
                          : 'border-border bg-surface-raised/50 hover:border-border-strong'
                      }
                    `}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-stone-400">{item.date}</span>
                      {isSelected && <Check className="w-3 h-3 text-accent" />}
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <span
                        className={
                          item.signal.includes('Buy')
                            ? 'text-green-400'
                            : item.signal.includes('Sell')
                            ? 'text-red-400'
                            : 'text-yellow-400'
                        }
                      >
                        {item.signal}
                      </span>
                      <span className="text-stone-600 font-mono">{item.confidence}%</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 对比视图 */}
          {isLoading && (
            <div className="flex items-center justify-center py-8 text-stone-500 text-sm">
              <Loader2 className="w-4 h-4 animate-spin mr-2" /> 加载分析报告...
            </div>
          )}

          {canCompare && loadedDetails.length >= 2 && !isLoading && (
            <div className="border-t border-border pt-4">
              <h4 className="text-xs text-stone-500 uppercase tracking-wider mb-3">对比详情</h4>
              <div className="flex gap-4 overflow-x-auto pb-2">
                {loadedDetails.map((detail, index) => (
                  <AnalysisColumn
                    key={detail.id}
                    detail={detail}
                    prevDetail={index > 0 ? loadedDetails[index - 1] : undefined}
                    index={index}
                  />
                ))}
              </div>
            </div>
          )}

          {selectedIds.length === 1 && !isLoading && (
            <div className="text-center py-4 text-xs text-stone-600">
              再选择至少 1 个分析以开始对比
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export const AnalysisComparison = memo(AnalysisComparisonComponent);
export default AnalysisComparison;
