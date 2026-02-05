import React from 'react';
import {
  X,
  TrendingUp,
  TrendingDown,
  Minus,
  Globe,
  AlertTriangle,
  Lightbulb,
  RefreshCw,
  Activity,
} from 'lucide-react';
import { useMacroImpactAnalysis, useRefreshMacro } from '../hooks/useMacro';
import type * as T from '../src/types/schema';

interface MacroDashboardProps {
  onClose: () => void;
}

// 趋势图标组件
const TrendIcon: React.FC<{ trend: string | undefined; className?: string }> = ({ trend, className = "w-4 h-4" }) => {
  if (trend === 'up') return <TrendingUp className={`${className} text-green-400`} />;
  if (trend === 'down') return <TrendingDown className={`${className} text-red-400`} />;
  return <Minus className={`${className} text-gray-400`} />;
};

// 单个指标卡片
const IndicatorCard: React.FC<{ indicator: T.MacroIndicator; icon: React.ReactNode }> = ({ indicator, icon }) => {
  const changeColor = indicator.change && indicator.change > 0 ? 'text-green-400' :
                      indicator.change && indicator.change < 0 ? 'text-red-400' : 'text-gray-400';

  return (
    <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700 hover:border-gray-600 transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-gray-400">{icon}</span>
          <span className="text-sm text-gray-400">{indicator.name}</span>
        </div>
        <TrendIcon trend={indicator.trend} />
      </div>

      <div className="flex items-end gap-2">
        <span className="text-2xl font-bold text-white">
          {indicator.value}{indicator.unit}
        </span>
        {indicator.change !== null && indicator.change !== undefined && (
          <span className={`text-sm ${changeColor}`}>
            {indicator.change > 0 ? '+' : ''}{indicator.change.toFixed(2)}
            {indicator.change_percent !== null && indicator.change_percent !== undefined && (
              <span className="ml-1">({indicator.change_percent.toFixed(1)}%)</span>
            )}
          </span>
        )}
      </div>

      <div className="mt-2 text-xs text-gray-500">
        {indicator.date} · {indicator.source}
      </div>
    </div>
  );
};

// 影响分析卡片
const ImpactCard: React.FC<{
  indicator: string;
  impact_level: string;
  direction: string;
  reasoning: string;
}> = ({ indicator, impact_level, direction, reasoning }) => {
  const directionColor = direction === 'Bullish' ? 'border-green-500 bg-green-500/10' :
                         direction === 'Bearish' ? 'border-red-500 bg-red-500/10' :
                         'border-gray-500 bg-gray-500/10';

  const directionIcon = direction === 'Bullish' ? <TrendingUp className="w-4 h-4 text-green-400" /> :
                        direction === 'Bearish' ? <TrendingDown className="w-4 h-4 text-red-400" /> :
                        <Minus className="w-4 h-4 text-gray-400" />;

  const levelBadge = impact_level === 'High' ? 'bg-red-500/20 text-red-400' :
                     impact_level === 'Medium' ? 'bg-yellow-500/20 text-yellow-400' :
                     'bg-gray-500/20 text-gray-400';

  return (
    <div className={`p-4 rounded-lg border-l-4 ${directionColor}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {directionIcon}
          <span className="font-medium text-white">{indicator}</span>
        </div>
        <span className={`text-xs px-2 py-1 rounded-full ${levelBadge}`}>
          {impact_level}
        </span>
      </div>
      <p className="text-sm text-gray-300">{reasoning}</p>
    </div>
  );
};

const MacroDashboard: React.FC<MacroDashboardProps> = ({ onClose }) => {
  const { data: analysisData, isLoading, error, isFetching } = useMacroImpactAnalysis('US');
  const analysis = analysisData as unknown as T.MacroImpactAnalysis;
  const refreshMutation = useRefreshMacro();

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  const handleRefresh = () => {
    refreshMutation.mutate();
  };

  // 情绪颜色
  const sentimentColor = analysis?.market_outlook?.includes('Bullish') ? 'text-green-400' :
                         analysis?.market_outlook?.includes('Bearish') ? 'text-red-400' :
                         'text-yellow-400';

  return (
    <div
      onClick={handleBackdropClick}
      className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
    >
      <div className="bg-gray-900 border border-gray-800 w-full max-w-5xl max-h-[90vh] rounded-xl flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="shrink-0 p-4 border-b border-gray-800 bg-gray-950/50 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Globe className="w-6 h-6 text-blue-400" />
            <div>
              <h2 className="text-xl font-bold text-white">Macro Economic Dashboard</h2>
              <p className="text-xs text-gray-500">
                {analysis?.overview?.last_updated
                  ? `Last updated: ${analysis.overview.last_updated}`
                  : 'Loading...'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* 整体情绪 */}
            {analysis && (
              <div className={`flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 ${sentimentColor}`}>
                <Activity className="w-4 h-4" />
                <span className="font-bold">{analysis.market_outlook}</span>
              </div>
            )}

            <button
              onClick={handleRefresh}
              disabled={refreshMutation.isPending || isFetching}
              className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${(refreshMutation.isPending || isFetching) ? 'animate-spin' : ''}`} />
              Refresh
            </button>

            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 p-2 rounded-full transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <RefreshCw className="w-12 h-12 animate-spin text-gray-600" />
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-64 text-red-400">
              <AlertTriangle className="w-12 h-12 mb-4" />
              <p>获取宏观数据失败</p>
              <button
                onClick={handleRefresh}
                className="mt-4 px-4 py-2 bg-gray-800 rounded-lg hover:bg-gray-700"
              >
                重试
              </button>
            </div>
          ) : analysis ? (
            <div className="space-y-6">
              {/* 摘要 */}
              <div className="bg-gradient-to-r from-blue-900/30 to-purple-900/30 rounded-xl p-4 border border-blue-800/50">
                <p className="text-gray-200">{analysis.market_outlook}</p>
              </div>

              {/* 影响分析 */}
              {analysis.impacts && analysis.impacts.length > 0 && (
                <div>
                  <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                    <Activity className="w-5 h-5 text-orange-400" />
                    Impact Analysis
                  </h3>
                  <div className="space-y-3">
                    {(analysis.impacts || []).map((impact: T.MacroImpact, i: number) => (
                      <ImpactCard
                        key={i}
                        indicator={impact.indicator}
                        impact_level={impact.impact_level}
                        direction={impact.direction}
                        reasoning={impact.reasoning}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* 市场展望 */}
              <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
                <h3 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
                  <Globe className="w-5 h-5 text-purple-400" />
                  Market Outlook
                </h3>
                <p className="text-gray-200">{analysis.market_outlook}</p>
              </div>

              {/* 风险与机会 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* 风险因素 */}
                {analysis.risk_factors && analysis.risk_factors.length > 0 && (
                  <div className="bg-red-950/20 rounded-xl p-4 border border-red-900/50">
                    <h4 className="text-sm font-bold text-red-400 mb-3 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4" />
                      Risk Factors
                    </h4>
                    <ul className="space-y-2">
                      {(analysis.risk_factors || []).map((risk, i) => (
                        <li key={i} className="text-sm text-gray-300 flex items-start gap-2">
                          <span className="text-red-400 mt-1">•</span>
                          <span>{risk}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* 机会 */}
                {analysis.opportunities && analysis.opportunities.length > 0 && (
                  <div className="bg-green-950/20 rounded-xl p-4 border border-green-900/50">
                    <h4 className="text-sm font-bold text-green-400 mb-3 flex items-center gap-2">
                      <Lightbulb className="w-4 h-4" />
                      Opportunities
                    </h4>
                    <ul className="space-y-2">
                      {(analysis.opportunities || []).map((opp, i) => (
                        <li key={i} className="text-sm text-gray-300 flex items-start gap-2">
                          <span className="text-green-400 mt-1">•</span>
                          <span>{opp}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default MacroDashboard;
