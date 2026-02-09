/**
 * 风控仪表盘组件
 *
 * 展示 VaR 分布直方图、压力测试场景卡片和风险指标雷达图
 */
import React, { useEffect, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts';
import { Shield, AlertTriangle, TrendingDown, Loader2, RefreshCw } from 'lucide-react';
import { useCalculateVaR, useStressTest, useRiskMetrics } from '../hooks/useRiskModeling';
import type { VaRResult, StressTestResult, RiskMetrics } from '../hooks/useRiskModeling';

interface RiskDashboardProps {
  symbols: string[];
  weights?: number[];
}

const RiskDashboard: React.FC<RiskDashboardProps> = ({ symbols, weights }) => {
  const varMutation = useCalculateVaR();
  const stressMutation = useStressTest();
  const metricsMutation = useRiskMetrics();

  const [varData, setVarData] = useState<VaRResult | null>(null);
  const [stressData, setStressData] = useState<StressTestResult | null>(null);
  const [metricsData, setMetricsData] = useState<RiskMetrics | null>(null);

  const runAll = async () => {
    if (symbols.length === 0) return;

    const params = { symbols, weights };

    try {
      const [v, s, m] = await Promise.all([
        varMutation.mutateAsync({ ...params, confidence: 0.95, simulations: 10000 }),
        stressMutation.mutateAsync(params),
        metricsMutation.mutateAsync(params),
      ]);
      setVarData(v as VaRResult);
      setStressData(s as StressTestResult);
      setMetricsData(m as RiskMetrics);
    } catch (e) {
      console.error('Risk analysis failed', e);
    }
  };

  useEffect(() => {
    if (symbols.length >= 1) {
      runAll();
    }
  }, [symbols.join(',')]);

  const isLoading = varMutation.isPending || stressMutation.isPending || metricsMutation.isPending;

  if (symbols.length === 0) {
    return (
      <div className="text-center py-12 text-stone-500">
        请先添加股票到组合中
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 标题栏 */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-bold text-white flex items-center gap-2">
          <Shield className="w-5 h-5 text-accent" />
          风控分析
        </h3>
        <button
          onClick={runAll}
          disabled={isLoading}
          className="text-sm text-accent hover:text-amber-300 flex items-center gap-1 disabled:opacity-50"
        >
          {isLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
          重新计算
        </button>
      </div>

      {isLoading && !varData ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-accent" />
          <span className="ml-2 text-stone-400">正在计算风险指标...</span>
        </div>
      ) : (
        <>
          {/* VaR 分布直方图 */}
          {varData && (
            <div className="bg-surface-raised/50 border border-border rounded-xl p-5">
              <h4 className="text-white font-medium mb-1 flex items-center gap-2">
                <TrendingDown className="w-4 h-4 text-red-400" />
                VaR 分布 (蒙特卡洛 {varData.simulations.toLocaleString()} 次模拟)
              </h4>
              <p className="text-xs text-stone-500 mb-4">{varData.var_interpretation}</p>

              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="text-center p-3 bg-red-500/10 rounded-lg border border-red-500/20">
                  <div className="text-xs text-stone-400">VaR ({(varData.confidence * 100).toFixed(0)}%)</div>
                  <div className="text-lg font-bold text-red-400">{varData.var.toFixed(2)}%</div>
                </div>
                <div className="text-center p-3 bg-orange-500/10 rounded-lg border border-orange-500/20">
                  <div className="text-xs text-stone-400">CVaR</div>
                  <div className="text-lg font-bold text-orange-400">{varData.cvar.toFixed(2)}%</div>
                </div>
                <div className="text-center p-3 bg-surface-overlay/50 rounded-lg border border-border">
                  <div className="text-xs text-stone-400">预期收益</div>
                  <div className={`text-lg font-bold ${varData.stats.mean_return >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {varData.stats.mean_return >= 0 ? '+' : ''}{varData.stats.mean_return.toFixed(2)}%
                  </div>
                </div>
              </div>

              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={varData.histogram}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#44403c" vertical={false} />
                    <XAxis
                      dataKey="bin_center"
                      stroke="#6b7280"
                      tick={{ fontSize: 10 }}
                      tickFormatter={(v: number) => `${(v * 100).toFixed(1)}%`}
                    />
                    <YAxis stroke="#6b7280" tick={{ fontSize: 10 }} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1c1917', border: '1px solid #44403c', fontSize: 12 }}
                      formatter={(value: number | undefined) => [value ?? 0, '频次']}
                      labelFormatter={(v) => `收益率: ${(Number(v) * 100).toFixed(2)}%`}
                    />
                    <Bar dataKey="count" fill="#D97706" opacity={0.8} />
                    <ReferenceLine x={varData.var / 100} stroke="#EF4444" strokeWidth={2} label={{ value: 'VaR', fill: '#EF4444', fontSize: 11 }} />
                    <ReferenceLine x={varData.cvar / 100} stroke="#F97316" strokeDasharray="3 3" label={{ value: 'CVaR', fill: '#F97316', fontSize: 11 }} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* 压力测试 */}
          {stressData && (
            <div className="bg-surface-raised/50 border border-border rounded-xl p-5">
              <h4 className="text-white font-medium mb-4 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                压力测试场景
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {stressData.scenarios.map((s) => (
                  <div
                    key={s.scenario_id}
                    className="p-4 bg-surface-overlay/50 rounded-lg border border-border hover:border-red-500/30 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h5 className="font-medium text-stone-200">{s.name}</h5>
                      <span className={`text-lg font-bold ${s.portfolio_loss < -20 ? 'text-red-400' : s.portfolio_loss < -10 ? 'text-orange-400' : 'text-amber-400'}`}>
                        {s.portfolio_loss.toFixed(1)}%
                      </span>
                    </div>
                    <p className="text-xs text-stone-500 mb-2">{s.description}</p>
                    <div className="w-full bg-surface-muted rounded-full h-1.5">
                      <div
                        className={`h-1.5 rounded-full ${Math.abs(s.portfolio_loss) > 30 ? 'bg-red-500' : Math.abs(s.portfolio_loss) > 15 ? 'bg-orange-500' : 'bg-amber-500'}`}
                        style={{ width: `${Math.min(Math.abs(s.portfolio_loss), 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 风险指标雷达图 */}
          {metricsData && (
            <div className="bg-surface-raised/50 border border-border rounded-xl p-5">
              <h4 className="text-white font-medium mb-4 flex items-center gap-2">
                <Shield className="w-4 h-4 text-emerald-400" />
                综合风险指标
              </h4>

              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
                <MetricCard label="年化波动率" value={`${metricsData.metrics.volatility}%`} desc={metricsData.interpretation.volatility} />
                <MetricCard label="夏普比率" value={metricsData.metrics.sharpe_ratio.toFixed(2)} desc={metricsData.interpretation.sharpe} />
                <MetricCard label="最大回撤" value={`${metricsData.metrics.max_drawdown}%`} desc={metricsData.interpretation.drawdown} negative />
                <MetricCard label="Sortino 比率" value={metricsData.metrics.sortino_ratio.toFixed(2)} desc={`Beta: ${metricsData.metrics.beta.toFixed(2)}`} />
              </div>

              <div className="h-64 flex items-center justify-center">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart
                    data={[
                      { metric: '收益率', value: Math.min(Math.max(metricsData.metrics.annual_return + 50, 0), 100) },
                      { metric: '夏普', value: Math.min(Math.max(metricsData.metrics.sharpe_ratio * 33, 0), 100) },
                      { metric: '低波动', value: Math.min(Math.max(100 - metricsData.metrics.volatility * 2, 0), 100) },
                      { metric: '低回撤', value: Math.min(Math.max(100 + metricsData.metrics.max_drawdown * 2, 0), 100) },
                      { metric: '分散化', value: Math.min(Math.max(100 - metricsData.metrics.avg_correlation * 100, 0), 100) },
                    ]}
                  >
                    <PolarGrid stroke="#44403c" />
                    <PolarAngleAxis dataKey="metric" tick={{ fill: '#9CA3AF', fontSize: 12 }} />
                    <PolarRadiusAxis tick={false} domain={[0, 100]} />
                    <Radar dataKey="value" stroke="#D97706" fill="#D97706" fillOpacity={0.3} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

const MetricCard: React.FC<{ label: string; value: string; desc: string; negative?: boolean }> = ({
  label,
  value,
  desc,
  negative,
}) => (
  <div className="p-3 bg-surface-overlay/50 rounded-lg border border-border">
    <div className="text-xs text-stone-500 mb-1">{label}</div>
    <div className={`text-lg font-bold ${negative ? 'text-red-400' : 'text-white'}`}>{value}</div>
    <div className="text-[10px] text-stone-500 mt-1 truncate" title={desc}>{desc}</div>
  </div>
);

export default RiskDashboard;
