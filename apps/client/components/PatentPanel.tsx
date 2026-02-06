/**
 * 专利监控面板组件
 *
 * 展示公司专利信息和技术趋势分析。
 */

import React from 'react';
import { usePatentAnalysis } from '../hooks/useAlternativeData';
import { FileText, ExternalLink, RefreshCw, Lightbulb, Search } from 'lucide-react';

interface PatentPanelProps {
  symbol: string;
  companyName?: string;
  className?: string;
}

const PatentPanel: React.FC<PatentPanelProps> = ({ symbol, companyName, className = '' }) => {
  const { data, isLoading, error, refetch } = usePatentAnalysis(symbol, companyName);

  if (!symbol) {
    return (
      <div className={`bg-surface-raised rounded-lg p-4 ${className}`}>
        <div className="text-stone-500 text-sm text-center py-4">请选择股票查看专利信息</div>
      </div>
    );
  }

  return (
    <div className={`bg-surface-raised rounded-lg ${className}`}>
      {/* 头部 */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-purple-400" />
          <h3 className="text-white font-medium">专利监控</h3>
          <span className="text-xs text-stone-400">
            {data?.company_name || symbol}
          </span>
        </div>
        <button
          onClick={() => refetch()}
          className="p-1 text-stone-400 hover:text-stone-50 transition-colors"
          title="刷新"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* 内容 */}
      <div className="p-4 space-y-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-5 h-5 text-stone-500 animate-spin" />
          </div>
        ) : error ? (
          <div className="text-red-400 text-sm">加载失败: {(error as Error).message}</div>
        ) : (
          <>
            {/* 专利新闻 */}
            <Section
              icon={<Search className="w-4 h-4 text-accent" />}
              title="专利动态"
              items={data?.patent_news || []}
              emptyText="暂无专利相关新闻"
            />

            {/* 技术趋势 */}
            <Section
              icon={<Lightbulb className="w-4 h-4 text-yellow-400" />}
              title="技术趋势"
              items={data?.tech_trends || []}
              emptyText="暂无技术趋势数据"
            />
          </>
        )}
      </div>
    </div>
  );
};

// ============ 子组件 ============

interface SectionProps {
  icon: React.ReactNode;
  title: string;
  items: Array<{ title: string; body: string; url: string }>;
  emptyText: string;
}

const Section: React.FC<SectionProps> = ({ icon, title, items, emptyText }) => (
  <div>
    <div className="flex items-center gap-2 mb-2">
      {icon}
      <h4 className="text-stone-300 text-sm font-medium">{title}</h4>
      <span className="text-xs text-stone-600">({items.length})</span>
    </div>

    {items.length === 0 ? (
      <div className="text-stone-600 text-xs py-2">{emptyText}</div>
    ) : (
      <div className="space-y-2">
        {items.map((item, idx) => (
          <div
            key={idx}
            className="bg-surface-overlay/50 rounded p-2.5 hover:bg-surface-overlay transition-colors"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="text-white text-xs font-medium truncate">{item.title}</div>
                <div className="text-stone-400 text-xs mt-1 line-clamp-2">{item.body}</div>
              </div>
              {item.url && (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-stone-500 hover:text-accent flex-shrink-0"
                  title="查看原文"
                >
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    )}
  </div>
);

export default PatentPanel;
