/**
 * 侧边栏组件
 *
 * 包含股票添加、AI Scout、市场筛选和导航
 */
import React, { useState } from 'react';
import { Stock, MarketOpportunity } from '../types';
import {
  Plus,
  LayoutDashboard,
  Settings,
  Activity,
  Sparkles,
  Loader,
  Bot,
  PieChart,
  Globe,
  ChevronDown,
  ChevronUp,
  Zap,
  Cpu,
} from 'lucide-react';
import { useScout } from '../hooks';
import SystemStatusPanel from './SystemStatusPanel';

interface SidebarProps {
  stocks: Stock[];
  onAddStock: (symbol: string, market: 'US' | 'HK' | 'CN') => void;
  selectedMarketFilter: string;
  onFilterChange: (filter: string) => void;
  onOpenPromptEditor?: () => void;
  onOpenPortfolioAnalysis?: () => void;
  onOpenMacroDashboard?: () => void;
  onOpenSchedulerPanel?: () => void;
  onOpenAIConfig?: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  stocks,
  onAddStock,
  selectedMarketFilter,
  onFilterChange,
  onOpenPromptEditor,
  onOpenPortfolioAnalysis,
  onOpenMacroDashboard,
  onOpenSchedulerPanel,
  onOpenAIConfig,
}) => {
  // 手动添加状态
  const [isAdding, setIsAdding] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');
  const [newMarket, setNewMarket] = useState<'CN' | 'HK' | 'US'>('CN');

  // 系统状态面板展开状态
  const [statusExpanded, setStatusExpanded] = useState(false);

  // 使用 useScout hook
  const scout = useScout();

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (newSymbol) {
      onAddStock(newSymbol.toUpperCase(), newMarket);
      setNewSymbol('');
      setIsAdding(false);
    }
  };

  const handleScout = async (e: React.FormEvent) => {
    e.preventDefault();
    await scout.scout();
  };

  const handleAddScoutResult = (stock: MarketOpportunity) => {
    onAddStock(stock.symbol, stock.market);
  };

  return (
    <div className="w-80 bg-gray-900 border-r border-gray-800 flex flex-col h-full shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-gray-800 flex items-center gap-2">
        <Activity className="w-6 h-6 text-blue-500" />
        <h1 className="font-bold text-lg tracking-tight">StockAgents</h1>
      </div>

      {/* Main Content */}
      <div className="p-4 flex-1 overflow-y-auto custom-scrollbar">
        {/* 手动添加股票 */}
        <button
          onClick={() => setIsAdding(!isAdding)}
          className="w-full bg-gray-800 hover:bg-gray-700 text-white py-2 rounded-md text-sm font-medium flex items-center justify-center gap-2 transition-colors mb-3 border border-gray-700"
        >
          <Plus className="w-4 h-4" /> Add Manually
        </button>

        {isAdding && (
          <form onSubmit={handleAdd} className="bg-gray-800 p-3 rounded-md mb-4 animate-in fade-in slide-in-from-top-2">
            <div className="flex gap-2 mb-2">
              <select
                value={newMarket}
                onChange={(e) => setNewMarket(e.target.value as Stock['market'])}
                className="bg-gray-700 text-xs rounded px-1 py-1 text-white border-none outline-none"
              >
                <option value="CN">CN</option>
                <option value="HK">HK</option>
                <option value="US">US</option>
              </select>
              <input
                type="text"
                placeholder="Symbol (e.g. AAPL)"
                value={newSymbol}
                onChange={(e) => setNewSymbol(e.target.value)}
                className="bg-gray-700 text-xs rounded px-2 py-1 w-full text-white outline-none focus:ring-1 focus:ring-blue-500"
                autoFocus
              />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setIsAdding(false)} className="text-xs text-gray-400 hover:text-white">
                Cancel
              </button>
              <button type="submit" className="text-xs text-blue-400 hover:text-blue-300 font-bold">
                Add
              </button>
            </div>
          </form>
        )}

        {/* AI Scout Agent */}
        <div className="mb-6">
          <button
            onClick={scout.toggle}
            className={`w-full py-2 rounded-md text-sm font-bold flex items-center justify-center gap-2 transition-all shadow-lg ${
              scout.isOpen
                ? 'bg-indigo-600 text-white'
                : 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:opacity-90'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            {scout.isOpen ? 'Close Scout' : 'AI Market Scout'}
          </button>

          {scout.isOpen && (
            <div className="bg-gray-800/50 rounded-lg p-3 mt-3 border border-indigo-500/30">
              <form onSubmit={handleScout}>
                <label className="text-xs text-indigo-300 font-bold mb-1 block">
                  What are we looking for?
                </label>
                <textarea
                  value={scout.query}
                  onChange={(e) => scout.setQuery(e.target.value)}
                  placeholder="e.g. Undervalued Chinese tech stocks, or US stocks with high RSI..."
                  className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-xs text-white focus:outline-none focus:border-indigo-500 min-h-[60px] resize-none mb-2"
                />
                <button
                  type="submit"
                  disabled={scout.isLoading || !scout.query}
                  className="w-full bg-indigo-600 hover:bg-indigo-500 text-white py-1.5 rounded text-xs font-bold disabled:opacity-50"
                >
                  {scout.isLoading ? <Loader className="w-3 h-3 animate-spin mx-auto" /> : 'Run Scout Agent'}
                </button>
              </form>

              {/* Scout Results */}
              {scout.results.length > 0 && (
                <div className="mt-3 space-y-2">
                  <div className="text-[10px] text-gray-400 uppercase font-bold">Suggestions</div>
                  {scout.results.map((res, idx) => (
                    <div
                      key={idx}
                      className="bg-gray-900 p-2 rounded border border-gray-700 flex justify-between items-center group"
                    >
                      <div className="flex-1 min-w-0 mr-2">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white text-xs">{res.symbol}</span>
                          <span className="text-[9px] bg-gray-800 text-gray-400 px-1 rounded">{res.market}</span>
                        </div>
                        <p className="text-[10px] text-gray-400 truncate">{res.name}</p>
                        <p className="text-[9px] text-indigo-300 line-clamp-1 mt-0.5">{res.reason}</p>
                      </div>
                      <button
                        onClick={() => handleAddScoutResult(res)}
                        className="bg-gray-800 hover:bg-indigo-600 text-gray-400 hover:text-white p-1.5 rounded transition-colors"
                        title="Add to Watchlist"
                      >
                        <Plus className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Market Filter */}
        <div className="mb-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">Market Filter</div>
        <div className="flex gap-1 mb-6">
          {['ALL', 'CN', 'HK', 'US'].map((filter) => (
            <button
              key={filter}
              onClick={() => onFilterChange(filter)}
              className={`flex-1 py-1 text-xs rounded ${
                selectedMarketFilter === filter
                  ? 'bg-gray-700 text-white'
                  : 'bg-gray-900 text-gray-500 border border-gray-800 hover:border-gray-600'
              }`}
            >
              {filter}
            </button>
          ))}
        </div>

        {/* Navigation */}
        <nav className="space-y-1">
          <a href="#" className="flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md bg-gray-800 text-white">
            <LayoutDashboard className="w-4 h-4" /> Dashboard
          </a>
          <button
            onClick={onOpenMacroDashboard}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
          >
            <Globe className="w-4 h-4" /> Macro Economy
          </button>
          <button
            onClick={onOpenPortfolioAnalysis}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
          >
            <PieChart className="w-4 h-4" /> Portfolio Analysis
          </button>
          <button
            onClick={onOpenPromptEditor}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
          >
            <Bot className="w-4 h-4" /> Prompt Editor
          </button>
          <button
            onClick={onOpenSchedulerPanel}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
          >
            <Zap className="w-4 h-4" /> Scheduler
          </button>
          <button
            onClick={onOpenAIConfig}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
          >
            <Cpu className="w-4 h-4" /> AI Config
          </button>
          <a
            href="#"
            className="flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
          >
            <Settings className="w-4 h-4" /> Settings
          </a>
        </nav>
      </div>

      {/* Footer - System Status */}
      <div className="p-4 border-t border-gray-800">
        <SystemStatusPanel
          expanded={statusExpanded}
          onToggle={() => setStatusExpanded(!statusExpanded)}
        />
      </div>
    </div>
  );
};

export default Sidebar;
