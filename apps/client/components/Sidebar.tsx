/**
 * 侧边栏组件
 *
 * 负责导航和品牌展示
 */
import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Stock, MarketOpportunity } from '../types';
import {
  Plus,
  LayoutDashboard,
  Settings,
  Sparkles,
  Loader,
  Bot,
  PieChart,
  Globe,
  Zap,
  Cpu,
  Landmark,
  Calendar,
  Newspaper,
} from 'lucide-react';
import { useScout, useAddStock } from '../hooks';
import SystemStatusPanel from './SystemStatusPanel';

const Sidebar: React.FC = () => {
  const location = useLocation();

  // 手动添加状态
  const [isAdding, setIsAdding] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');
  const [newMarket, setNewMarket] = useState<'CN' | 'HK' | 'US'>('CN');

  // 系统状态面板展开状态
  const [statusExpanded, setStatusExpanded] = useState(false);

  // 使用 hooks
  const scout = useScout();
  const addStockMutation = useAddStock();

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newSymbol) {
      try {
        await addStockMutation.mutateAsync(newSymbol.toUpperCase());
        setNewSymbol('');
        setIsAdding(false);
      } catch (error) {
        console.error('Failed to add stock', error);
      }
    }
  };

  const handleScout = async (e: React.FormEvent) => {
    e.preventDefault();
    await scout.scout();
  };

  const handleAddScoutResult = async (stock: MarketOpportunity) => {
    try {
      await addStockMutation.mutateAsync(stock.symbol);
    } catch (error) {
      console.error('Failed to add stock', error);
    }
  };

  // 导航项配置
  const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/news', icon: Newspaper, label: 'News', iconColor: 'text-orange-400' },
    { path: '/china-market', icon: Landmark, label: 'A股市场', iconColor: 'text-red-400' },
    { path: '/macro', icon: Globe, label: 'Macro Economy' },
    { path: '/portfolio', icon: PieChart, label: 'Portfolio Analysis' },
    { path: '/prompts', icon: Bot, label: 'Prompt Editor' },
    { path: '/scheduler', icon: Calendar, label: 'Scheduler' },
    { path: '/ai-config', icon: Cpu, label: 'AI Config' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ];

  return (
    <div className="w-80 bg-gray-900 border-r border-gray-800 flex flex-col h-full shrink-0">
      {/* Header - 品牌区域 */}
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-lg tracking-tight text-white">Stock Agents</h1>
            <p className="text-[10px] text-gray-500">AI-Powered Trading</p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="p-4 flex-1 overflow-y-auto custom-scrollbar">
        {/* 手动添加股票 */}
        <button
          onClick={() => setIsAdding(!isAdding)}
          className="w-full bg-gray-800/50 hover:bg-gray-700/50 text-white py-2.5 rounded-xl text-sm font-medium flex items-center justify-center gap-2 transition-all mb-3 border border-gray-700/50 hover:border-gray-600"
        >
          <Plus className="w-4 h-4" /> Add Stock
        </button>

        {isAdding && (
          <form onSubmit={handleAdd} className="bg-gray-800/50 backdrop-blur-sm p-4 rounded-xl mb-4 animate-in fade-in slide-in-from-top-2 border border-gray-700/50">
            <div className="flex gap-2 mb-3">
              <select
                value={newMarket}
                onChange={(e) => setNewMarket(e.target.value as 'CN' | 'HK' | 'US')}
                className="bg-gray-900 text-xs rounded-lg px-2 py-2 text-white border border-gray-700 outline-none focus:border-blue-500 transition-colors"
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
                className="bg-gray-900 text-xs rounded-lg px-3 py-2 w-full text-white outline-none border border-gray-700 focus:border-blue-500 transition-colors"
                autoFocus
              />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setIsAdding(false)} className="text-xs text-gray-400 hover:text-white px-3 py-1.5 rounded-lg hover:bg-gray-700/50 transition-colors">
                Cancel
              </button>
              <button
                type="submit"
                disabled={addStockMutation.isPending}
                className="text-xs text-white font-bold px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 transition-colors disabled:opacity-50"
              >
                {addStockMutation.isPending ? 'Adding...' : 'Add'}
              </button>
            </div>
          </form>
        )}

        {/* AI Scout Agent */}
        <div className="mb-6">
          <button
            onClick={scout.toggle}
            className={`w-full py-2.5 rounded-xl text-sm font-bold flex items-center justify-center gap-2 transition-all shadow-lg ${
              scout.isOpen
                ? 'bg-indigo-600 text-white shadow-indigo-500/30'
                : 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:opacity-90 shadow-indigo-500/20 hover:shadow-indigo-500/40'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            {scout.isOpen ? 'Close Scout' : 'AI Market Scout'}
          </button>

          {scout.isOpen && (
            <div className="bg-gray-800/30 backdrop-blur-sm rounded-xl p-4 mt-3 border border-indigo-500/20">
              <form onSubmit={handleScout}>
                <label className="text-xs text-indigo-300 font-bold mb-2 block">
                  What are we looking for?
                </label>
                <textarea
                  value={scout.query}
                  onChange={(e) => scout.setQuery(e.target.value)}
                  placeholder="e.g. Undervalued Chinese tech stocks, or US stocks with high RSI..."
                  className="w-full bg-gray-900/80 border border-gray-700/50 rounded-lg p-3 text-xs text-white focus:outline-none focus:border-indigo-500 min-h-[70px] resize-none mb-3 placeholder-gray-500"
                />
                <button
                  type="submit"
                  disabled={scout.isLoading || !scout.query}
                  className="w-full bg-indigo-600 hover:bg-indigo-500 text-white py-2 rounded-lg text-xs font-bold disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
                >
                  {scout.isLoading ? <Loader className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                  {scout.isLoading ? 'Searching...' : 'Run Scout Agent'}
                </button>
              </form>

              {/* Scout Results */}
              {scout.results.length > 0 && (
                <div className="mt-4 space-y-2">
                  <div className="text-[10px] text-gray-400 uppercase font-bold tracking-wider">Suggestions</div>
                  {scout.results.map((res, idx) => (
                    <div
                      key={idx}
                      className="bg-gray-900/50 p-3 rounded-lg border border-gray-700/50 flex justify-between items-center group hover:border-indigo-500/30 transition-colors"
                    >
                      <div className="flex-1 min-w-0 mr-2">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white text-xs">{res.symbol}</span>
                          <span className="text-[9px] bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded">{res.market}</span>
                        </div>
                        <p className="text-[10px] text-gray-400 truncate">{res.name}</p>
                        <p className="text-[9px] text-indigo-300/80 line-clamp-1 mt-0.5">{res.reason}</p>
                      </div>
                      <button
                        onClick={() => handleAddScoutResult(res)}
                        className="bg-gray-800/50 hover:bg-indigo-600 text-gray-400 hover:text-white p-2 rounded-lg transition-all"
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

        {/* Navigation */}
        <div className="mb-2 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Navigation</div>
        <nav className="space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-xl transition-colors ${
                  isActive
                    ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20'
                    : 'text-gray-400 hover:bg-gray-800/50 hover:text-white'
                }`
              }
            >
              <item.icon className={`w-4 h-4 ${item.iconColor || ''}`} />
              {item.label}
            </NavLink>
          ))}
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
