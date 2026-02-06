import React, { useState, useCallback, memo } from 'react';
import type * as T from '../src/types/schema';
import { AnalysisProgressBar } from './AnalysisProgressBar';
import { ArrowUp, ArrowDown, RefreshCw, Target, TrendingUp, TrendingDown, Minus, Maximize2, Zap, BrainCircuit, ChevronDown } from 'lucide-react';
import type { AnalysisOptions } from '../services/api';

interface StockCardProps {
  stock: T.AssetPrice;
  priceData?: T.StockPrice;
  analysis?: T.AgentAnalysisResponse;
  onRefresh: (symbol: string, name: string, options?: AnalysisOptions) => void;
  isAnalyzing: boolean;
  currentStage?: string;
  onDelete: (symbol: string) => void;
  onClick: (stock: T.AssetPrice) => void;
}

const getSignalColor = (signal: string | T.SignalType) => {
  switch (signal) {
    case 'Strong Buy':
      return 'text-green-400 border-green-500';
    case 'Buy':
      return 'text-green-400 border-green-500/50';
    case 'Strong Sell':
      return 'text-red-500 border-red-500';
    case 'Sell':
      return 'text-red-400 border-red-500/50';
    default:
      return 'text-yellow-400 border-yellow-500/50';
  }
};

const getTrendIcon = (trend: string) => {
  if (trend === 'Bullish') return <TrendingUp className="w-4 h-4 text-green-400" />;
  if (trend === 'Bearish') return <TrendingDown className="w-4 h-4 text-red-400" />;
  return <Minus className="w-4 h-4 text-yellow-400" />;
};

const StockCardComponent: React.FC<StockCardProps> = ({ stock, priceData, analysis, onRefresh, isAnalyzing, currentStage, onDelete, onClick }) => {
  const isUp = priceData && priceData.change >= 0;

  // Analysis level state
  const [showLevelMenu, setShowLevelMenu] = useState(false);

  const handleRefresh = useCallback((e: React.MouseEvent, level: 'L1' | 'L2' = 'L2') => {
    e.stopPropagation();
    setShowLevelMenu(false);
    onRefresh(stock.symbol, stock.name, { analysisLevel: level });
  }, [stock.symbol, stock.name, onRefresh]);

  const handleDelete = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete(stock.symbol);
  }, [stock.symbol, onDelete]);

  const handleToggleLevelMenu = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setShowLevelMenu(prev => !prev);
  }, []);

  const handleCardClick = useCallback(() => {
    onClick(stock);
  }, [stock, onClick]);

  return (
    <div
      onClick={handleCardClick}
      className="bg-surface-raised border border-border rounded-lg p-4 flex flex-col gap-4 hover:border-accent/50 hover:bg-surface-raised/80 transition-all shadow-lg relative group cursor-pointer"
    >
      {/* Hover Expand Icon */}
      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <Maximize2 className="w-4 h-4 text-stone-500" />
      </div>

      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-xl font-bold text-white tracking-wider">{stock.symbol}</h3>
            <span className="text-xs font-mono text-stone-400 bg-surface-overlay px-1.5 py-0.5 rounded">
              {priceData?.market || 'N/A'}
            </span>
          </div>
          <p className="text-xs text-stone-500 truncate max-w-[150px]">{stock.name}</p>
        </div>

        <div className="text-right pr-6">
          {/* pr-6 to avoid overlap with maximize icon */}
          {priceData ? (
            <>
              <div className="text-xl font-mono text-white">{priceData.price.toFixed(2)}</div>
              <div
                className={`text-xs font-bold flex items-center justify-end ${
                  isUp ? 'text-green-400' : 'text-red-400'
                }`}
              >
                {isUp ? <ArrowUp className="w-3 h-3 mr-1" /> : <ArrowDown className="w-3 h-3 mr-1" />}
                {Math.abs(priceData.change_percent).toFixed(2)}%
              </div>
            </>
          ) : (
            <div className="animate-pulse h-8 w-16 bg-surface-overlay rounded"></div>
          )}
        </div>
      </div>

      {/* Chart Placeholder */}
      <div className="h-16 -mx-2 pointer-events-none">
        {priceData && <div className="h-full w-full bg-surface-overlay/20 rounded" />}
      </div>

      {/* Agent Analysis Section */}
      <div className="flex-1 bg-surface/50 rounded p-3 border border-border/50 flex flex-col gap-2">
        <div className="flex justify-between items-center">
          <span className="text-xs text-stone-400 uppercase font-semibold flex items-center gap-1">
            <Target className="w-3 h-3" /> Agent Signal
          </span>
          {analysis && <span className="text-xs text-stone-500">{analysis.created_at}</span>}
        </div>

        {isAnalyzing && !analysis ? (
          <div className="flex flex-col gap-2 py-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-accent font-medium flex items-center gap-1.5">
                <RefreshCw className="w-3 h-3 animate-spin" />
                分析中
              </span>
            </div>
            <AnalysisProgressBar currentStage={currentStage || 'starting'} compact />
          </div>
        ) : analysis ? (
          <>
            <div
              className={`flex items-center justify-between border-l-4 pl-2 py-1 ${getSignalColor(
                analysis.full_report.signal
              )} bg-surface-raised/50`}
            >
              <span className="font-bold text-lg">{analysis.full_report.signal}</span>
              <span className="text-xs font-mono bg-surface-overlay px-2 py-1 rounded text-white">
                {analysis.full_report.confidence}% Conf.
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs mt-1">
              <div className="flex flex-col">
                <span className="text-stone-500">Signal</span>
                <span className="text-green-400 font-mono">{analysis.signal}</span>
              </div>
              <div className="flex flex-col text-right">
                <span className="text-stone-500">Confidence</span>
                <span className="text-accent font-mono">{analysis.confidence}%</span>
              </div>
            </div>

            <div className="mt-2 pt-2 border-t border-border">
              <div className="flex gap-2 items-center mb-1">
                <span className="text-xs text-stone-400">Indicators:</span>
                <div className="flex gap-2">
                  {analysis.full_report.technical_indicators && (
                    <>
                      <span className="text-[10px] bg-surface-overlay px-1 rounded text-stone-300">
                        RSI: {analysis.full_report.technical_indicators.rsi}
                      </span>
                      <span className="text-[10px] bg-surface-overlay px-1 rounded text-stone-300 flex items-center gap-1">
                        Trend: {getTrendIcon(analysis.full_report.technical_indicators.trend)}
                      </span>
                    </>
                  )}
                </div>
              </div>

              {/* Use structured news if available */}
              <p className="text-xs text-stone-400 line-clamp-2 leading-relaxed opacity-80">
                {analysis.full_report.news_analysis && analysis.full_report.news_analysis.length > 0
                  ? analysis.full_report.news_analysis[0].headline
                  : 'No news available'}
              </p>
            </div>
          </>
        ) : (
          <div className="text-center py-4 text-xs text-stone-600">
            Waiting for agent analysis...
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-2 mt-auto pt-2">
        {/* Analysis Level Dropdown */}
        <div className="relative flex-1">
          <div className="flex">
            {/* Main button - defaults to L2 Full Analysis */}
            <button
              onClick={(e) => handleRefresh(e, 'L2')}
              disabled={isAnalyzing}
              className="flex-1 bg-surface-overlay hover:bg-surface-muted text-white text-xs py-2 rounded-l flex items-center justify-center gap-2 transition-colors disabled:opacity-50 z-10"
            >
              <RefreshCw className={`w-3 h-3 ${isAnalyzing ? 'animate-spin' : ''}`} />
              {isAnalyzing ? 'Running...' : 'Run Agent'}
            </button>

            {/* Dropdown trigger */}
            <button
              onClick={handleToggleLevelMenu}
              disabled={isAnalyzing}
              className="px-2 bg-surface-overlay hover:bg-surface-muted text-stone-400 border-l border-border-strong rounded-r transition-colors disabled:opacity-50 z-10"
              title="选择分析级别"
            >
              <ChevronDown className={`w-3 h-3 transition-transform ${showLevelMenu ? 'rotate-180' : ''}`} />
            </button>
          </div>

          {/* Dropdown menu */}
          {showLevelMenu && !isAnalyzing && (
            <div className="absolute bottom-full left-0 right-8 mb-1 bg-surface-raised border border-border-strong rounded-lg shadow-xl overflow-hidden z-20 animate-in fade-in slide-in-from-bottom-1 duration-150">
              <button
                onClick={(e) => handleRefresh(e, 'L1')}
                className="w-full px-3 py-2 text-left hover:bg-surface-overlay transition-colors flex items-center gap-2"
              >
                <Zap className="w-4 h-4 text-yellow-400" />
                <div className="flex-1">
                  <div className="text-xs font-medium text-white">快速扫描 (L1)</div>
                  <div className="text-[10px] text-stone-500">Market + News + Macro，~15秒</div>
                </div>
              </button>
              <button
                onClick={(e) => handleRefresh(e, 'L2')}
                className="w-full px-3 py-2 text-left hover:bg-surface-overlay transition-colors flex items-center gap-2 border-t border-border-strong"
              >
                <BrainCircuit className="w-4 h-4 text-accent" />
                <div className="flex-1">
                  <div className="text-xs font-medium text-white">完整分析 (L2)</div>
                  <div className="text-[10px] text-stone-500">全部分析师 + 辩论，~60秒</div>
                </div>
              </button>
            </div>
          )}
        </div>

        <button
          onClick={handleDelete}
          className="px-3 bg-surface-overlay hover:bg-red-900/30 text-stone-400 hover:text-red-400 rounded transition-colors z-10"
        >
          <Minus className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
};

// 使用 React.memo 优化，仅在关键 props 变化时重渲染
const StockCard = memo(StockCardComponent, (prevProps, nextProps) => {
  // 返回 true 表示不需要重渲染
  return (
    prevProps.stock.symbol === nextProps.stock.symbol &&
    prevProps.isAnalyzing === nextProps.isAnalyzing &&
    prevProps.currentStage === nextProps.currentStage &&
    prevProps.analysis?.created_at === nextProps.analysis?.created_at &&
    prevProps.priceData?.price === nextProps.priceData?.price &&
    prevProps.priceData?.change_percent === nextProps.priceData?.change_percent
  );
});

export default StockCard;
