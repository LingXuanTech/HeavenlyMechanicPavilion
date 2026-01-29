/**
 * A 股市场综合面板
 *
 * 整合北向资金、龙虎榜、限售解禁三大 A 股特色功能
 */
import React, { useState } from 'react';
import {
  DollarSign,
  Trophy,
  Unlock,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Building2,
  Users,
  AlertTriangle,
  Calendar,
  ChevronRight,
} from 'lucide-react';
import {
  useNorthMoneySummary,
  useLHBSummary,
  useJiejinSummary,
} from '../hooks';
import type {
  NorthMoneySummary,
  LHBSummary,
  LHBStock,
  HotMoneySeat,
  JiejinSummary,
  JiejinStock,
} from '../types';

interface ChinaMarketPanelProps {
  onStockClick?: (symbol: string) => void;
}

type TabType = 'north' | 'lhb' | 'jiejin';

const TABS: { id: TabType; label: string; icon: React.ReactNode }[] = [
  { id: 'north', label: '北向资金', icon: <DollarSign className="w-3.5 h-3.5" /> },
  { id: 'lhb', label: '龙虎榜', icon: <Trophy className="w-3.5 h-3.5" /> },
  { id: 'jiejin', label: '限售解禁', icon: <Unlock className="w-3.5 h-3.5" /> },
];

const formatMoney = (value: number): string => {
  const abs = Math.abs(value);
  if (abs >= 100) {
    return `${value >= 0 ? '+' : ''}${value.toFixed(0)}亿`;
  }
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}亿`;
};

// ============ 北向资金内容 ============
const NorthMoneyContent: React.FC<{
  data: NorthMoneySummary;
  onStockClick?: (symbol: string) => void;
}> = ({ data, onStockClick }) => {
  const isInflow = data.trend === 'Inflow';

  return (
    <div className="space-y-4">
      {/* 汇总数据 */}
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-gray-950/50 rounded p-2.5 border border-gray-800">
          <div className="text-[10px] text-gray-500">今日合计</div>
          <div className={`text-base font-mono font-bold ${data.flow.total_net >= 0 ? 'text-red-400' : 'text-green-400'}`}>
            {formatMoney(data.flow.total_net)}
          </div>
        </div>
        <div className="bg-gray-950/50 rounded p-2.5 border border-gray-800">
          <div className="text-[10px] text-gray-500">沪股通</div>
          <div className={`text-base font-mono font-bold ${data.flow.shanghai_connect >= 0 ? 'text-red-400' : 'text-green-400'}`}>
            {formatMoney(data.flow.shanghai_connect)}
          </div>
        </div>
        <div className="bg-gray-950/50 rounded p-2.5 border border-gray-800">
          <div className="text-[10px] text-gray-500">深股通</div>
          <div className={`text-base font-mono font-bold ${data.flow.shenzhen_connect >= 0 ? 'text-red-400' : 'text-green-400'}`}>
            {formatMoney(data.flow.shenzhen_connect)}
          </div>
        </div>
      </div>

      {/* 趋势 */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-950/30 rounded border border-gray-800">
        <span className="text-xs text-gray-400">资金趋势</span>
        <span className={`text-xs font-medium ${isInflow ? 'text-red-400' : 'text-green-400'}`}>
          连续{data.trend_days}日{isInflow ? '净流入' : '净流出'}
        </span>
      </div>

      {/* TOP 股票 */}
      <div>
        <div className="flex items-center gap-1 text-xs text-gray-500 mb-2">
          <TrendingUp className="w-3 h-3 text-red-400" />
          <span>净买入 TOP</span>
        </div>
        <div className="space-y-1">
          {data.top_buys.slice(0, 5).map((stock) => (
            <div
              key={stock.symbol}
              className="flex items-center justify-between py-1.5 px-2 bg-gray-950/30 rounded hover:bg-gray-800/30 cursor-pointer transition-colors"
              onClick={() => onStockClick?.(stock.symbol)}
            >
              <div className="flex items-center gap-2">
                <span className="text-xs text-white">{stock.name}</span>
                <span className="text-[10px] text-gray-500">{stock.holding_ratio.toFixed(1)}%</span>
              </div>
              <span className="text-xs font-mono text-red-400">{formatMoney(stock.net_buy)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ============ 龙虎榜内容 ============
const LHBContent: React.FC<{
  data: LHBSummary;
  onStockClick?: (symbol: string) => void;
}> = ({ data, onStockClick }) => {
  return (
    <div className="space-y-4">
      {/* 汇总数据 */}
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-gray-950/50 rounded p-2.5 border border-gray-800">
          <div className="text-[10px] text-gray-500">上榜股票</div>
          <div className="text-base font-mono font-bold text-white">{data.total_stocks}</div>
        </div>
        <div className="bg-gray-950/50 rounded p-2.5 border border-gray-800">
          <div className="text-[10px] text-gray-500">市场净买</div>
          <div className={`text-base font-mono font-bold ${data.total_net_buy >= 0 ? 'text-red-400' : 'text-green-400'}`}>
            {formatMoney(data.total_net_buy)}
          </div>
        </div>
        <div className="bg-gray-950/50 rounded p-2.5 border border-gray-800">
          <div className="text-[10px] text-gray-500">机构净买</div>
          <div className={`text-base font-mono font-bold ${data.institution_net_buy >= 0 ? 'text-red-400' : 'text-green-400'}`}>
            {formatMoney(data.institution_net_buy)}
          </div>
        </div>
      </div>

      {/* 活跃游资 */}
      {data.hot_money_active.length > 0 && (
        <div>
          <div className="flex items-center gap-1 text-xs text-gray-500 mb-2">
            <Users className="w-3 h-3 text-yellow-400" />
            <span>活跃游资</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {data.hot_money_active.slice(0, 5).map((seat) => (
              <span
                key={seat.alias}
                className="px-2 py-0.5 text-[10px] bg-yellow-900/20 text-yellow-400 rounded border border-yellow-800/30"
              >
                {seat.alias}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 净买入 TOP */}
      <div>
        <div className="flex items-center gap-1 text-xs text-gray-500 mb-2">
          <TrendingUp className="w-3 h-3 text-red-400" />
          <span>净买入 TOP</span>
        </div>
        <div className="space-y-1">
          {data.top_buys.slice(0, 5).map((stock) => (
            <div
              key={stock.symbol}
              className="flex items-center justify-between py-1.5 px-2 bg-gray-950/30 rounded hover:bg-gray-800/30 cursor-pointer transition-colors"
              onClick={() => onStockClick?.(stock.symbol)}
            >
              <div className="flex items-center gap-2">
                <span className="text-xs text-white">{stock.name}</span>
                {stock.hot_money_involved && (
                  <span className="text-[9px] px-1 py-0.5 bg-yellow-900/30 text-yellow-400 rounded">游资</span>
                )}
                {stock.institution_net > 0 && (
                  <span className="text-[9px] px-1 py-0.5 bg-blue-900/30 text-blue-400 rounded">机构</span>
                )}
              </div>
              <div className="text-right">
                <span className="text-xs font-mono text-red-400">{formatMoney(stock.lhb_net_buy)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ============ 限售解禁内容 ============
const JiejinContent: React.FC<{
  data: JiejinSummary;
  onStockClick?: (symbol: string) => void;
}> = ({ data, onStockClick }) => {
  return (
    <div className="space-y-4">
      {/* 汇总数据 */}
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-gray-950/50 rounded p-2.5 border border-gray-800">
          <div className="text-[10px] text-gray-500">涉及股票</div>
          <div className="text-base font-mono font-bold text-white">{data.total_stocks}</div>
        </div>
        <div className="bg-gray-950/50 rounded p-2.5 border border-gray-800">
          <div className="text-[10px] text-gray-500">总解禁市值</div>
          <div className="text-base font-mono font-bold text-orange-400">
            {data.total_market_value.toFixed(0)}亿
          </div>
        </div>
        <div className="bg-gray-950/50 rounded p-2.5 border border-gray-800">
          <div className="text-[10px] text-gray-500">日均解禁</div>
          <div className="text-base font-mono font-bold text-gray-300">
            {data.daily_average.toFixed(1)}亿
          </div>
        </div>
      </div>

      {/* 统计周期 */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-950/30 rounded border border-gray-800">
        <span className="text-xs text-gray-400">统计周期</span>
        <span className="text-xs text-gray-300">{data.date_range}</span>
      </div>

      {/* 高压力股票 */}
      {data.high_pressure_stocks.length > 0 && (
        <div>
          <div className="flex items-center gap-1 text-xs text-gray-500 mb-2">
            <AlertTriangle className="w-3 h-3 text-orange-400" />
            <span>高解禁压力</span>
          </div>
          <div className="space-y-1">
            {data.high_pressure_stocks.slice(0, 5).map((stock) => (
              <div
                key={`${stock.symbol}-${stock.jiejin_date}`}
                className="flex items-center justify-between py-1.5 px-2 bg-gray-950/30 rounded hover:bg-gray-800/30 cursor-pointer transition-colors"
                onClick={() => onStockClick?.(stock.symbol)}
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs text-white">{stock.name}</span>
                  <span className="text-[10px] text-gray-500">
                    {new Date(stock.jiejin_date).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-orange-400">
                    {stock.jiejin_market_value.toFixed(1)}亿
                  </span>
                  <span className={`text-[9px] px-1 py-0.5 rounded ${
                    stock.pressure_level === '高'
                      ? 'bg-red-900/30 text-red-400'
                      : stock.pressure_level === '中'
                      ? 'bg-yellow-900/30 text-yellow-400'
                      : 'bg-gray-800 text-gray-400'
                  }`}>
                    {stock.jiejin_ratio.toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 近期解禁日历 */}
      {data.calendar.length > 0 && (
        <div>
          <div className="flex items-center gap-1 text-xs text-gray-500 mb-2">
            <Calendar className="w-3 h-3 text-blue-400" />
            <span>近期解禁日历</span>
          </div>
          <div className="space-y-1">
            {data.calendar.slice(0, 3).map((day) => (
              <div
                key={day.date}
                className="flex items-center justify-between py-1.5 px-2 bg-gray-950/30 rounded"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-300">
                    {new Date(day.date).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })}
                  </span>
                  <span className="text-[10px] text-gray-500">{day.stock_count}只</span>
                </div>
                <span className="text-xs font-mono text-orange-400">
                  {day.total_market_value.toFixed(1)}亿
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// ============ 主组件 ============
const ChinaMarketPanel: React.FC<ChinaMarketPanelProps> = ({ onStockClick }) => {
  const [activeTab, setActiveTab] = useState<TabType>('north');

  const { data: northData, isLoading: northLoading, refetch: refetchNorth } = useNorthMoneySummary();
  const { data: lhbData, isLoading: lhbLoading, refetch: refetchLhb } = useLHBSummary();
  const { data: jiejinData, isLoading: jiejinLoading, refetch: refetchJiejin } = useJiejinSummary(30);

  const isLoading = activeTab === 'north' ? northLoading : activeTab === 'lhb' ? lhbLoading : jiejinLoading;

  const handleRefresh = () => {
    if (activeTab === 'north') refetchNorth();
    else if (activeTab === 'lhb') refetchLhb();
    else refetchJiejin();
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
      {/* Header with Tabs */}
      <div className="flex items-center justify-between px-2 py-2 bg-gray-950/50 border-b border-gray-800">
        <div className="flex">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                activeTab === tab.id
                  ? 'bg-gray-800 text-white'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800/50'
              }`}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        <button
          onClick={handleRefresh}
          disabled={isLoading}
          className="p-1.5 hover:bg-gray-800 rounded transition-colors disabled:opacity-50"
          title="刷新数据"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-gray-400 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Content */}
      <div className="p-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-6 h-6 text-gray-500 animate-spin" />
          </div>
        ) : (
          <>
            {activeTab === 'north' && northData && (
              <NorthMoneyContent data={northData} onStockClick={onStockClick} />
            )}
            {activeTab === 'lhb' && lhbData && (
              <LHBContent data={lhbData} onStockClick={onStockClick} />
            )}
            {activeTab === 'jiejin' && jiejinData && (
              <JiejinContent data={jiejinData} onStockClick={onStockClick} />
            )}

            {!northData && activeTab === 'north' && (
              <div className="text-center py-8 text-gray-500 text-sm">无法获取北向资金数据</div>
            )}
            {!lhbData && activeTab === 'lhb' && (
              <div className="text-center py-8 text-gray-500 text-sm">无法获取龙虎榜数据</div>
            )}
            {!jiejinData && activeTab === 'jiejin' && (
              <div className="text-center py-8 text-gray-500 text-sm">无法获取解禁数据</div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default ChinaMarketPanel;
