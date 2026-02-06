/**
 * 产业链知识图谱页面
 *
 * 展示 A 股核心产业链图谱，支持搜索和交互式浏览。
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GitBranch, Search, ChevronRight } from 'lucide-react';
import PageLayout from '../components/layout/PageLayout';
import SupplyChainGraph from '../components/SupplyChainGraph';
import { useChainList, useStockChainPosition } from '../hooks/useSupplyChain';
import type { ChainSummary } from '../hooks/useSupplyChain';
import { useAddStock } from '../hooks';
import { useToast } from '../components/Toast';

const SupplyChainPage: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const addStockMutation = useAddStock();

  const [selectedChain, setSelectedChain] = useState<string>('');
  const [searchSymbol, setSearchSymbol] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  const { data: chainList, isLoading: chainsLoading } = useChainList();
  const { data: stockPosition, isLoading: positionLoading } = useStockChainPosition(searchQuery);

  const handleCompanyClick = async (symbol: string) => {
    try {
      await addStockMutation.mutateAsync(symbol);
      toast.success(`已添加 ${symbol} 到关注列表`);
      navigate('/');
    } catch (error) {
      toast.error('添加失败: ' + String(error));
    }
  };

  const handleSearch = () => {
    if (searchSymbol.trim()) {
      setSearchQuery(searchSymbol.trim());
    }
  };

  return (
    <PageLayout
      title="产业链图谱"
      subtitle="A 股核心产业链上下游关系分析"
      icon={GitBranch}
      iconColor="text-cyan-400"
      iconBgColor="bg-cyan-500/10"
      variant="wide"
    >
      <div className="space-y-6">
        {/* 搜索栏 */}
        <div className="bg-surface-raised rounded-lg p-4">
          <div className="flex items-center gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-500" />
              <input
                type="text"
                value={searchSymbol}
                onChange={(e) => setSearchSymbol(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="输入股票代码查找产业链位置（如 300750、002594）"
                className="w-full bg-surface-overlay text-stone-300 text-sm rounded-lg pl-10 pr-4 py-2.5 border border-border-strong focus:border-cyan-500 focus:outline-none"
              />
            </div>
            <button
              onClick={handleSearch}
              disabled={!searchSymbol.trim() || positionLoading}
              className="bg-cyan-600 hover:bg-cyan-700 disabled:bg-surface-muted text-white text-sm px-4 py-2.5 rounded-lg transition-colors"
            >
              查找
            </button>
          </div>

          {/* 搜索结果 */}
          {searchQuery && stockPosition && (
            <div className="mt-3 p-3 bg-surface-overlay/50 rounded-lg">
              {stockPosition.found ? (
                <div>
                  <div className="text-green-400 text-sm font-medium mb-2">
                    找到 {stockPosition.chain_count} 条相关产业链
                  </div>
                  <div className="space-y-1">
                    {stockPosition.chains?.map((chain, idx) => (
                      <div
                        key={idx}
                        className="flex items-center gap-2 text-xs cursor-pointer hover:bg-surface-muted/50 rounded px-2 py-1"
                        onClick={() => setSelectedChain(chain.chain_id)}
                      >
                        <span className="text-cyan-400">{chain.chain_name}</span>
                        <span className="text-stone-500">→</span>
                        <span className="text-stone-300">{chain.segment}</span>
                        <span className={`px-1.5 py-0.5 rounded text-xs ${
                          chain.position === 'upstream'
                            ? 'bg-blue-900/30 text-blue-400'
                            : chain.position === 'midstream'
                              ? 'bg-yellow-900/30 text-yellow-400'
                              : 'bg-green-900/30 text-green-400'
                        }`}>
                          {chain.position === 'upstream' ? '上游' : chain.position === 'midstream' ? '中游' : '下游'}
                        </span>
                        <ChevronRight className="w-3 h-3 text-stone-600 ml-auto" />
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-stone-400 text-sm">
                  {stockPosition.suggestion || '未找到该股票的产业链信息'}
                </div>
              )}
            </div>
          )}
        </div>

        {/* 产业链选择 */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
          {chainsLoading ? (
            <div className="col-span-full text-stone-500 text-sm text-center py-4">加载中...</div>
          ) : (
            chainList?.chains?.map((chain: ChainSummary) => (
              <button
                key={chain.id}
                onClick={() => setSelectedChain(chain.id)}
                className={`p-3 rounded-lg border text-left transition-colors ${
                  selectedChain === chain.id
                    ? 'border-cyan-500 bg-cyan-900/20'
                    : 'border-border bg-surface-raised hover:border-border-strong'
                }`}
              >
                <div className="text-white text-sm font-medium truncate">{chain.name}</div>
                <div className="text-stone-500 text-xs mt-1">
                  {chain.total_companies} 家公司
                </div>
              </button>
            ))
          )}
        </div>

        {/* 产业链图谱 */}
        {selectedChain && (
          <SupplyChainGraph
            chainId={selectedChain}
            onCompanyClick={handleCompanyClick}
          />
        )}

        {/* 空状态 */}
        {!selectedChain && (
          <div className="bg-surface-raised rounded-lg p-12 text-center">
            <GitBranch className="w-12 h-12 text-surface-muted mx-auto mb-3" />
            <p className="text-stone-500 text-sm">选择一条产业链查看图谱</p>
            <p className="text-stone-600 text-xs mt-1">或输入股票代码搜索其产业链位置</p>
          </div>
        )}
      </div>
    </PageLayout>
  );
};

export default SupplyChainPage;
