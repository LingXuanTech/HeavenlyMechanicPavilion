/**
 * 仪表板页面
 *
 * 显示股票监控卡片和市场概览
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Stock, MarketStatus } from '../types';
import Header from '../components/Header';
import StockCard from '../components/StockCard';
import StockDetailModal from '../components/StockDetailModal';
import FlashNewsTicker from '../components/FlashNewsTicker';
import {
  useWatchlist,
  useRemoveStock,
  useStockPrices,
  useStockAnalysis,
  useGlobalMarket,
  useFlashNews,
  useMarketStatus,
} from '../hooks';

const DashboardPage: React.FC = () => {
  // === TanStack Query Hooks ===

  // Watchlist 数据
  const { data: stocks = [], isLoading: isWatchlistLoading } = useWatchlist();
  const removeStockMutation = useRemoveStock();

  // 价格数据（自动并行获取所有股票价格）
  const { prices, isLoading: isPricesLoading } = useStockPrices(stocks);

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
    isLoading: isGlobalMarketLoading,
    isFetching: isMarketRefreshing,
  } = useGlobalMarket();

  const { data: flashNews = [], isFetching: isFlashNewsRefreshing } = useFlashNews();
  const { refreshGlobalMarket, refreshFlashNews } = useMarketStatus();

  // === 本地状态 ===
  const [marketFilter, setMarketFilter] = useState('ALL');
  const [selectedStock, setSelectedStock] = useState<Stock | null>(null);
  // 跟踪新鲜分析（用于打字机效果）
  const [freshAnalyses, setFreshAnalyses] = useState<Set<string>>(new Set());

  // === 计算属性 ===
  const marketStatus: MarketStatus = useMemo(
    () => ({
      sentiment: globalMarketData?.sentiment || 'Neutral',
      lastUpdated: new Date(),
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
    async (symbol: string, _stockName: string) => {
      try {
        // 标记为新鲜分析（用于打字机效果）
        setFreshAnalyses(prev => new Set(prev).add(symbol));
        await runAnalysis(symbol);
      } catch (error) {
        console.error(`Analysis failed for ${symbol}`, error);
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
    runMultipleAnalyses(symbols, 2000);
  }, [filteredStocks, runMultipleAnalyses]);

  const handleDeleteStock = useCallback(
    async (symbol: string) => {
      try {
        await removeStockMutation.mutateAsync(symbol);
        if (selectedStock?.symbol === symbol) {
          setSelectedStock(null);
        }
      } catch (e) {
        console.error('Failed to delete stock', e);
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
      <FlashNewsTicker news={flashNews} isRefreshing={isFlashNewsRefreshing} />

      <main className="flex-1 overflow-y-auto p-6 scroll-smooth">
        {/* Loading State */}
        {isWatchlistLoading && (
          <div className="flex items-center justify-center h-64 text-gray-500">Loading watchlist...</div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 pb-20">
          {filteredStocks.map((stock) => (
            <StockCard
              key={stock.symbol}
              stock={stock}
              priceData={prices[stock.symbol]}
              analysis={getAnalysis(stock.symbol)}
              onRefresh={handleRunAnalysis}
              isAnalyzing={analyzingStates[stock.symbol] || false}
              currentStage={analyzingStages[stock.symbol]}
              onDelete={handleDeleteStock}
              onClick={setSelectedStock}
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
      </main>

      <div className="pointer-events-none fixed bottom-0 left-80 right-0 h-32 bg-gradient-to-t from-gray-950 to-transparent z-10"></div>

      {/* Detail Modal */}
      {selectedStock && (
        <StockDetailModal
          stock={selectedStock}
          priceData={prices[selectedStock.symbol]}
          analysis={getAnalysis(selectedStock.symbol)}
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
