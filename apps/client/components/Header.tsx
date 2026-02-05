import React, { useState, useRef, useEffect } from 'react';
import type * as T from '../src/types/schema';
import { Clock, RefreshCcw, Wifi, TrendingUp, TrendingDown, Globe, User, LogOut, ChevronDown } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

interface HeaderProps {
  status: T.MarketStatus;
  marketAnalysis: T.MarketOverview | null;
  onRefreshAll: () => void;
  onRefreshMarket: () => void;
  isGlobalRefreshing: boolean;
  isMarketRefreshing: boolean;
  marketFilter?: string;
  onFilterChange?: (filter: string) => void;
}

const Header: React.FC<HeaderProps> = ({
  status,
  marketAnalysis,
  onRefreshAll,
  onRefreshMarket,
  isGlobalRefreshing,
  isMarketRefreshing,
  marketFilter,
  onFilterChange,
}) => {
  const { user, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭菜单
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Use marketAnalysis if available, otherwise fallback to loading or empty
  const indices = marketAnalysis?.indices || [
    { name: 'S&P 500', current: 0, change: 0, change_percent: 0, code: 'SPX', region: 'US', updated_at: '', name_en: 'S&P 500' },
    { name: 'Nasdaq', current: 0, change: 0, change_percent: 0, code: 'IXIC', region: 'US', updated_at: '', name_en: 'Nasdaq' },
    { name: 'HSI', current: 0, change: 0, change_percent: 0, code: 'HSI', region: 'HK', updated_at: '', name_en: 'HSI' },
    { name: 'BTC/USD', current: 0, change: 0, change_percent: 0, code: 'BTC', region: 'GLOBAL', updated_at: '', name_en: 'BTC/USD' },
  ];

  const marketSummary = marketAnalysis?.global_sentiment || 'Initializing market agents...';
  const sentiment = marketAnalysis?.global_sentiment || 'Neutral';

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
            {/* Market Filter */}
            {marketFilter !== undefined && onFilterChange && (
              <div className="flex items-center gap-1 bg-gray-800/50 rounded-lg p-1">
                {['ALL', 'CN', 'HK', 'US'].map((filter) => (
                  <button
                    key={filter}
                    onClick={() => onFilterChange(filter)}
                    className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                      marketFilter === filter
                        ? 'bg-blue-600 text-white'
                        : 'text-gray-400 hover:text-white hover:bg-gray-700'
                    }`}
                  >
                    {filter}
                  </button>
                ))}
              </div>
            )}

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
              {marketAnalysis?.updated_at || status.lastUpdated}
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

          {/* User Menu */}
          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-2 rounded-md transition-all"
            >
              {user?.avatar_url ? (
                <img src={user.avatar_url} alt="" className="w-6 h-6 rounded-full" />
              ) : (
                <User className="w-5 h-5" />
              )}
              <span className="hidden sm:inline text-sm truncate max-w-[100px]">
                {user?.display_name || user?.email?.split('@')[0]}
              </span>
              <ChevronDown className="w-4 h-4" />
            </button>

            {showUserMenu && (
              <div className="absolute right-0 mt-2 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-lg py-1 z-50">
                <div className="px-4 py-2 border-b border-gray-700">
                  <p className="text-sm font-medium text-white truncate">
                    {user?.display_name || 'User'}
                  </p>
                  <p className="text-xs text-gray-400 truncate">{user?.email}</p>
                </div>
                <button
                  onClick={() => {
                    logout();
                    setShowUserMenu(false);
                  }}
                  className="w-full px-4 py-2 text-left text-sm text-gray-300 hover:bg-gray-700 flex items-center gap-2"
                >
                  <LogOut className="w-4 h-4" />
                  Sign Out
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Ticker Bar */}
      <div className="bg-gray-900/50 border-t border-gray-800 h-8 flex items-center overflow-hidden">
        <div className="flex gap-8 animate-marquee px-4 w-full">
           {indices.map((idx, i) => (
             <div key={i} className="flex items-center gap-2 text-xs font-mono shrink-0">
                <span className="font-bold text-gray-400">{idx.name}</span>
                <span className="text-white">
                  {'current' in idx ? idx.current.toFixed(2) : '---'}
                </span>
                <span
                  className={`flex items-center ${
                    (idx.change_percent ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}
                >
                  {(idx.change_percent ?? 0) >= 0 ? (
                    <TrendingUp className="w-3 h-3 mr-1" />
                  ) : (
                    <TrendingDown className="w-3 h-3 mr-1" />
                  )}
                  {idx.change_percent ? Math.abs(idx.change_percent).toFixed(2) : '0.00'}%
                </span>
             </div>
           ))}
           {/* Duplicate for basic marquee effect */}
           {indices.map((idx, i) => (
             <div key={`dup-${i}`} className="flex items-center gap-2 text-xs font-mono shrink-0">
                <span className="font-bold text-gray-400">{idx.name}</span>
                <span className="text-white">
                  {'current' in idx ? idx.current.toFixed(2) : '---'}
                </span>
                <span
                  className={`flex items-center ${
                    (idx.change_percent ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}
                >
                  {(idx.change_percent ?? 0) >= 0 ? (
                    <TrendingUp className="w-3 h-3 mr-1" />
                  ) : (
                    <TrendingDown className="w-3 h-3 mr-1" />
                  )}
                  {idx.change_percent ? Math.abs(idx.change_percent).toFixed(2) : '0.00'}%
                </span>
             </div>
           ))}
        </div>
      </div>
    </header>
  );
};

export default Header;