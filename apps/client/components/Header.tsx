import React from 'react';
import { MarketStatus, GlobalMarketAnalysis } from '../types';
import { Clock, RefreshCcw, Wifi, TrendingUp, TrendingDown, Globe } from 'lucide-react';

interface HeaderProps {
  status: MarketStatus;
  marketAnalysis: GlobalMarketAnalysis | null;
  onRefreshAll: () => void;
  onRefreshMarket: () => void;
  isGlobalRefreshing: boolean;
  isMarketRefreshing: boolean;
}

const Header: React.FC<HeaderProps> = ({ status, marketAnalysis, onRefreshAll, onRefreshMarket, isGlobalRefreshing, isMarketRefreshing }) => {
  // Use marketAnalysis if available, otherwise fallback to loading or empty
  const indices = marketAnalysis?.indices || [
    { name: 'S&P 500', value: 0, change: 0, changePercent: 0 },
    { name: 'Nasdaq', value: 0, change: 0, changePercent: 0 },
    { name: 'HSI', value: 0, change: 0, changePercent: 0 },
    { name: 'BTC/USD', value: 0, change: 0, changePercent: 0 },
  ];

  const marketSummary = marketAnalysis?.summary || "Initializing market agents...";
  const sentiment = marketAnalysis?.sentiment || "Neutral";

  return (
    <header className="border-b border-gray-800 bg-gray-950/80 backdrop-blur-md sticky top-0 z-20 flex flex-col">
      {/* Top Bar: Controls & Status */}
      <div className="h-16 px-6 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              Market Overview
              {isMarketRefreshing && <RefreshCcw className="w-3 h-3 animate-spin text-gray-500" />}
            </h2>
            <p className="text-xs text-gray-500 truncate max-w-[200px] sm:max-w-md">{marketSummary}</p>
          </div>
          
          <div className="h-8 w-px bg-gray-800 mx-2 hidden sm:block"></div>
          
          <div className="hidden sm:flex items-center gap-4">
            <div className="flex flex-col">
              <span className="text-[10px] text-gray-500 uppercase font-bold">Global Sentiment</span>
              <span className={`text-sm font-bold ${sentiment === 'Bullish' ? 'text-green-400' : sentiment === 'Bearish' ? 'text-red-400' : 'text-gray-400'}`}>
                {sentiment}
              </span>
            </div>
            
            <div className="flex flex-col">
              <span className="text-[10px] text-gray-500 uppercase font-bold">Active Agents</span>
              <span className="text-sm font-bold text-blue-400">{status.activeAgents} Running</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right hidden md:block">
            <div className="text-sm font-mono text-gray-300 flex items-center justify-end gap-2">
              <Clock className="w-3 h-3 text-gray-500" />
              {marketAnalysis?.lastUpdated || status.lastUpdated.toLocaleTimeString()}
            </div>
            <div className="text-[10px] text-gray-500 flex items-center justify-end gap-1">
              <Wifi className="w-3 h-3" /> Connected
            </div>
          </div>
          
          <div className="flex gap-2">
            <button 
              onClick={onRefreshMarket}
              disabled={isMarketRefreshing}
              className="bg-gray-800 hover:bg-gray-700 text-gray-300 p-2 rounded-md transition-all active:scale-95 disabled:opacity-50"
              title="Refresh Global Market"
            >
              <Globe className={`w-4 h-4 ${isMarketRefreshing ? 'animate-spin' : ''}`} />
            </button>
            <button 
              onClick={onRefreshAll}
              disabled={isGlobalRefreshing}
              className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-md text-sm font-medium flex items-center gap-2 transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_15px_rgba(37,99,235,0.3)] hover:shadow-[0_0_20px_rgba(37,99,235,0.5)]"
            >
              <RefreshCcw className={`w-4 h-4 ${isGlobalRefreshing ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Run All Agents</span>
            </button>
          </div>
        </div>
      </div>

      {/* Ticker Bar */}
      <div className="bg-gray-900/50 border-t border-gray-800 h-8 flex items-center overflow-hidden">
        <div className="flex gap-8 animate-marquee px-4 w-full">
           {indices.map((idx, i) => (
             <div key={i} className="flex items-center gap-2 text-xs font-mono shrink-0">
                <span className="font-bold text-gray-400">{idx.name}</span>
                <span className="text-white">{idx.value ? idx.value.toFixed(2) : '---'}</span>
                <span className={`flex items-center ${idx.changePercent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {idx.changePercent >= 0 ? <TrendingUp className="w-3 h-3 mr-1" /> : <TrendingDown className="w-3 h-3 mr-1" />}
                  {idx.changePercent ? Math.abs(idx.changePercent).toFixed(2) : '0.00'}%
                </span>
             </div>
           ))}
           {/* Duplicate for basic marquee effect */}
           {indices.map((idx, i) => (
             <div key={`dup-${i}`} className="flex items-center gap-2 text-xs font-mono shrink-0">
                <span className="font-bold text-gray-400">{idx.name}</span>
                <span className="text-white">{idx.value ? idx.value.toFixed(2) : '---'}</span>
                <span className={`flex items-center ${idx.changePercent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {idx.changePercent >= 0 ? <TrendingUp className="w-3 h-3 mr-1" /> : <TrendingDown className="w-3 h-3 mr-1" />}
                  {idx.changePercent ? Math.abs(idx.changePercent).toFixed(2) : '0.00'}%
                </span>
             </div>
           ))}
        </div>
      </div>
    </header>
  );
};

export default Header;