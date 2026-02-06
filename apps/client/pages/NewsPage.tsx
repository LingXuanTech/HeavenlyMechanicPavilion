/**
 * 新闻聚合页面
 *
 * 展示多来源聚合的金融新闻和快讯
 * 使用 dashboard 布局变体（全宽带自定义筛选栏）
 */
import React, { useState, useMemo } from 'react';
import {
  Newspaper,
  RefreshCw,
  Loader2,
  ExternalLink,
  TrendingUp,
  TrendingDown,
  Minus,
  Filter,
  Clock,
  Tag,
  Zap,
  ChevronRight,
  AlertCircle,
} from 'lucide-react';
import PageLayout from '../components/layout/PageLayout';
import {
  useAggregatedNews,
  useNewsFlash,
  useNewsByCategory,
  useRefreshNews,
  useNewsSources,
} from '../hooks';
import type * as T from '../src/types/schema';

// === 常量定义 ===

const CATEGORY_LABELS: Record<T.NewsCategory, string> = {
  market: '市场动态',
  stock: '个股新闻',
  macro: '宏观经济',
  policy: '政策法规',
  earnings: '财报业绩',
  ipo: 'IPO/融资',
  forex: '外汇',
  crypto: '加密货币',
  general: '综合',
};

const CATEGORY_COLORS: Record<T.NewsCategory, string> = {
  market: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  stock: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  macro: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  policy: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  earnings: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  ipo: 'bg-pink-500/20 text-pink-400 border-pink-500/30',
  forex: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  crypto: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  general: 'bg-stone-500/20 text-stone-400 border-stone-500/30',
};

// === 辅助组件 ===

const SentimentIcon: React.FC<{ sentiment: T.NewsSentiment }> = ({ sentiment }) => {
  switch (sentiment) {
    case 'positive':
      return <TrendingUp className="w-4 h-4 text-emerald-400" />;
    case 'negative':
      return <TrendingDown className="w-4 h-4 text-red-400" />;
    default:
      return <Minus className="w-4 h-4 text-stone-400" />;
  }
};

const CategoryBadge: React.FC<{ category: T.NewsCategory }> = ({ category }) => (
  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs border ${CATEGORY_COLORS[category]}`}>
    <Tag className="w-3 h-3" />
    {CATEGORY_LABELS[category]}
  </span>
);

const TimeAgo: React.FC<{ timestamp: string }> = ({ timestamp }) => {
  const getTimeAgo = (dateStr: string): string => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diff < 60) return '刚刚';
    if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
    if (diff < 604800) return `${Math.floor(diff / 86400)} 天前`;
    return date.toLocaleDateString('zh-CN');
  };

  return (
    <span className="text-xs text-stone-500 flex items-center gap-1">
      <Clock className="w-3 h-3" />
      {getTimeAgo(timestamp)}
    </span>
  );
};

const NewsCard: React.FC<{ news: T.AggregatedNewsItem }> = ({ news }) => (
  <a
    href={news.url}
    target="_blank"
    rel="noopener noreferrer"
    className="block p-4 bg-surface-overlay/50 hover:bg-surface-overlay/70 rounded-xl border border-border-strong hover:border-stone-600 transition-all group"
  >
    <div className="flex items-start gap-3">
      <SentimentIcon sentiment={news.sentiment} />
      <div className="flex-1 min-w-0">
        <h3 className="text-white font-medium text-sm leading-snug group-hover:text-accent transition-colors line-clamp-2">
          {news.title}
        </h3>
        {news.summary && (
          <p className="text-stone-400 text-xs mt-2 line-clamp-2">{news.summary}</p>
        )}
        <div className="flex items-center justify-between mt-3">
          <div className="flex items-center gap-2">
            <CategoryBadge category={news.category} />
            <span className="text-xs text-stone-500">{news.source}</span>
          </div>
          <div className="flex items-center gap-2">
            <TimeAgo timestamp={news.published_at} />
            <ExternalLink className="w-3.5 h-3.5 text-stone-500 opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        </div>
        {news.symbols.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {news.symbols.slice(0, 5).map((symbol) => (
              <span key={symbol} className="text-[10px] px-1.5 py-0.5 bg-surface-muted text-stone-300 rounded">
                {symbol}
              </span>
            ))}
            {news.symbols.length > 5 && (
              <span className="text-[10px] text-stone-500">+{news.symbols.length - 5}</span>
            )}
          </div>
        )}
      </div>
    </div>
  </a>
);

const FlashNewsItem: React.FC<{ news: T.AggregatedNewsItem }> = ({ news }) => (
  <a
    href={news.url}
    target="_blank"
    rel="noopener noreferrer"
    className="flex items-start gap-2 p-3 bg-surface-overlay/30 hover:bg-surface-overlay/50 rounded-lg border border-border-strong/50 hover:border-stone-600/50 transition-all group"
  >
    <Zap className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
    <div className="flex-1 min-w-0">
      <p className="text-sm text-stone-200 group-hover:text-white transition-colors line-clamp-2">
        {news.title}
      </p>
      <div className="flex items-center gap-2 mt-1">
        <TimeAgo timestamp={news.published_at} />
        <span className="text-xs text-stone-600">|</span>
        <span className="text-xs text-stone-500">{news.source}</span>
      </div>
    </div>
    <ChevronRight className="w-4 h-4 text-stone-600 group-hover:text-stone-400 shrink-0" />
  </a>
);

// === 主组件 ===

const NewsPage: React.FC = () => {
  // 筛选状态
  const [selectedCategory, setSelectedCategory] = useState<T.NewsCategory | 'all'>('all');
  const [selectedSentiment, setSelectedSentiment] = useState<T.NewsSentiment | 'all'>('all');

  // 数据 hooks
  const { data: allNews, isLoading: isAllLoading, isFetching: isAllFetching } = useAggregatedNews();
  const { data: flashNews = [], isLoading: isFlashLoading } = useNewsFlash(10);
  const { data: sourcesData } = useNewsSources();
  const refreshNews = useRefreshNews();

  // 按分类获取（当选择特定分类时）
  const { data: categoryNews, isLoading: isCategoryLoading } = useNewsByCategory(
    selectedCategory as T.NewsCategory,
    50
  );

  // 决定使用哪个数据源
  const newsItems = useMemo(() => {
    if (selectedCategory !== 'all' && categoryNews) {
      return categoryNews;
    }
    return allNews?.news || [];
  }, [selectedCategory, categoryNews, allNews]);

  // 应用情感筛选
  const filteredNews = useMemo(() => {
    if (selectedSentiment === 'all') return newsItems;
    return newsItems.filter((n) => n.sentiment === selectedSentiment);
  }, [newsItems, selectedSentiment]);

  const isLoading = isAllLoading || (selectedCategory !== 'all' && isCategoryLoading);
  const isRefreshing = isAllFetching || refreshNews.isPending;

  // 刷新处理
  const handleRefresh = async () => {
    await refreshNews.mutateAsync();
  };

  // 分类列表
  const categories: (T.NewsCategory | 'all')[] = ['all', ...Object.keys(CATEGORY_LABELS) as T.NewsCategory[]];

  return (
    <PageLayout
      title="News Aggregator"
      subtitle={sourcesData ? `${(sourcesData as any).total_sources} 个新闻源` : '多源聚合新闻'}
      icon={Newspaper}
      iconColor="text-orange-400"
      iconBgColor="bg-orange-500/10"
      variant="dashboard"
      noPadding
      actions={[
        {
          label: '刷新',
          icon: RefreshCw,
          onClick: handleRefresh,
          loading: isRefreshing,
          variant: 'secondary',
        },
      ]}
    >
      {/* Filters */}
      <div className="shrink-0 px-6 py-3 border-b border-border bg-surface-raised/30">
        <div className="flex items-center gap-4 overflow-x-auto custom-scrollbar pb-1">
          <div className="flex items-center gap-2 shrink-0">
            <Filter className="w-4 h-4 text-stone-500" />
            <span className="text-xs text-stone-500">分类:</span>
          </div>
          <div className="flex gap-1">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1.5 text-xs rounded-lg whitespace-nowrap transition-colors ${
                  selectedCategory === cat
                    ? 'bg-accent text-white'
                    : 'bg-surface-overlay/50 text-stone-400 hover:bg-surface-overlay hover:text-white'
                }`}
              >
                {cat === 'all' ? '全部' : CATEGORY_LABELS[cat]}
              </button>
            ))}
          </div>

          <div className="h-6 w-px bg-border-strong shrink-0" />

          <div className="flex items-center gap-2 shrink-0">
            <span className="text-xs text-stone-500">情感:</span>
          </div>
          <div className="flex gap-1">
            {(['all', 'positive', 'negative', 'neutral'] as const).map((sent) => (
              <button
                key={sent}
                onClick={() => setSelectedSentiment(sent)}
                className={`px-3 py-1.5 text-xs rounded-lg whitespace-nowrap transition-colors flex items-center gap-1 ${
                  selectedSentiment === sent
                    ? 'bg-accent text-white'
                    : 'bg-surface-overlay/50 text-stone-400 hover:bg-surface-overlay hover:text-white'
                }`}
              >
                {sent === 'all' && '全部'}
                {sent === 'positive' && <><TrendingUp className="w-3 h-3" />利好</>}
                {sent === 'negative' && <><TrendingDown className="w-3 h-3" />利空</>}
                {sent === 'neutral' && <><Minus className="w-3 h-3" />中性</>}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden flex">
        {/* Main News List */}
        <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="w-8 h-8 animate-spin text-accent" />
            </div>
          ) : filteredNews.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-stone-500">
              <AlertCircle className="w-12 h-12 mb-3" />
              <p>暂无新闻数据</p>
              <p className="text-sm mt-1">尝试刷新或切换筛选条件</p>
            </div>
          ) : (
            <div className="grid gap-4 pb-10">
              {filteredNews.map((news) => (
                <NewsCard key={news.id} news={news} />
              ))}
            </div>
          )}
        </div>

        {/* Flash News Sidebar */}
        <aside className="w-80 shrink-0 border-l border-border bg-surface-raised/30 overflow-hidden flex flex-col">
          <div className="p-4 border-b border-border">
            <h2 className="text-white font-medium flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" />
              快讯
            </h2>
            <p className="text-xs text-stone-500 mt-1">实时市场快讯</p>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar">
            {isFlashLoading ? (
              <div className="flex items-center justify-center py-10">
                <Loader2 className="w-5 h-5 animate-spin text-stone-400" />
              </div>
            ) : flashNews.length === 0 ? (
              <div className="text-center py-10 text-stone-500 text-sm">
                暂无快讯
              </div>
            ) : (
              flashNews.map((news) => (
                <FlashNewsItem key={news.id} news={news} />
              ))
            )}
          </div>
        </aside>
      </div>
    </PageLayout>
  );
};

export default NewsPage;
