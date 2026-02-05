/**
 * 仪表板页面
 *
 * 显示股票监控卡片、市场概览和新闻摘要
 */
import React, { useState, useCallback, useMemo } from 'react';
import type * as T from '../src/types/schema';
import { logger } from '../utils/logger';
import Header from '../components/Header';
import LazyStockCard from '../components/LazyStockCard';
import StockDetailModal from '../components/StockDetailModal';
import FlashNewsTicker from '../components/FlashNewsTicker';
import NewsHighlightsPanel from '../components/NewsHighlightsPanel';
import {
  useWatchlist,
  useRemoveStock,
  useStockPrices,
  useStockAnalysis,
  useGlobalMarket,
  useFlashNews,
  useMarketStatus,
} from '../hooks';
import type { AnalysisOptions } from '../services/api';

const DashboardPage: React.FC = () => {
  // === TanStack Query Hooks ===

  // Watchlist 数据
  const { data: stocks = [], isLoading: isWatchlistLoading } = useWatchlist();
  const removeStockMutation = useRemoveStock();

  // 价格数据（自动并行获取所有股票价格）
  const { prices } = useStockPrices(stocks);

  // 分析相关
  const {
    analyzingStates,
    analyzingStages,
    runAnalysis,
    runMultipleAnalyses,
    getAnalysis,
  } = useStockAnalysis();

  // 市场数据
  const {
    data: globalMarketData,
    isFetching: isMarketRefreshing,
  } = useGlobalMarket();

  const { data: flashNews = [], isFetching: isFlashNewsRefreshing } = useFlashNews();
  const { refreshGlobalMarket } = useMarketStatus();

  // === 本地状态 ===
  const [marketFilter, setMarketFilter] = useState('ALL');
  const [selectedStock, setSelectedStock] = useState<T.AssetPrice | null>(null);
  // 跟踪新鲜分析（用于打字机效果）
  const [freshAnalyses, setFreshAnalyses] = useState<Set<string>>(new Set());

  // === 计算属性 ===
  const marketStatus: T.MarketStatus = useMemo(
    () => ({
      sentiment: (globalMarketData?.global_sentiment as any) || 'Neutral',
      lastUpdated: new Date().toISOString(),
      activeAgents: Object.values(analyzingStates).filter(Boolean).length,
    }),
    [globalMarketData, analyzingStates]
  );

  const filteredStocks = useMemo(
    () => stocks.filter((s) => marketFilter === 'ALL' || s.market === marketFilter),
    [stocks, marketFilter]
  );

  const isGlobalRefreshing = useMemo(
    () => Object.values(analyzingStates).some(Boolean),
    [analyzingStates]
  );

  // === 事件处理 ===
  const handleRunAnalysis = useCallback(
    async (symbol: string, _stockName: string, options?: AnalysisOptions) => {
      try {
        // 标记为新鲜分析（用于打字机效果）
        setFreshAnalyses(prev => new Set(prev).add(symbol));
        await runAnalysis(symbol, options);
      } catch (error) {
        logger.error(`Analysis failed for ${symbol}`, error);
        // 失败时移除新鲜标记
        setFreshAnalyses(prev => {
          const next = new Set(prev);
          next.delete(symbol);
          return next;
        });
      }
    },
    [runAnalysis]
  );

  const handleRunAll = useCallback(() => {
    const symbols = filteredStocks.map((s) => s.symbol);
    runMultipleAnalyses(symbols, {}, 2000);
  }, [filteredStocks, runMultipleAnalyses]);

  const handleDeleteStock = useCallback(
    async (symbol: string) => {
      try {
        await removeStockMutation.mutateAsync(symbol);
        if (selectedStock?.symbol === symbol) {
          setSelectedStock(null);
        }
      } catch (e) {
        logger.error('Failed to delete stock', e);
      }
    },
    [removeStockMutation, selectedStock]
  );

  const handleRefreshMarket = useCallback(async () => {
    await refreshGlobalMarket();
  }, [refreshGlobalMarket]);

  // === 渲染 ===
  return (
    <>
      <Header
        status={marketStatus}
        marketAnalysis={globalMarketData || null}
        onRefreshAll={handleRunAll}
        onRefreshMarket={handleRefreshMarket}
        isGlobalRefreshing={isGlobalRefreshing}
        isMarketRefreshing={isMarketRefreshing}
        marketFilter={marketFilter}
        onFilterChange={setMarketFilter}
      />

      {/* Watchdog Ticker */}
      <FlashNewsTicker
        news={flashNews.map((n) => ({
          id: n.id,
          time: n.published_at,
          headline: n.title,
          impact: 'Medium',
          sentiment: n.sentiment === 'positive' ? 'Positive' : 'Negative',
          relatedSymbols: n.symbols,
        }))}
        isRefreshing={isFlashNewsRefreshing}
      />

      <main className="flex-1 overflow-hidden flex">
        {/* Stock Cards Area */}
        <div className="flex-1 overflow-y-auto p-6 scroll-smooth">
          {/* Loading State */}
          {isWatchlistLoading && (
            <div className="flex items-center justify-center h-64 text-gray-500">Loading watchlist...</div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-20">
            {filteredStocks.map((stock) => (
              <LazyStockCard
                key={stock.symbol}
                stock={
                  {
                    ...stock,
                    asset_class: 'Equity',
                    price: prices[stock.symbol]?.price || 0,
                    change_1d: prices[stock.symbol]?.change || 0,
                    change_5d: 0,
                    change_20d: 0,
                  } as T.AssetPrice
                }
                priceData={prices[stock.symbol]}
                analysis={getAnalysis(stock.symbol) as any}
                onRefresh={handleRunAnalysis}
                isAnalyzing={analyzingStates[stock.symbol] || false}
                currentStage={analyzingStages[stock.symbol]}
                onDelete={handleDeleteStock}
                onClick={(s) => setSelectedStock(s as T.AssetPrice)}
              />
            ))}

            {/* Empty State */}
            {!isWatchlistLoading && filteredStocks.length === 0 && (
              <div className="col-span-full h-64 flex flex-col items-center justify-center text-gray-600 border-2 border-dashed border-gray-800 rounded-lg">
                <p>No stocks in this filter.</p>
                <p className="text-sm">Use the "AI Market Scout" in the sidebar to find stocks.</p>
              </div>
            )}
          </div>
        </div>

        {/* News Highlights Panel */}
        <aside className="w-80 shrink-0 border-l border-gray-800 overflow-y-auto p-4 bg-gray-950/50 hidden xl:block">
          <NewsHighlightsPanel />
        </aside>
      </main>

      <div className="pointer-events-none fixed bottom-0 left-80 right-0 h-32 bg-gradient-to-t from-gray-950 to-transparent z-10 xl:right-80"></div>

      {/* Detail Modal */}
      {selectedStock && (
        <StockDetailModal
          stock={
            {
              ...selectedStock,
              market: (selectedStock as any).market || 'CN',
            } as any
          }
          priceData={prices[selectedStock.symbol]}
          analysis={getAnalysis(selectedStock.symbol) as any}
          onClose={() => {
            // 关闭时清除新鲜标记
            setFreshAnalyses(prev => {
              const next = new Set(prev);
              next.delete(selectedStock.symbol);
              return next;
            });
            setSelectedStock(null);
          }}
          enableTypewriter={freshAnalyses.has(selectedStock.symbol)}
        />
      )}
    </>
  );
};

export default DashboardPage;
