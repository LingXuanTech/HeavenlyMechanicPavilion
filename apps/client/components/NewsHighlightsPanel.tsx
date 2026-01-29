/**
 * 新闻摘要面板组件
 *
 * 在 Dashboard 中显示最新新闻摘要，点击可跳转到完整新闻页
 */
import React from 'react';
import { Link } from 'react-router-dom';
import {
  Newspaper,
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronRight,
  Clock,
  RefreshCw,
  Loader2,
  ExternalLink,
} from 'lucide-react';
import { useAggregatedNews, useRefreshNews } from '../hooks';
import type { AggregatedNewsItem, NewsSentiment } from '../types';

const SentimentIcon: React.FC<{ sentiment: NewsSentiment }> = ({ sentiment }) => {
  switch (sentiment) {
    case 'positive':
      return <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />;
    case 'negative':
      return <TrendingDown className="w-3.5 h-3.5 text-red-400" />;
    default:
      return <Minus className="w-3.5 h-3.5 text-gray-400" />;
  }
};

const TimeAgo: React.FC<{ timestamp: string }> = ({ timestamp }) => {
  const getTimeAgo = (dateStr: string): string => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diff < 60) return '刚刚';
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`;
    return `${Math.floor(diff / 86400)}天前`;
  };

  return (
    <span className="text-[10px] text-gray-500 flex items-center gap-0.5">
      <Clock className="w-2.5 h-2.5" />
      {getTimeAgo(timestamp)}
    </span>
  );
};

const NewsItem: React.FC<{ news: AggregatedNewsItem }> = ({ news }) => (
  <a
    href={news.url}
    target="_blank"
    rel="noopener noreferrer"
    className="block p-2.5 hover:bg-gray-800/50 rounded-lg transition-colors group"
  >
    <div className="flex items-start gap-2">
      <SentimentIcon sentiment={news.sentiment} />
      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-200 group-hover:text-white line-clamp-2 leading-relaxed">
          {news.title}
        </p>
        <div className="flex items-center gap-2 mt-1.5">
          <span className="text-[10px] text-gray-500">{news.source}</span>
          <TimeAgo timestamp={news.published_at} />
        </div>
      </div>
      <ExternalLink className="w-3 h-3 text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
    </div>
  </a>
);

interface NewsHighlightsPanelProps {
  className?: string;
}

const NewsHighlightsPanel: React.FC<NewsHighlightsPanelProps> = ({ className = '' }) => {
  const { data: newsData, isLoading, isFetching } = useAggregatedNews();
  const refreshNews = useRefreshNews();

  const recentNews = newsData?.news?.slice(0, 8) || [];
  const isRefreshing = isFetching || refreshNews.isPending;

  const handleRefresh = () => {
    refreshNews.mutate();
  };

  return (
    <div className={`bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden ${className}`}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Newspaper className="w-4 h-4 text-orange-400" />
          <h3 className="text-sm font-medium text-white">最新资讯</h3>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="p-1 hover:bg-gray-800 rounded transition-colors disabled:opacity-50"
            title="刷新"
          >
            {isRefreshing ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-gray-400" />
            ) : (
              <RefreshCw className="w-3.5 h-3.5 text-gray-400" />
            )}
          </button>
          <Link
            to="/news"
            className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-0.5"
          >
            更多
            <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* News List */}
      <div className="divide-y divide-gray-800/50">
        {isLoading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
          </div>
        ) : recentNews.length === 0 ? (
          <div className="py-10 text-center text-gray-500 text-xs">
            暂无新闻
          </div>
        ) : (
          recentNews.map((news) => (
            <NewsItem key={news.id} news={news} />
          ))
        )}
      </div>

      {/* Footer */}
      {recentNews.length > 0 && (
        <div className="px-4 py-2 border-t border-gray-800 bg-gray-900/30">
          <Link
            to="/news"
            className="flex items-center justify-center gap-1 text-xs text-gray-400 hover:text-white transition-colors"
          >
            查看全部新闻
            <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}
    </div>
  );
};

export default NewsHighlightsPanel;
