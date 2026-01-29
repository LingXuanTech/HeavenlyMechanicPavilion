/**
 * 北向资金面板
 *
 * 显示沪深港通北向资金流向、净买入TOP等
 */
import React, { useState } from 'react';
import {
  ArrowUpCircle,
  ArrowDownCircle,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  ChevronDown,
  DollarSign,
  BarChart3,
  Info,
} from 'lucide-react';
import { useNorthMoneySummary, useNorthMoneyHistory } from '../hooks';
import type { NorthMoneySummary, NorthMoneyTopStock, NorthMoneyHistory } from '../types';

interface NorthMoneyPanelProps {
  compact?: boolean;
  onStockClick?: (symbol: string) => void;
}

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

const TopStockRow: React.FC<{
  stock: NorthMoneyTopStock;
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

const MiniChart: React.FC<{ data: NorthMoneyHistory[] }> = ({ data }) => {
  if (!data || data.length === 0) return null;

  const values = data.map(d => d.total_net);
  const max = Math.max(...values.map(Math.abs));
  const height = 40;
  const width = 120;
  const barWidth = width / data.length - 1;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-10">
      {data.map((d, i) => {
        const barHeight = (Math.abs(d.total_net) / max) * (height / 2 - 2);
        const y = d.total_net >= 0 ? height / 2 - barHeight : height / 2;
        const fill = d.total_net >= 0 ? '#f87171' : '#4ade80';

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
      {/* 零线 */}
      <line
        x1={0}
        y1={height / 2}
        x2={width}
        y2={height / 2}
        stroke="#374151"
        strokeWidth={1}
      />
    </svg>
  );
};

const NorthMoneyPanel: React.FC<NorthMoneyPanelProps> = ({
  compact = false,
  onStockClick,
}) => {
  const [activeTab, setActiveTab] = useState<'buys' | 'sells'>('buys');
  const [showInfo, setShowInfo] = useState(false);

  const { data: summary, isLoading, refetch, isRefetching } = useNorthMoneySummary();
  const { data: history } = useNorthMoneyHistory(10);

  const handleRefresh = () => {
    refetch();
  };

  // 紧凑模式
  if (compact && summary) {
    const isInflow = summary.trend === 'Inflow';
    return (
      <div className="flex items-center gap-4 px-3 py-2 bg-gray-900/50 rounded border border-gray-800">
        <div className="flex items-center gap-2">
          <DollarSign className="w-4 h-4 text-yellow-500" />
          <span className="text-xs text-gray-400">北向资金</span>
        </div>
        <div className={`text-sm font-mono font-semibold ${isInflow ? 'text-red-400' : 'text-green-400'}`}>
          {formatMoney(summary.flow.total_net)}
        </div>
        <div className="text-[10px] text-gray-500">
          连续{summary.trend_days}日{isInflow ? '流入' : '流出'}
        </div>
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
                连续{summary.trend_days}日{summary.trend === 'Inflow' ? '净流入' : summary.trend === 'Outflow' ? '净流出' : '持平'}
              </span>
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

      {/* Content */}
      <div className="p-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-6 h-6 text-gray-500 animate-spin" />
          </div>
        ) : summary ? (
          <>
            {/* Flow Summary */}
            <div className="grid grid-cols-3 gap-3 mb-4">
              <FlowCard
                title="今日合计"
                value={summary.flow.total_net}
              />
              <FlowCard
                title="沪股通"
                value={summary.flow.shanghai_connect}
                subTitle="买入"
                subValue={summary.flow.shanghai_buy}
              />
              <FlowCard
                title="深股通"
                value={summary.flow.shenzhen_connect}
                subTitle="买入"
                subValue={summary.flow.shenzhen_buy}
              />
            </div>

            {/* Mini Chart */}
            {history && history.length > 0 && (
              <div className="mb-4 p-3 bg-gray-950/50 rounded border border-gray-800">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-gray-500">近期走势</span>
                  <span className="text-[10px] text-gray-500">
                    累计: <span className={summary.flow.cumulative_net >= 0 ? 'text-red-400' : 'text-green-400'}>
                      {formatMoney(summary.flow.cumulative_net)}
                    </span>
                  </span>
                </div>
                <MiniChart data={history} />
              </div>
            )}

            {/* Tabs */}
            <div className="flex border-b border-gray-800 mb-3">
              <button
                onClick={() => setActiveTab('buys')}
                className={`flex-1 py-2 text-xs font-medium transition-colors ${
                  activeTab === 'buys'
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
                onClick={() => setActiveTab('sells')}
                className={`flex-1 py-2 text-xs font-medium transition-colors ${
                  activeTab === 'sells'
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
              {activeTab === 'buys' ? (
                summary.top_buys.length > 0 ? (
                  summary.top_buys.slice(0, 8).map((stock) => (
                    <TopStockRow
                      key={stock.symbol}
                      stock={stock}
                      onClick={() => onStockClick?.(stock.symbol)}
                    />
                  ))
                ) : (
                  <div className="text-center py-4 text-gray-500 text-sm">
                    暂无数据
                  </div>
                )
              ) : (
                summary.top_sells.length > 0 ? (
                  summary.top_sells.slice(0, 8).map((stock) => (
                    <TopStockRow
                      key={stock.symbol}
                      stock={stock}
                      onClick={() => onStockClick?.(stock.symbol)}
                    />
                  ))
                ) : (
                  <div className="text-center py-4 text-gray-500 text-sm">
                    暂无数据
                  </div>
                )
              )}
            </div>

            {/* Timestamp */}
            <div className="text-[10px] text-gray-500 text-right mt-3">
              数据日期: {summary.date}
            </div>
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

export default NorthMoneyPanel;
