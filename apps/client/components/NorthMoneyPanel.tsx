/**
 * 北向资金面板（增强版）
 *
 * 显示沪深港通北向资金流向，包括：
 * - 基础流向概览
 * - 盘中实时分时图
 * - 异常信号提示
 * - 板块轮动面板
 * - 净买入/卖出 TOP
 */
import React, { useState, memo } from 'react';
import {
  ArrowUpCircle,
  ArrowDownCircle,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  DollarSign,
  BarChart3,
  Info,
  AlertTriangle,
  Activity,
  Layers,
  Clock,
  Zap,
  Shield,
  Target,
  ChevronRight,
} from 'lucide-react';
import {
  useNorthMoneySummary,
  useNorthMoneyHistory,
  useNorthMoneyIntraday,
  useNorthMoneyAnomalies,
  useNorthMoneySectorFlow,
  useNorthMoneyRotationSignal,
} from '../hooks';
import type * as T from '../src/types/schema';

interface NorthMoneyPanelProps {
  compact?: boolean;
  onStockClick?: (symbol: string) => void;
}

// ============ 工具函数 ============

const formatMoney = (value: number): string => {
  const abs = Math.abs(value);
  if (abs >= 100) {
    return `${value >= 0 ? '+' : ''}${value.toFixed(0)}亿`;
  }
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}亿`;
};

const getTrendColor = (trend: string): string => {
  if (trend === 'Inflow') return 'text-red-400';
  if (trend === 'Outflow') return 'text-green-400';
  return 'text-gray-400';
};

const getTrendIcon = (trend: string) => {
  if (trend === 'Inflow') {
    return <ArrowUpCircle className="w-4 h-4 text-red-400" />;
  }
  if (trend === 'Outflow') {
    return <ArrowDownCircle className="w-4 h-4 text-green-400" />;
  }
  return <BarChart3 className="w-4 h-4 text-gray-400" />;
};

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case 'critical': return 'bg-red-500/20 border-red-500/50 text-red-400';
    case 'high': return 'bg-orange-500/20 border-orange-500/50 text-orange-400';
    case 'medium': return 'bg-yellow-500/20 border-yellow-500/50 text-yellow-400';
    default: return 'bg-blue-500/20 border-blue-500/50 text-blue-400';
  }
};

const getRotationPatternInfo = (pattern: string) => {
  switch (pattern) {
    case 'defensive':
      return { label: '防御型', color: 'text-blue-400', icon: Shield };
    case 'aggressive':
      return { label: '进攻型', color: 'text-red-400', icon: Zap };
    case 'broad_inflow':
      return { label: '全面流入', color: 'text-green-400', icon: TrendingUp };
    case 'broad_outflow':
      return { label: '全面流出', color: 'text-red-400', icon: TrendingDown };
    case 'mixed':
      return { label: '分化', color: 'text-yellow-400', icon: Activity };
    default:
      return { label: '不明确', color: 'text-gray-400', icon: BarChart3 };
  }
};

// ============ 子组件 ============

/** 资金流向卡片 */
const FlowCard: React.FC<{
  title: string;
  value: number;
  subTitle?: string;
  subValue?: number;
}> = ({ title, value, subTitle, subValue }) => {
  const isPositive = value >= 0;

  return (
    <div className="bg-gray-950/50 rounded border border-gray-800 p-3">
      <div className="text-xs text-gray-500 mb-1">{title}</div>
      <div className={`text-lg font-mono font-bold ${isPositive ? 'text-red-400' : 'text-green-400'}`}>
        {formatMoney(value)}
      </div>
      {subTitle && subValue !== undefined && (
        <div className="text-[10px] text-gray-500 mt-1">
          {subTitle}: <span className={subValue >= 0 ? 'text-red-400' : 'text-green-400'}>
            {formatMoney(subValue)}
          </span>
        </div>
      )}
    </div>
  );
};

/** TOP 股票行 */
const TopStockRow: React.FC<{
  stock: T.NorthMoneyTopStock;
  onClick?: () => void;
}> = ({ stock, onClick }) => {
  const isPositive = stock.net_buy >= 0;

  return (
    <div
      className="flex items-center justify-between py-2 px-3 hover:bg-gray-800/30 cursor-pointer transition-colors border-b border-gray-800/50 last:border-b-0"
      onClick={onClick}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-white truncate">{stock.name}</span>
          <span className="text-[10px] text-gray-500 font-mono">{stock.symbol}</span>
        </div>
        <div className="text-[10px] text-gray-500">
          持股比例: {stock.holding_ratio.toFixed(2)}%
        </div>
      </div>
      <div className="text-right">
        <div className={`text-sm font-mono font-semibold ${isPositive ? 'text-red-400' : 'text-green-400'}`}>
          {formatMoney(stock.net_buy)}
        </div>
      </div>
    </div>
  );
};

/** 历史迷你图 */
const MiniChart: React.FC<{ data: T.NorthMoneyHistory[] }> = ({ data }) => {
  if (!data || data.length === 0) return null;

  const values = data.map(d => d.total);
  const max = Math.max(...values.map(Math.abs));
  const height = 40;
  const width = 120;
  const barWidth = width / data.length - 1;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-10">
      {data.map((d, i) => {
        const barHeight = (Math.abs(d.total) / max) * (height / 2 - 2);
        const y = d.total >= 0 ? height / 2 - barHeight : height / 2;
        const fill = d.total >= 0 ? '#f87171' : '#4ade80';

        return (
          <rect
            key={i}
            x={i * (barWidth + 1)}
            y={y}
            width={barWidth}
            height={barHeight}
            fill={fill}
            rx={1}
          />
        );
      })}
      <line x1={0} y1={height / 2} x2={width} y2={height / 2} stroke="#374151" strokeWidth={1} />
    </svg>
  );
};

/** 盘中分时图 */
const IntradayChart: React.FC<{ data: T.IntradayFlowSummary }> = memo(({ data }) => {
  const points = data.flow_points;
  if (!points || points.length === 0) {
    return (
      <div className="text-center py-4 text-gray-500 text-xs">
        暂无盘中数据
      </div>
    );
  }

  const width = 280;
  const height = 80;
  const padding = { top: 10, right: 10, bottom: 20, left: 35 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const values = points.map(p => p.cumulative_total);
  const maxVal = Math.max(...values.map(Math.abs), 1);

  // 生成路径
  const pathPoints = points.map((p, i) => {
    const x = padding.left + (i / (points.length - 1)) * chartWidth;
    const y = padding.top + chartHeight / 2 - (p.cumulative_total / maxVal) * (chartHeight / 2);
    return `${i === 0 ? 'M' : 'L'}${x},${y}`;
  }).join(' ');

  // 填充区域路径
  const areaPath = pathPoints +
    ` L${padding.left + chartWidth},${padding.top + chartHeight / 2}` +
    ` L${padding.left},${padding.top + chartHeight / 2} Z`;

  const currentTotal = data.current_total;
  const isPositive = currentTotal >= 0;

  return (
    <div className="bg-gray-950/50 rounded border border-gray-800 p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Activity className="w-3 h-3 text-blue-400" />
          <span className="text-xs text-gray-400">盘中分时</span>
        </div>
        <div className="flex items-center gap-2 text-[10px]">
          <span className="text-gray-500">{data.last_update}</span>
          <span className={`font-mono font-bold ${isPositive ? 'text-red-400' : 'text-green-400'}`}>
            {formatMoney(currentTotal)}
          </span>
        </div>
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} className="w-full">
        {/* 零线 */}
        <line
          x1={padding.left}
          y1={padding.top + chartHeight / 2}
          x2={width - padding.right}
          y2={padding.top + chartHeight / 2}
          stroke="#374151"
          strokeWidth={1}
          strokeDasharray="4,2"
        />

        {/* 填充区域 */}
        <path
          d={areaPath}
          fill={isPositive ? 'rgba(248, 113, 113, 0.1)' : 'rgba(74, 222, 128, 0.1)'}
        />

        {/* 折线 */}
        <path
          d={pathPoints}
          fill="none"
          stroke={isPositive ? '#f87171' : '#4ade80'}
          strokeWidth={1.5}
        />

        {/* Y轴刻度 */}
        <text x={padding.left - 5} y={padding.top + 4} textAnchor="end" className="fill-gray-500 text-[8px]">
          +{maxVal.toFixed(0)}
        </text>
        <text x={padding.left - 5} y={padding.top + chartHeight} textAnchor="end" className="fill-gray-500 text-[8px]">
          -{maxVal.toFixed(0)}
        </text>

        {/* X轴时间标签 */}
        {points.length > 0 && (
          <>
            <text x={padding.left} y={height - 5} textAnchor="start" className="fill-gray-500 text-[8px]">
              {points[0].time}
            </text>
            <text x={width - padding.right} y={height - 5} textAnchor="end" className="fill-gray-500 text-[8px]">
              {points[points.length - 1].time}
            </text>
          </>
        )}
      </svg>

      {/* 统计指标 */}
      <div className="flex justify-between mt-2 text-[10px]">
        <div>
          <span className="text-gray-500">峰值流入:</span>
          <span className="text-red-400 ml-1 font-mono">{formatMoney(data.peak_inflow)}</span>
        </div>
        <div>
          <span className="text-gray-500">峰值流出:</span>
          <span className="text-green-400 ml-1 font-mono">{formatMoney(data.peak_outflow)}</span>
        </div>
        <div>
          <span className="text-gray-500">动量:</span>
          <span className={`ml-1 ${
            data.momentum === 'accelerating' ? 'text-red-400' :
            data.momentum === 'decelerating' ? 'text-green-400' :
            'text-gray-400'
          }`}>
            {data.momentum === 'accelerating' ? '加速流入' :
             data.momentum === 'decelerating' ? '加速流出' : '平稳'}
          </span>
        </div>
      </div>
    </div>
  );
});
IntradayChart.displayName = 'IntradayChart';

/** 异常信号提示 */
const AnomalyAlerts: React.FC<{ anomalies: T.NorthMoneyAnomaly[] }> = memo(({ anomalies }) => {
  if (!anomalies || anomalies.length === 0) return null;

  return (
    <div className="space-y-2">
      {anomalies.slice(0, 3).map((anomaly, idx) => (
        <div
          key={idx}
          className={`p-3 rounded border ${getSeverityColor(anomaly.severity)}`}
        >
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-bold uppercase">{anomaly.severity}</span>
                <span className="text-[10px] opacity-70">
                  {anomaly.anomaly_type.replace(/_/g, ' ')}
                </span>
              </div>
              <p className="text-xs opacity-90 mb-1">{anomaly.description}</p>
              <p className="text-[10px] opacity-70">
                💡 {anomaly.recommendation}
              </p>
              {anomaly.affected_stocks && anomaly.affected_stocks.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {anomaly.affected_stocks.slice(0, 3).map((stock, i) => (
                    <span key={i} className="text-[10px] px-1.5 py-0.5 bg-black/20 rounded">
                      {stock}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
});
AnomalyAlerts.displayName = 'AnomalyAlerts';

/** 板块轮动面板 */
const SectorRotationPanel: React.FC<{
  sectorFlow: T.NorthMoneySectorFlow[];
  rotationSignal: T.SectorRotationSignal | null;
}> = memo(({ sectorFlow, rotationSignal }) => {
  const [showAll, setShowAll] = useState(false);

  const inflowSectors = sectorFlow.filter(s => s.flow_direction === 'inflow').slice(0, showAll ? 10 : 5);
  const outflowSectors = sectorFlow.filter(s => s.flow_direction === 'outflow').slice(0, showAll ? 10 : 5);

  const patternInfo = rotationSignal ? getRotationPatternInfo(rotationSignal.rotation_pattern) : null;
  const PatternIcon = patternInfo?.icon || BarChart3;

  return (
    <div className="space-y-3">
      {/* 轮动信号 */}
      {rotationSignal && (
        <div className="bg-gray-950/50 rounded border border-gray-800 p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Layers className="w-3 h-3 text-purple-400" />
              <span className="text-xs text-gray-400">轮动信号</span>
            </div>
            <div className="flex items-center gap-2">
              <PatternIcon className={`w-4 h-4 ${patternInfo?.color}`} />
              <span className={`text-sm font-bold ${patternInfo?.color}`}>
                {patternInfo?.label}
              </span>
              <span className="text-[10px] text-gray-500">
                强度 {rotationSignal.signal_strength}%
              </span>
            </div>
          </div>
          <p className="text-xs text-gray-300 leading-relaxed">
            {rotationSignal.interpretation}
          </p>
        </div>
      )}

      {/* 板块流向 */}
      <div className="grid grid-cols-2 gap-3">
        {/* 流入板块 */}
        <div className="bg-gray-950/50 rounded border border-gray-800 p-2">
          <div className="flex items-center gap-1 mb-2 px-1">
            <TrendingUp className="w-3 h-3 text-red-400" />
            <span className="text-[10px] text-red-400 font-bold">资金流入</span>
          </div>
          <div className="space-y-1">
            {inflowSectors.map((sector, idx) => (
              <div key={idx} className="flex items-center justify-between px-2 py-1.5 hover:bg-gray-800/30 rounded text-xs">
                <span className="text-gray-300 truncate">{sector.sector}</span>
                <span className="text-red-400 font-mono shrink-0 ml-2">
                  {formatMoney(sector.net_buy)}
                </span>
              </div>
            ))}
            {inflowSectors.length === 0 && (
              <div className="text-center py-2 text-gray-500 text-[10px]">暂无</div>
            )}
          </div>
        </div>

        {/* 流出板块 */}
        <div className="bg-gray-950/50 rounded border border-gray-800 p-2">
          <div className="flex items-center gap-1 mb-2 px-1">
            <TrendingDown className="w-3 h-3 text-green-400" />
            <span className="text-[10px] text-green-400 font-bold">资金流出</span>
          </div>
          <div className="space-y-1">
            {outflowSectors.map((sector, idx) => (
              <div key={idx} className="flex items-center justify-between px-2 py-1.5 hover:bg-gray-800/30 rounded text-xs">
                <span className="text-gray-300 truncate">{sector.sector}</span>
                <span className="text-green-400 font-mono shrink-0 ml-2">
                  {formatMoney(sector.net_buy)}
                </span>
              </div>
            ))}
            {outflowSectors.length === 0 && (
              <div className="text-center py-2 text-gray-500 text-[10px]">暂无</div>
            )}
          </div>
        </div>
      </div>

      {/* 展开更多 */}
      {(sectorFlow.filter(s => s.flow_direction === 'inflow').length > 5 ||
        sectorFlow.filter(s => s.flow_direction === 'outflow').length > 5) && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="w-full text-center text-[10px] text-gray-500 hover:text-gray-300 py-1"
        >
          {showAll ? '收起' : '查看更多板块'} <ChevronRight className={`w-3 h-3 inline transition-transform ${showAll ? 'rotate-90' : ''}`} />
        </button>
      )}
    </div>
  );
});
SectorRotationPanel.displayName = 'SectorRotationPanel';

// ============ 主组件 ============

const NorthMoneyPanel: React.FC<NorthMoneyPanelProps> = ({
  compact = false,
  onStockClick,
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'realtime' | 'sectors' | 'stocks'>('overview');
  const [stockTab, setStockTab] = useState<'buys' | 'sells'>('buys');
  const [showInfo, setShowInfo] = useState(false);

  // 基础数据
  const { data: summary, isLoading, refetch, isRefetching } = useNorthMoneySummary();
  const { data: history } = useNorthMoneyHistory(10);

  // 实时数据
  const { data: intraday } = useNorthMoneyIntraday();
  const { data: anomalies } = useNorthMoneyAnomalies();

  // 板块数据
  const { data: sectorFlow } = useNorthMoneySectorFlow();
  const { data: rotationSignal } = useNorthMoneyRotationSignal();

  const handleRefresh = () => {
    refetch();
  };

  // 紧凑模式
  if (compact && summary) {
    const isInflow = summary.trend === 'Inflow';
    const hasAnomaly = anomalies && anomalies.length > 0;

    return (
      <div className="flex items-center gap-4 px-3 py-2 bg-gray-900/50 rounded border border-gray-800">
        <div className="flex items-center gap-2">
          <DollarSign className="w-4 h-4 text-yellow-500" />
          <span className="text-xs text-gray-400">北向资金</span>
        </div>
        <div className={`text-sm font-mono font-semibold ${isInflow ? 'text-red-400' : 'text-green-400'}`}>
          {formatMoney(summary.today.total)}
        </div>
        <div className="text-[10px] text-gray-500">
          近期趋势: {isInflow ? '流入' : '流出'}
        </div>
        {hasAnomaly && (
          <div title="检测到异常信号">
            <AlertTriangle className="w-3 h-3 text-yellow-500" />
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-950/50 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-yellow-500" />
            <span className="text-sm font-semibold text-white">北向资金</span>
          </div>

          {summary && (
            <div className="hidden sm:flex items-center gap-2">
              {getTrendIcon(summary.trend)}
              <span className={`text-xs font-medium ${getTrendColor(summary.trend)}`}>
                近期趋势: {summary.trend === 'Inflow' ? '净流入' : summary.trend === 'Outflow' ? '净流出' : '持平'}
              </span>
            </div>
          )}

          {/* 异常标记 */}
          {anomalies && anomalies.length > 0 && (
            <div className="flex items-center gap-1 px-2 py-0.5 bg-yellow-500/20 rounded text-yellow-400">
              <AlertTriangle className="w-3 h-3" />
              <span className="text-[10px] font-bold">{anomalies.length}</span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowInfo(!showInfo)}
            className="p-1.5 hover:bg-gray-800 rounded transition-colors"
            title="数据说明"
          >
            <Info className="w-3.5 h-3.5 text-gray-400" />
          </button>
          <button
            onClick={handleRefresh}
            disabled={isRefetching}
            className="p-1.5 hover:bg-gray-800 rounded transition-colors disabled:opacity-50"
            title="刷新数据"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-gray-400 ${isRefetching ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Info Tooltip */}
      {showInfo && (
        <div className="px-4 py-2 bg-gray-800/50 text-xs text-gray-400 border-b border-gray-800">
          北向资金指通过沪港通、深港通渠道流入A股的境外资金。红色表示净流入（买入），绿色表示净流出（卖出）。
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-gray-800 bg-gray-950/30">
        {[
          { key: 'overview', label: '概览', icon: BarChart3 },
          { key: 'realtime', label: '实时', icon: Activity },
          { key: 'sectors', label: '板块', icon: Layers },
          { key: 'stocks', label: 'TOP', icon: Target },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key as typeof activeTab)}
            className={`flex-1 py-2.5 text-xs font-medium transition-colors flex items-center justify-center gap-1 ${
              activeTab === key
                ? 'text-blue-400 border-b-2 border-blue-400 bg-blue-500/5'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            <Icon className="w-3 h-3" />
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-6 h-6 text-gray-500 animate-spin" />
          </div>
        ) : summary ? (
          <>
            {/* 概览 Tab */}
            {activeTab === 'overview' && (
              <>
                {/* Flow Summary */}
                <div className="grid grid-cols-3 gap-3 mb-4">
                  <FlowCard
                    title="今日合计"
                    value={summary.today.total}
                  />
                  <FlowCard
                    title="沪股通"
                    value={summary.today.sh_connect}
                    subTitle="买入"
                    subValue={summary.today.sh_buy || 0}
                  />
                  <FlowCard
                    title="深股通"
                    value={summary.today.sz_connect}
                    subTitle="买入"
                    subValue={summary.today.sz_buy || 0}
                  />
                </div>

                {/* Mini Chart */}
                {history && history.length > 0 && (
                  <div className="p-3 bg-gray-950/50 rounded border border-gray-800">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-gray-500">近期走势</span>
                      <span className="text-[10px] text-gray-500">
                        累计: <span className={summary.week_total >= 0 ? 'text-red-400' : 'text-green-400'}>
                          {formatMoney(summary.week_total)}
                        </span>
                      </span>
                    </div>
                    <MiniChart data={history} />
                  </div>
                )}

                {/* Timestamp */}
                <div className="text-[10px] text-gray-500 text-right mt-3">
                  数据日期: {summary.today.date}
                </div>
              </>
            )}

            {/* 实时 Tab */}
            {activeTab === 'realtime' && (
              <div className="space-y-4">
                {/* 盘中分时图 */}
                {intraday ? (
                  <IntradayChart data={intraday} />
                ) : (
                  <div className="bg-gray-950/50 rounded border border-gray-800 p-4 text-center text-gray-500 text-xs">
                    <Clock className="w-6 h-6 mx-auto mb-2 opacity-50" />
                    <p>非交易时段，暂无盘中数据</p>
                    <p className="text-[10px] mt-1">交易时段：9:30-11:30, 13:00-15:00</p>
                  </div>
                )}

                {/* 异常信号 */}
                {anomalies && anomalies.length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <AlertTriangle className="w-3 h-3 text-yellow-500" />
                      <span className="text-xs text-gray-400">异常信号 ({anomalies.length})</span>
                    </div>
                    <AnomalyAlerts anomalies={anomalies} />
                  </div>
                )}

                {!intraday && (!anomalies || anomalies.length === 0) && (
                  <div className="text-center py-4 text-gray-500 text-xs">
                    暂无实时数据
                  </div>
                )}
              </div>
            )}

            {/* 板块 Tab */}
            {activeTab === 'sectors' && (
              <SectorRotationPanel
                sectorFlow={sectorFlow || []}
                rotationSignal={rotationSignal || null}
              />
            )}

            {/* TOP Tab */}
            {activeTab === 'stocks' && (
              <>
                {/* Sub Tabs */}
                <div className="flex border-b border-gray-800 mb-3">
                  <button
                    onClick={() => setStockTab('buys')}
                    className={`flex-1 py-2 text-xs font-medium transition-colors ${
                      stockTab === 'buys'
                        ? 'text-red-400 border-b-2 border-red-400'
                        : 'text-gray-500 hover:text-gray-300'
                    }`}
                  >
                    <div className="flex items-center justify-center gap-1">
                      <TrendingUp className="w-3 h-3" />
                      净买入 TOP
                    </div>
                  </button>
                  <button
                    onClick={() => setStockTab('sells')}
                    className={`flex-1 py-2 text-xs font-medium transition-colors ${
                      stockTab === 'sells'
                        ? 'text-green-400 border-b-2 border-green-400'
                        : 'text-gray-500 hover:text-gray-300'
                    }`}
                  >
                    <div className="flex items-center justify-center gap-1">
                      <TrendingDown className="w-3 h-3" />
                      净卖出 TOP
                    </div>
                  </button>
                </div>

                {/* Stock List */}
                <div className="max-h-64 overflow-y-auto">
                  {stockTab === 'buys' ? (
                    summary.top_buys.length > 0 ? (
                      summary.top_buys.slice(0, 10).map((stock) => (
                        <TopStockRow
                          key={stock.symbol}
                          stock={stock}
                          onClick={() => onStockClick?.(stock.symbol)}
                        />
                      ))
                    ) : (
                      <div className="text-center py-4 text-gray-500 text-sm">暂无数据</div>
                    )
                  ) : (
                    summary.top_sells.length > 0 ? (
                      summary.top_sells.slice(0, 10).map((stock) => (
                        <TopStockRow
                          key={stock.symbol}
                          stock={stock}
                          onClick={() => onStockClick?.(stock.symbol)}
                        />
                      ))
                    ) : (
                      <div className="text-center py-4 text-gray-500 text-sm">暂无数据</div>
                    )
                  )}
                </div>
              </>
            )}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-gray-500">
            <DollarSign className="w-8 h-8 mb-2 opacity-50" />
            <p className="text-sm">无法获取北向资金数据</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default memo(NorthMoneyPanel);
