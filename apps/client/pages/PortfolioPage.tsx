/**
 * 组合分析页面
 *
 * 展示投资组合相关性分析和分散化建议
 */
import React, { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Info,
  PieChart,
  Link2,
} from 'lucide-react';
import { useWatchlist } from '../hooks';
import { usePortfolioAnalysis, PortfolioAnalysis as PortfolioAnalysisType } from '../hooks/usePortfolio';

// 相关性颜色映射
const getCorrelationColor = (value: number): string => {
  if (value >= 0.7) return 'bg-red-600';
  if (value >= 0.4) return 'bg-orange-500';
  if (value >= 0.1) return 'bg-yellow-500';
  if (value >= -0.1) return 'bg-gray-600';
  if (value >= -0.4) return 'bg-cyan-500';
  if (value >= -0.7) return 'bg-blue-500';
  return 'bg-blue-700';
};

const getCorrelationTextColor = (value: number): string => {
  if (Math.abs(value) >= 0.4) return 'text-white';
  return 'text-gray-300';
};

const getDiversificationColor = (score: number): string => {
  if (score >= 70) return 'text-green-400';
  if (score >= 40) return 'text-yellow-400';
  return 'text-red-400';
};

// 热力图单元格组件
const HeatmapCell: React.FC<{
  value: number;
  rowSymbol: string;
  colSymbol: string;
  isDiagonal: boolean;
}> = ({ value, rowSymbol, colSymbol, isDiagonal }) => {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div
      className={`relative w-12 h-12 flex items-center justify-center text-xs font-mono cursor-pointer transition-all hover:ring-2 hover:ring-white/50 ${
        isDiagonal ? 'bg-gray-700' : getCorrelationColor(value)
      } ${getCorrelationTextColor(value)}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      {value.toFixed(2)}

      {showTooltip && !isDiagonal && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-50 whitespace-nowrap">
          <div className="text-xs text-gray-400">
            {rowSymbol} ↔ {colSymbol}
          </div>
          <div className={`text-sm font-bold ${value > 0 ? 'text-red-400' : 'text-blue-400'}`}>
            {value > 0 ? '正相关' : '负相关'}: {(value * 100).toFixed(1)}%
          </div>
        </div>
      )}
    </div>
  );
};

const PortfolioPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: stocks = [] } = useWatchlist();
  const portfolioMutation = usePortfolioAnalysis();
  const [analysis, setAnalysis] = useState<PortfolioAnalysisType | null>(null);

  const handleAnalyze = async () => {
    const symbols = stocks.map(s => s.symbol);
    try {
      const result = await portfolioMutation.mutateAsync(symbols);
      setAnalysis(result);
    } catch (error) {
      console.error('Portfolio analysis failed', error);
    }
  };

  // 自动运行分析
  useEffect(() => {
    if (stocks.length >= 2 && !analysis && !portfolioMutation.isPending) {
      handleAnalyze();
    }
  }, [stocks.length]);

  // 排序后的股票收益摘要
  const sortedReturns = useMemo(() => {
    if (!analysis?.correlation.returns_summary) return [];
    return Object.entries(analysis.correlation.returns_summary)
      .map(([symbol, data]) => ({ symbol, ...data }))
      .sort((a, b) => b.total_return - a.total_return);
  }, [analysis]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="shrink-0 px-6 py-4 border-b border-gray-800 bg-gray-900/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/')}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400 hover:text-white"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-cyan-500/10 rounded-lg">
                <PieChart className="w-5 h-5 text-cyan-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Portfolio Analysis</h1>
                <p className="text-xs text-gray-500">{stocks.length} stocks in portfolio</p>
              </div>
            </div>
          </div>

          <button
            onClick={handleAnalyze}
            disabled={portfolioMutation.isPending || stocks.length < 2}
            className="flex items-center gap-2 px-3 py-1.5 bg-cyan-600 text-white rounded-lg hover:bg-cyan-500 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${portfolioMutation.isPending ? 'animate-spin' : ''}`} />
            {portfolioMutation.isPending ? 'Analyzing...' : 'Refresh'}
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 overflow-y-auto p-6">
        {stocks.length < 2 ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-500">
            <AlertTriangle className="w-12 h-12 mb-4 opacity-50" />
            <p>需要至少 2 只股票来进行组合分析</p>
            <p className="text-sm mt-2">请在 Dashboard 添加更多股票到关注列表</p>
          </div>
        ) : portfolioMutation.isPending && !analysis ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-500">
            <RefreshCw className="w-12 h-12 mb-4 animate-spin" />
            <p>正在分析组合...</p>
          </div>
        ) : portfolioMutation.error ? (
          <div className="flex flex-col items-center justify-center h-64 text-red-400">
            <AlertTriangle className="w-12 h-12 mb-4" />
            <p>分析失败: {(portfolioMutation.error as Error).message}</p>
            <button
              onClick={handleAnalyze}
              className="mt-4 px-4 py-2 bg-gray-800 rounded-lg hover:bg-gray-700"
            >
              重试
            </button>
          </div>
        ) : analysis ? (
          <div className="max-w-6xl mx-auto space-y-6">
            {/* 顶部摘要卡片 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* 分散化评分 */}
              <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-400">Diversification Score</span>
                  <Info className="w-4 h-4 text-gray-600" />
                </div>
                <div className={`text-4xl font-bold ${getDiversificationColor(analysis.diversification_score)}`}>
                  {analysis.diversification_score}
                  <span className="text-lg text-gray-500">/100</span>
                </div>
                <div className="mt-2 h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-1000 ${
                      analysis.diversification_score >= 70 ? 'bg-green-500' :
                      analysis.diversification_score >= 40 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${analysis.diversification_score}%` }}
                  />
                </div>
              </div>

              {/* 风险聚类 */}
              <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-400">Risk Clusters</span>
                  <Link2 className="w-4 h-4 text-gray-600" />
                </div>
                <div className="text-4xl font-bold text-white">
                  {analysis.risk_clusters.length}
                  <span className="text-lg text-gray-500"> groups</span>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  {analysis.risk_clusters.length === 0
                    ? '无高度相关股票群'
                    : `${analysis.risk_clusters.reduce((sum, c) => sum + c.stocks.length, 0)} stocks in correlated groups`}
                </p>
              </div>

              {/* 股票数量 */}
              <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-400">Analyzed Stocks</span>
                  <CheckCircle className="w-4 h-4 text-green-500" />
                </div>
                <div className="text-4xl font-bold text-white">
                  {analysis.correlation.symbols.length}
                  <span className="text-lg text-gray-500">/{stocks.length}</span>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  {analysis.correlation.symbols.length === stocks.length
                    ? '所有股票数据完整'
                    : `${stocks.length - analysis.correlation.symbols.length} 只股票数据不足`}
                </p>
              </div>
            </div>

            {/* 相关性热力图 */}
            <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700">
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-gradient-to-r from-blue-500 to-red-500" />
                Correlation Heatmap
              </h3>

              <div className="overflow-x-auto">
                <div className="inline-block min-w-max">
                  {/* 列标题 */}
                  <div className="flex">
                    <div className="w-20" />
                    {analysis.correlation.symbols.map(symbol => (
                      <div key={symbol} className="w-12 text-center">
                        <span className="text-xs text-gray-400 font-mono truncate block" style={{ writingMode: 'vertical-lr' }}>
                          {symbol.split('.')[0]}
                        </span>
                      </div>
                    ))}
                  </div>

                  {/* 矩阵行 */}
                  {analysis.correlation.matrix.map((row, i) => (
                    <div key={i} className="flex items-center">
                      <div className="w-20 pr-2 text-right">
                        <span className="text-xs text-gray-400 font-mono truncate">
                          {analysis.correlation.symbols[i].split('.')[0]}
                        </span>
                      </div>

                      {row.map((value, j) => (
                        <HeatmapCell
                          key={j}
                          value={value}
                          rowSymbol={analysis.correlation.symbols[i]}
                          colSymbol={analysis.correlation.symbols[j]}
                          isDiagonal={i === j}
                        />
                      ))}
                    </div>
                  ))}
                </div>
              </div>

              {/* 图例 */}
              <div className="mt-4 flex items-center justify-center gap-4 text-xs text-gray-400">
                <span className="flex items-center gap-1">
                  <span className="w-4 h-4 rounded bg-blue-700" /> -1.0 负相关
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-4 h-4 rounded bg-gray-600" /> 0 无相关
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-4 h-4 rounded bg-red-600" /> +1.0 正相关
                </span>
              </div>
            </div>

            {/* 收益摘要 */}
            {sortedReturns.length > 0 && (
              <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700">
                <h3 className="text-lg font-bold text-white mb-4">Returns Summary (1M)</h3>

                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                  {sortedReturns.map(item => (
                    <div
                      key={item.symbol}
                      className={`p-3 rounded-lg border ${
                        item.total_return >= 0
                          ? 'bg-green-950/30 border-green-900/50'
                          : 'bg-red-950/30 border-red-900/50'
                      }`}
                    >
                      <div className="text-xs text-gray-400 font-mono truncate">{item.symbol.split('.')[0]}</div>
                      <div className={`text-lg font-bold ${item.total_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {item.total_return >= 0 ? '+' : ''}{item.total_return.toFixed(1)}%
                      </div>
                      <div className="text-xs text-gray-500">Vol: {item.volatility.toFixed(1)}%</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 建议 */}
            <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700">
              <h3 className="text-lg font-bold text-white mb-4">Recommendations</h3>

              <div className="space-y-3">
                {analysis.recommendations.map((rec, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-3 p-3 bg-gray-900/50 rounded-lg border border-gray-700"
                  >
                    <span className="text-xl">{rec.charAt(0)}</span>
                    <p className="text-sm text-gray-300">{rec.slice(2)}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : null}
      </main>
    </div>
  );
};

export default PortfolioPage;
