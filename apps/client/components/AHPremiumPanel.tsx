/**
 * AH 溢价面板组件
 *
 * 展示 AH 股溢价排行榜，支持排序和详情查看。
 */

import React, { useState } from 'react';
import { useAHPremiumList, useAHPremiumDetail } from '../hooks/useAlternativeData';
import type { AHPremiumStock } from '../hooks/useAlternativeData';
import { ArrowUpDown, TrendingUp, TrendingDown, Minus, RefreshCw, ChevronRight, X } from 'lucide-react';

interface AHPremiumPanelProps {
  className?: string;
}

const AHPremiumPanel: React.FC<AHPremiumPanelProps> = ({ className = '' }) => {
  const [sortBy, setSortBy] = useState('premium_rate');
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);

  const { data, isLoading, error, refetch } = useAHPremiumList(sortBy, 30);
  const { data: detail, isLoading: detailLoading } = useAHPremiumDetail(selectedSymbol || '');

  if (error) {
    return (
      <div className={`bg-surface-raised rounded-lg p-4 ${className}`}>
        <div className="text-red-400 text-sm">AH 溢价数据加载失败: {(error as Error).message}</div>
      </div>
    );
  }

  return (
    <div className={`bg-surface-raised rounded-lg ${className}`}>
      {/* 头部 */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <ArrowUpDown className="w-5 h-5 text-accent" />
          <h3 className="text-white font-medium">AH 溢价排行</h3>
          {data?.stats && (
            <span className="text-xs text-stone-400 ml-2">
              均值 {data.stats.avg_premium_pct}% | 共 {data.stats.total_count} 只
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="bg-surface-overlay text-stone-300 text-xs rounded px-2 py-1 border border-border-strong"
          >
            <option value="premium_rate">按溢价率</option>
            <option value="a_price">按 A 股价格</option>
          </select>
          <button
            onClick={() => refetch()}
            className="p-1 text-stone-400 hover:text-stone-50 transition-colors"
            title="刷新"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* 统计摘要 */}
      {data?.stats && (
        <div className="grid grid-cols-4 gap-2 p-3 border-b border-border">
          <StatCard label="平均溢价" value={`${data.stats.avg_premium_pct}%`} />
          <StatCard label="最高溢价" value={`${data.stats.max_premium_pct}%`} color="text-red-400" />
          <StatCard label="最低溢价" value={`${data.stats.min_premium_pct}%`} color="text-green-400" />
          <StatCard label="折价数量" value={`${data.stats.discount_count}`} color="text-cyan-400" />
        </div>
      )}

      {/* 列表 */}
      <div className="overflow-y-auto max-h-96">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-5 h-5 text-stone-500 animate-spin" />
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-stone-500 text-xs sticky top-0 bg-surface-raised">
              <tr>
                <th className="text-left px-3 py-2">名称</th>
                <th className="text-right px-3 py-2">A 股价</th>
                <th className="text-right px-3 py-2">H 股价</th>
                <th className="text-right px-3 py-2">溢价率</th>
                <th className="text-right px-3 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {data?.stocks?.map((stock) => (
                <StockRow
                  key={stock.a_code}
                  stock={stock}
                  onSelect={() => setSelectedSymbol(stock.a_code)}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* 详情弹窗 */}
      {selectedSymbol && (
        <DetailPanel
          symbol={selectedSymbol}
          detail={detail}
          loading={detailLoading}
          onClose={() => setSelectedSymbol(null)}
        />
      )}
    </div>
  );
};

// ============ 子组件 ============

const StatCard: React.FC<{ label: string; value: string; color?: string }> = ({
  label,
  value,
  color = 'text-white',
}) => (
  <div className="text-center">
    <div className="text-xs text-stone-500">{label}</div>
    <div className={`text-sm font-medium ${color}`}>{value}</div>
  </div>
);

const StockRow: React.FC<{ stock: AHPremiumStock; onSelect: () => void }> = ({ stock, onSelect }) => {
  const premiumColor =
    stock.premium_pct > 50
      ? 'text-red-400'
      : stock.premium_pct > 0
        ? 'text-yellow-400'
        : 'text-green-400';

  const PremiumIcon =
    stock.premium_pct > 20 ? TrendingUp : stock.premium_pct < -10 ? TrendingDown : Minus;

  return (
    <tr
      className="border-t border-border/50 hover:bg-surface-overlay/50 cursor-pointer transition-colors"
      onClick={onSelect}
    >
      <td className="px-3 py-2">
        <div className="text-white text-xs font-medium">{stock.name}</div>
        <div className="text-stone-500 text-xs">
          A:{stock.a_code} / H:{stock.h_code}
        </div>
      </td>
      <td className="text-right px-3 py-2 text-stone-300 text-xs">{stock.a_price.toFixed(2)}</td>
      <td className="text-right px-3 py-2 text-stone-300 text-xs">{stock.h_price.toFixed(2)}</td>
      <td className="text-right px-3 py-2">
        <div className={`flex items-center justify-end gap-1 ${premiumColor}`}>
          <PremiumIcon className="w-3 h-3" />
          <span className="text-xs font-medium">{stock.premium_pct.toFixed(1)}%</span>
        </div>
      </td>
      <td className="text-right px-3 py-2">
        <ChevronRight className="w-3 h-3 text-stone-600" />
      </td>
    </tr>
  );
};

const DetailPanel: React.FC<{
  symbol: string;
  detail: ReturnType<typeof useAHPremiumDetail>['data'];
  loading: boolean;
  onClose: () => void;
}> = ({ symbol, detail, loading, onClose }) => (
  <div className="border-t border-border-strong p-4">
    <div className="flex items-center justify-between mb-3">
      <h4 className="text-white text-sm font-medium">
        {detail?.current?.name || symbol} 溢价详情
      </h4>
      <button onClick={onClose} className="text-stone-400 hover:text-stone-50">
        <X className="w-4 h-4" />
      </button>
    </div>

    {loading ? (
      <div className="flex items-center justify-center py-4">
        <RefreshCw className="w-4 h-4 text-stone-500 animate-spin" />
      </div>
    ) : detail?.signal ? (
      <div className="space-y-2">
        <div
          className={`px-3 py-2 rounded text-xs ${
            detail.signal.signal.includes('BUY')
              ? 'bg-green-900/30 text-green-400'
              : detail.signal.signal.includes('SELL')
                ? 'bg-red-900/30 text-red-400'
                : 'bg-surface-overlay text-stone-400'
          }`}
        >
          <div className="font-medium">{detail.signal.signal}</div>
          <div className="mt-1">{detail.signal.description}</div>
          {detail.signal.percentile !== undefined && (
            <div className="mt-1">历史分位: {detail.signal.percentile}%</div>
          )}
        </div>

        {/* 简易历史图表（文字版） */}
        {detail.history && detail.history.length > 0 && (
          <div className="text-xs text-stone-500">
            近 {detail.history.length} 日溢价比范围:{' '}
            {Math.min(...detail.history.map((h) => h.ratio)).toFixed(2)} ~{' '}
            {Math.max(...detail.history.map((h) => h.ratio)).toFixed(2)}
          </div>
        )}
      </div>
    ) : (
      <div className="text-stone-500 text-xs">暂无详情数据</div>
    )}
  </div>
);

export default AHPremiumPanel;
