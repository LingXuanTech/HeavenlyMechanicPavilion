import React, { useState } from 'react';
import { AgentAnalysis, SignalType, Stock, StockPrice } from '../types';
import StockChart from './StockChart';
import { ArrowUp, ArrowDown, RefreshCw, Target, TrendingUp, TrendingDown, Minus, Maximize2, Calendar, Scale, Zap, BrainCircuit, ChevronDown } from 'lucide-react';
import type { AnalysisOptions } from '../services/api';

interface StockCardProps {
  stock: Stock;
  priceData?: StockPrice;
  analysis?: AgentAnalysis;
  onRefresh: (symbol: string, name: string, options?: AnalysisOptions) => void;
  isAnalyzing: boolean;
  currentStage?: string;
  onDelete: (symbol: string) => void;
  onClick: (stock: Stock) => void;
}

const getSignalColor = (signal: SignalType) => {
  switch (signal) {
    case SignalType.STRONG_BUY: return 'text-green-400 border-green-500';
    case SignalType.BUY: return 'text-green-400 border-green-500/50';
    case SignalType.STRONG_SELL: return 'text-red-500 border-red-500';
    case SignalType.SELL: return 'text-red-400 border-red-500/50';
    default: return 'text-yellow-400 border-yellow-500/50';
  }
};

const getTrendIcon = (trend: string) => {
  if (trend === 'Bullish') return <TrendingUp className="w-4 h-4 text-green-400" />;
  if (trend === 'Bearish') return <TrendingDown className="w-4 h-4 text-red-400" />;
  return <Minus className="w-4 h-4 text-yellow-400" />;
};

const StockCard: React.FC<StockCardProps> = ({ stock, priceData, analysis, onRefresh, isAnalyzing, currentStage, onDelete, onClick }) => {
  const isUp = priceData && priceData.change >= 0;
  const chartColor = isUp ? '#10B981' : '#EF4444';

  // Analysis level state
  const [showLevelMenu, setShowLevelMenu] = useState(false);

  const handleRefresh = (e: React.MouseEvent, level: 'L1' | 'L2' = 'L2') => {
    e.stopPropagation();
    setShowLevelMenu(false);
    onRefresh(stock.symbol, stock.name, { analysisLevel: level });
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete(stock.symbol);
  };

  const handleToggleLevelMenu = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowLevelMenu(!showLevelMenu);
  };

  return (
    <div 
      onClick={() => onClick(stock)}
      className="bg-gray-900 border border-gray-800 rounded-lg p-4 flex flex-col gap-4 hover:border-blue-500/50 hover:bg-gray-900/80 transition-all shadow-lg relative group cursor-pointer"
    >
      {/* Hover Expand Icon */}
      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <Maximize2 className="w-4 h-4 text-gray-500" />
      </div>

      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-xl font-bold text-white tracking-wider">{stock.symbol}</h3>
            <span className="text-xs font-mono text-gray-400 bg-gray-800 px-1.5 py-0.5 rounded">{stock.market}</span>
          </div>
          <p className="text-xs text-gray-500 truncate max-w-[150px]">{stock.name}</p>
        </div>
        
        <div className="text-right pr-6"> {/* pr-6 to avoid overlap with maximize icon */}
          {priceData ? (
            <>
              <div className="text-xl font-mono text-white">{priceData.price.toFixed(2)}</div>
              <div className={`text-xs font-bold flex items-center justify-end ${isUp ? 'text-green-400' : 'text-red-400'}`}>
                {isUp ? <ArrowUp className="w-3 h-3 mr-1" /> : <ArrowDown className="w-3 h-3 mr-1" />}
                {Math.abs(priceData.changePercent).toFixed(2)}%
              </div>
            </>
          ) : (
            <div className="animate-pulse h-8 w-16 bg-gray-800 rounded"></div>
          )}
        </div>
      </div>

      {/* Chart */}
      <div className="h-16 -mx-2 pointer-events-none">
        {priceData && <StockChart data={priceData.history} color={chartColor} />}
      </div>

      {/* Agent Analysis Section */}
      <div className="flex-1 bg-gray-950/50 rounded p-3 border border-gray-800/50 flex flex-col gap-2">
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-400 uppercase font-semibold flex items-center gap-1">
            <Target className="w-3 h-3" /> Agent Signal
          </span>
          {analysis && (
             <span className="text-xs text-gray-500">{analysis.timestamp}</span>
          )}
        </div>

        {isAnalyzing && !analysis ? (
          <div className="flex flex-col items-center justify-center py-4 gap-2 text-sm text-blue-400 animate-pulse">
            <div className="flex items-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin" /> Analyzing...
            </div>
            {currentStage && (
              <span className="text-[10px] text-blue-300/70 uppercase font-bold tracking-widest mt-1">
                {currentStage.replace('stage_', '')}
              </span>
            )}
          </div>
        ) : analysis ? (
          <>
            <div className={`flex items-center justify-between border-l-4 pl-2 py-1 ${getSignalColor(analysis.signal)} bg-gray-900/50`}>
              <span className="font-bold text-lg">{analysis.signal}</span>
              <span className="text-xs font-mono bg-gray-800 px-2 py-1 rounded text-white">{analysis.confidence}% Conf.</span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs mt-1">
              <div className="flex flex-col">
                <span className="text-gray-500">Take Profit</span>
                <span className="text-green-400 font-mono">{analysis.tradeSetup ? analysis.tradeSetup.targetPrice : 'N/A'}</span>
              </div>
              <div className="flex flex-col text-right">
                <span className="text-gray-500">Stop Loss</span>
                <span className="text-red-400 font-mono">{analysis.tradeSetup ? analysis.tradeSetup.stopLossPrice : 'N/A'}</span>
              </div>
            </div>

            {analysis.tradeSetup && (
               <div className="flex justify-between items-center bg-gray-900/80 p-2 rounded mt-2 border border-dashed border-gray-700/50 hover:border-blue-500/30 transition-colors">
                  <div className="flex flex-col">
                     <span className="text-[9px] text-gray-500 uppercase">Entry Zone</span>
                     <span className="text-xs text-blue-300 font-mono">{analysis.tradeSetup.entryZone}</span>
                  </div>
                  <div className="flex items-center gap-1 text-[10px] font-bold text-green-400 bg-green-900/20 border border-green-900/50 px-1.5 py-0.5 rounded">
                    <Scale className="w-3 h-3" />
                    {analysis.tradeSetup.rewardToRiskRatio}R
                  </div>
               </div>
            )}
            
            <div className="mt-2 pt-2 border-t border-gray-800">
               <div className="flex gap-2 items-center mb-1">
                 <span className="text-xs text-gray-400">Indicators:</span>
                 <div className="flex gap-2">
                   <span className="text-[10px] bg-gray-800 px-1 rounded text-gray-300">RSI: {analysis.technicalIndicators.rsi}</span>
                   <span className="text-[10px] bg-gray-800 px-1 rounded text-gray-300 flex items-center gap-1">
                     Trend: {getTrendIcon(analysis.technicalIndicators.trend)}
                   </span>
                 </div>
               </div>
               
               {analysis.catalysts && analysis.catalysts.length > 0 && (
                 <div className="flex items-center gap-1 mb-1 text-[10px] text-blue-400 font-bold">
                   <Calendar className="w-3 h-3" />
                   {analysis.catalysts[0].name} ({analysis.catalysts[0].date})
                 </div>
               )}

               {/* Use structured news if available */}
               <p className="text-xs text-gray-400 line-clamp-2 leading-relaxed opacity-80">
                  {analysis.newsAnalysis && analysis.newsAnalysis.length > 0 
                    ? analysis.newsAnalysis[0].headline 
                    : 'No news available'
                  }
               </p>
            </div>
          </>
        ) : (
          <div className="text-center py-4 text-xs text-gray-600">
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
              className="flex-1 bg-gray-800 hover:bg-gray-700 text-white text-xs py-2 rounded-l flex items-center justify-center gap-2 transition-colors disabled:opacity-50 z-10"
            >
              <RefreshCw className={`w-3 h-3 ${isAnalyzing ? 'animate-spin' : ''}`} />
              {isAnalyzing ? 'Running...' : 'Run Agent'}
            </button>

            {/* Dropdown trigger */}
            <button
              onClick={handleToggleLevelMenu}
              disabled={isAnalyzing}
              className="px-2 bg-gray-800 hover:bg-gray-700 text-gray-400 border-l border-gray-700 rounded-r transition-colors disabled:opacity-50 z-10"
              title="选择分析级别"
            >
              <ChevronDown className={`w-3 h-3 transition-transform ${showLevelMenu ? 'rotate-180' : ''}`} />
            </button>
          </div>

          {/* Dropdown menu */}
          {showLevelMenu && !isAnalyzing && (
            <div className="absolute bottom-full left-0 right-8 mb-1 bg-gray-900 border border-gray-700 rounded-lg shadow-xl overflow-hidden z-20 animate-in fade-in slide-in-from-bottom-1 duration-150">
              <button
                onClick={(e) => handleRefresh(e, 'L1')}
                className="w-full px-3 py-2 text-left hover:bg-gray-800 transition-colors flex items-center gap-2"
              >
                <Zap className="w-4 h-4 text-yellow-400" />
                <div className="flex-1">
                  <div className="text-xs font-medium text-white">快速扫描 (L1)</div>
                  <div className="text-[10px] text-gray-500">Market + News + Macro，~15秒</div>
                </div>
              </button>
              <button
                onClick={(e) => handleRefresh(e, 'L2')}
                className="w-full px-3 py-2 text-left hover:bg-gray-800 transition-colors flex items-center gap-2 border-t border-gray-700"
              >
                <BrainCircuit className="w-4 h-4 text-blue-400" />
                <div className="flex-1">
                  <div className="text-xs font-medium text-white">完整分析 (L2)</div>
                  <div className="text-[10px] text-gray-500">全部分析师 + 辩论，~60秒</div>
                </div>
              </button>
            </div>
          )}
        </div>

        <button
          onClick={handleDelete}
          className="px-3 bg-gray-800 hover:bg-red-900/30 text-gray-400 hover:text-red-400 rounded transition-colors z-10"
        >
          <Minus className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
};

export default StockCard;