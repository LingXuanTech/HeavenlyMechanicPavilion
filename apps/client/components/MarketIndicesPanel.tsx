/**
 * 市场指数面板
 *
 * 显示全球市场指数和情绪
 */
import React, { useState } from 'react';
import {
  Globe,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Activity,
  AlertTriangle,
  ChevronDown,
  Filter
} from 'lucide-react';
import { useMarketWatcherOverview, useMarketIndices, useMarketSentiment, useRefreshMarketIndices } from '../hooks';
import type * as T from '../src/types/schema';

interface MarketIndicesPanelProps {
  compact?: boolean;
}

const REGIONS: { value: T.MarketRegion | 'ALL'; label: string }[] = [
  { value: 'ALL', label: 'All' },
  { value: 'US', label: 'US' },
  { value: 'CN', label: 'China' },
  { value: 'HK', label: 'Hong Kong' },
  { value: 'GLOBAL', label: 'Global' },
];

const getSentimentColor = (sentiment: string): string => {
  const s = sentiment.toLowerCase();
  if (s.includes('bullish')) return 'text-green-400';
  if (s.includes('bearish')) return 'text-red-400';
  return 'text-yellow-400';
};

const getRiskColor = (level: number): string => {
  if (level < 30) return 'text-green-400';
  if (level < 60) return 'text-yellow-400';
  return 'text-red-400';
};

const getStatusBadge = (status: string) => {
  switch (status) {
    case 'trading':
      return <span className="text-[9px] px-1.5 py-0.5 rounded bg-green-900/30 text-green-400">LIVE</span>;
    case 'closed':
      return <span className="text-[9px] px-1.5 py-0.5 rounded bg-surface-overlay text-stone-500">CLOSED</span>;
    case 'pre_market':
      return <span className="text-[9px] px-1.5 py-0.5 rounded bg-accent/10 text-accent">PRE</span>;
    case 'after_hours':
      return <span className="text-[9px] px-1.5 py-0.5 rounded bg-purple-900/30 text-purple-400">AH</span>;
    default:
      return null;
  }
};

const IndexCard: React.FC<{ index: T.MarketIndex }> = ({ index }) => {
  const isUp = index.change_percent >= 0;

  return (
    <div className="flex items-center justify-between p-3 bg-surface/50 rounded border border-border hover:border-border-strong transition-colors">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-white truncate">{index.name}</span>
          {getStatusBadge(index.status)}
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-[10px] text-stone-500 font-mono">{index.code}</span>
          <span className="text-[10px] text-stone-600">•</span>
          <span className="text-[10px] text-stone-500">{index.region}</span>
        </div>
      </div>

      <div className="text-right">
        <div className="text-sm font-mono text-white">
          {index.current.toLocaleString(undefined, { maximumFractionDigits: 2 })}
        </div>
        <div className={`text-xs font-mono flex items-center justify-end gap-1 ${isUp ? 'text-green-400' : 'text-red-400'}`}>
          {isUp ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          {isUp ? '+' : ''}{index.change_percent.toFixed(2)}%
        </div>
      </div>
    </div>
  );
};

const MarketIndicesPanel: React.FC<MarketIndicesPanelProps> = ({ compact = false }) => {
  const [selectedRegion, setSelectedRegion] = useState<T.MarketRegion | 'ALL'>('ALL');
  const [showFilter, setShowFilter] = useState(false);

  const { data: overview, isLoading: overviewLoading } = useMarketWatcherOverview();
  const { data: _sentiment } = useMarketSentiment();
  const { data: indices, isLoading: indicesLoading, refetch } = useMarketIndices(
    selectedRegion === 'ALL' ? undefined : selectedRegion
  );
  const refreshMutation = useRefreshMarketIndices();

  const handleRefresh = () => {
    refreshMutation.mutate();
    refetch();
  };

  const isRefreshing = refreshMutation.isPending || indicesLoading;

  // 紧凑模式 - 只显示关键指数
  if (compact) {
    const keyIndices = overview?.indices?.slice(0, 4) || [];

    return (
      <div className="flex gap-4 overflow-x-auto py-2">
        {keyIndices.map((idx) => (
          <div key={idx.code} className="flex items-center gap-2 text-xs font-mono shrink-0">
            <span className="font-semibold text-stone-400">{idx.name}</span>
            <span className="text-white">{idx.current.toLocaleString()}</span>
            <span className={idx.change_percent >= 0 ? 'text-green-400' : 'text-red-400'}>
              {idx.change_percent >= 0 ? '+' : ''}{idx.change_percent.toFixed(2)}%
            </span>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="bg-surface-raised border border-border rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-surface/50 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Globe className="w-4 h-4 text-accent" />
            <span className="text-sm font-semibold text-white">Market Indices</span>
          </div>

          {/* Sentiment & Risk */}
          {overview && (
            <div className="hidden sm:flex items-center gap-3 ml-2">
              <div className="flex items-center gap-1">
                <Activity className="w-3 h-3 text-stone-500" />
                <span className={`text-xs font-medium ${getSentimentColor(overview.global_sentiment)}`}>
                  {overview.global_sentiment}
                </span>
              </div>
              <div className="flex items-center gap-1">
                <AlertTriangle className="w-3 h-3 text-stone-500" />
                <span className={`text-xs font-medium ${getRiskColor(overview.risk_level)}`}>
                  Risk: {overview.risk_level}
                </span>
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Region Filter */}
          <div className="relative">
            <button
              onClick={() => setShowFilter(!showFilter)}
              className="flex items-center gap-1 px-2 py-1 text-xs text-stone-400 hover:text-stone-50 bg-surface-overlay hover:bg-surface-muted rounded transition-colors"
            >
              <Filter className="w-3 h-3" />
              <span>{REGIONS.find(r => r.value === selectedRegion)?.label}</span>
              <ChevronDown className="w-3 h-3" />
            </button>

            {showFilter && (
              <div className="absolute right-0 top-full mt-1 bg-surface-overlay border border-border-strong rounded shadow-lg z-10">
                {REGIONS.map((region) => (
                  <button
                    key={region.value}
                    onClick={() => {
                      setSelectedRegion(region.value);
                      setShowFilter(false);
                    }}
                    className={`block w-full text-left px-3 py-1.5 text-xs hover:bg-surface-muted transition-colors ${
                      selectedRegion === region.value ? 'text-accent' : 'text-stone-300'
                    }`}
                  >
                    {region.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="p-1.5 hover:bg-surface-overlay rounded transition-colors disabled:opacity-50"
            title="刷新指数"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-stone-400 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {overviewLoading || indicesLoading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-6 h-6 text-stone-500 animate-spin" />
          </div>
        ) : indices && indices.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {indices.map((index) => (
              <IndexCard key={index.code} index={index} />
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-stone-500">
            <Globe className="w-8 h-8 mb-2 opacity-50" />
            <p className="text-sm">No market data available</p>
          </div>
        )}

        {/* Timestamp */}
        {overview && (
          <div className="text-[10px] text-stone-500 text-right mt-3">
            Updated: {new Date(overview.updated_at).toLocaleTimeString()}
          </div>
        )}
      </div>
    </div>
  );
};

export default MarketIndicesPanel;
