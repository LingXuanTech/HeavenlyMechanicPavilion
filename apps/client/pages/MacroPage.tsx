/**
 * 宏观经济页面
 *
 * 展示宏观经济数据和影响分析
 */
import React from 'react';
import {
  Globe,
  TrendingUp,
  TrendingDown,
  Minus,
  DollarSign,
  BarChart3,
  AlertTriangle,
  Lightbulb,
  RefreshCw,
  Activity,
} from 'lucide-react';
import PageLayout, { LoadingState, EmptyState } from '../components/layout/PageLayout';
import { useMacroImpactAnalysis, useRefreshMacro } from '../hooks/useMacro';
import type * as T from '../src/types/schema';

// 趋势图标组件
const TrendIcon: React.FC<{ trend: string; className?: string }> = ({ trend, className = "w-4 h-4" }) => {
  if (trend === 'up') return <TrendingUp className={`${className} text-green-400`} />;
  if (trend === 'down') return <TrendingDown className={`${className} text-red-400`} />;
  return <Minus className={`${className} text-stone-400`} />;
};

// 单个指标卡片
const IndicatorCard: React.FC<{ indicator: T.MacroIndicator; icon: React.ReactNode }> = ({ indicator, icon }) => {
  const changeColor = indicator.change && indicator.change > 0 ? 'text-green-400' :
                      indicator.change && indicator.change < 0 ? 'text-red-400' : 'text-stone-400';

  return (
    <div className="bg-surface-overlay/50 rounded-xl p-4 border border-border-strong hover:border-stone-600 transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-stone-400">{icon}</span>
          <span className="text-sm text-stone-400">{indicator.name}</span>
        </div>
        <TrendIcon trend={indicator.trend} />
      </div>

      <div className="flex items-end gap-2">
        <span className="text-2xl font-bold text-white">
          {indicator.value}{indicator.unit}
        </span>
        {indicator.change !== undefined && indicator.change !== null && (
          <span className={`text-sm ${changeColor}`}>
            {indicator.change > 0 ? '+' : ''}{indicator.change.toFixed(2)}
            {indicator.change_percent !== undefined && indicator.change_percent !== null && (
              <span className="ml-1">({indicator.change_percent.toFixed(1)}%)</span>
            )}
          </span>
        )}
      </div>

      <div className="mt-2 text-xs text-stone-500">
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
                         'border-stone-500 bg-stone-500/10';

  const directionIcon = direction === 'Bullish' ? <TrendingUp className="w-4 h-4 text-green-400" /> :
                        direction === 'Bearish' ? <TrendingDown className="w-4 h-4 text-red-400" /> :
                        <Minus className="w-4 h-4 text-stone-400" />;

  const levelBadge = impact_level === 'High' ? 'bg-red-500/20 text-red-400' :
                     impact_level === 'Medium' ? 'bg-yellow-500/20 text-yellow-400' :
                     'bg-stone-500/20 text-stone-400';

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
      <p className="text-sm text-stone-300">{reasoning}</p>
    </div>
  );
};

const MacroPage: React.FC = () => {
  const { data: analysis, isLoading, error, isFetching } = useMacroImpactAnalysis('US');
  const refreshMutation = useRefreshMacro();

  const handleRefresh = () => {
    refreshMutation.mutate();
  };

  // 情绪颜色
  const sentimentColor = analysis?.overview.sentiment === 'Bullish' ? 'text-green-400' :
                         analysis?.overview.sentiment === 'Bearish' ? 'text-red-400' :
                         'text-yellow-400';

  // Header 右侧内容：情绪指示器
  const headerRight = analysis && (
    <div className={`flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-overlay ${sentimentColor}`}>
      <Activity className="w-4 h-4" />
      <span className="font-bold">{analysis.overview.sentiment}</span>
    </div>
  );

  return (
    <PageLayout
      title="Macro Economic Dashboard"
      subtitle={analysis?.overview.last_updated
        ? `Last updated: ${new Date(analysis.overview.last_updated).toLocaleString()}`
        : '加载中...'}
      icon={Globe}
      iconColor="text-accent"
      iconBgColor="bg-accent/10"
      variant="wide"
      actions={[
        {
          label: '刷新',
          icon: RefreshCw,
          onClick: handleRefresh,
          loading: refreshMutation.isPending || isFetching,
          variant: 'primary',
        },
      ]}
      headerRight={headerRight}
    >
      {isLoading ? (
        <LoadingState message="获取宏观数据..." />
      ) : error ? (
        <EmptyState
          icon={AlertTriangle}
          title="获取宏观数据失败"
          description="请检查网络连接后重试"
          action={
            <button
              onClick={handleRefresh}
              className="px-4 py-2 bg-surface-overlay rounded-lg hover:bg-surface-muted text-white"
            >
              重试
            </button>
          }
        />
      ) : analysis ? (
        <div className="space-y-6">
            {/* 摘要 */}
            <div className="bg-gradient-to-r from-amber-900/30 to-yellow-900/30 rounded-xl p-4 border border-amber-800/50">
              <p className="text-stone-200">{analysis.overview.summary}</p>
            </div>

            {/* 指标网格 */}
            <div>
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-cyan-400" />
                Key Indicators
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {analysis.overview.fed_rate && (
                  <IndicatorCard
                    indicator={analysis.overview.fed_rate}
                    icon={<DollarSign className="w-4 h-4" />}
                  />
                )}
                {analysis.overview.gdp_growth && (
                  <IndicatorCard
                    indicator={analysis.overview.gdp_growth}
                    icon={<TrendingUp className="w-4 h-4" />}
                  />
                )}
                {analysis.overview.unemployment && (
                  <IndicatorCard
                    indicator={analysis.overview.unemployment}
                    icon={<Activity className="w-4 h-4" />}
                  />
                )}
                {analysis.overview.cpi && (
                  <IndicatorCard
                    indicator={analysis.overview.cpi}
                    icon={<BarChart3 className="w-4 h-4" />}
                  />
                )}
                {analysis.overview.treasury_10y && (
                  <IndicatorCard
                    indicator={analysis.overview.treasury_10y}
                    icon={<DollarSign className="w-4 h-4" />}
                  />
                )}
                {analysis.overview.vix && (
                  <IndicatorCard
                    indicator={analysis.overview.vix}
                    icon={<AlertTriangle className="w-4 h-4" />}
                  />
                )}
                {analysis.overview.dxy && (
                  <IndicatorCard
                    indicator={analysis.overview.dxy}
                    icon={<DollarSign className="w-4 h-4" />}
                  />
                )}
              </div>
            </div>

            {/* 影响分析 */}
            {analysis.impacts && analysis.impacts.length > 0 && (
              <div>
                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                  <Activity className="w-5 h-5 text-orange-400" />
                  Impact Analysis
                </h3>
                <div className="space-y-3">
                  {analysis.impacts.map((impact, i) => (
                    <ImpactCard key={i} {...impact} />
                  ))}
                </div>
              </div>
            )}

            {/* 市场展望 */}
            <div className="bg-surface-overlay/50 rounded-xl p-4 border border-border-strong">
              <h3 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
                <Globe className="w-5 h-5 text-purple-400" />
                Market Outlook
              </h3>
              <p className="text-stone-200">{analysis.market_outlook}</p>
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
                    {analysis.risk_factors.map((risk, i) => (
                      <li key={i} className="text-sm text-stone-300 flex items-start gap-2">
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
                    {analysis.opportunities.map((opp, i) => (
                      <li key={i} className="text-sm text-stone-300 flex items-start gap-2">
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
    </PageLayout>
  );
};

export default MacroPage;
