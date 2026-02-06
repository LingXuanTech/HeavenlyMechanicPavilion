/**
 * 产业链可视化组件
 *
 * 使用 CSS Grid + Flexbox 实现产业链图谱展示。
 * 节点颜色表示涨跌，支持点击交互。
 */

import React, { useState } from 'react';
import { useChainGraph } from '../hooks/useSupplyChain';
import type { GraphNode } from '../hooks/useSupplyChain';
import {
  RefreshCw,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';

interface SupplyChainGraphProps {
  chainId: string;
  onCompanyClick?: (symbol: string) => void;
  className?: string;
}

const SupplyChainGraph: React.FC<SupplyChainGraphProps> = ({
  chainId,
  onCompanyClick,
  className = '',
}) => {
  const { data, isLoading, error } = useChainGraph(chainId);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className={`bg-surface-raised rounded-lg p-8 flex items-center justify-center ${className}`}>
        <RefreshCw className="w-6 h-6 text-stone-500 animate-spin" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className={`bg-surface-raised rounded-lg p-4 ${className}`}>
        <div className="text-red-400 text-sm">
          加载失败: {(error as Error)?.message || '未知错误'}
        </div>
      </div>
    );
  }

  // 按位置分组节点
  const segments = {
    upstream: data.nodes.filter((n) => n.position === 'upstream' && n.type === 'segment'),
    midstream: data.nodes.filter((n) => n.position === 'midstream' && n.type === 'segment'),
    downstream: data.nodes.filter((n) => n.position === 'downstream' && n.type === 'segment'),
  };

  const companies = data.nodes.filter((n) => n.type === 'company');

  return (
    <div className={`bg-surface-raised rounded-lg ${className}`}>
      {/* 头部 */}
      <div className="p-4 border-b border-border">
        <h3 className="text-white font-medium">{data.chain_name}</h3>
        <p className="text-stone-500 text-xs mt-1">{data.description}</p>
        <div className="flex items-center gap-4 mt-2 text-xs text-stone-600">
          <span>节点: {data.stats.total_nodes}</span>
          <span>上游: {data.stats.upstream_count}</span>
          <span>中游: {data.stats.midstream_count}</span>
          <span>下游: {data.stats.downstream_count}</span>
        </div>
      </div>

      {/* 产业链流程图 */}
      <div className="p-4 overflow-x-auto">
        <div className="flex items-start gap-4 min-w-[800px]">
          {/* 上游 */}
          <ChainColumn
            title="上游"
            titleColor="text-accent"
            bgColor="bg-blue-900/10"
            borderColor="border-blue-800/30"
            segments={segments.upstream}
            companies={companies}
            edges={data.edges}
            hoveredNode={hoveredNode}
            onHover={setHoveredNode}
            onCompanyClick={onCompanyClick}
          />

          {/* 箭头 */}
          <div className="flex items-center self-center py-8">
            <ArrowRight className="w-6 h-6 text-stone-600" />
          </div>

          {/* 中游 */}
          <ChainColumn
            title="中游"
            titleColor="text-yellow-400"
            bgColor="bg-yellow-900/10"
            borderColor="border-yellow-800/30"
            segments={segments.midstream}
            companies={companies}
            edges={data.edges}
            hoveredNode={hoveredNode}
            onHover={setHoveredNode}
            onCompanyClick={onCompanyClick}
          />

          {/* 箭头 */}
          <div className="flex items-center self-center py-8">
            <ArrowRight className="w-6 h-6 text-stone-600" />
          </div>

          {/* 下游 */}
          <ChainColumn
            title="下游"
            titleColor="text-green-400"
            bgColor="bg-green-900/10"
            borderColor="border-green-800/30"
            segments={segments.downstream}
            companies={companies}
            edges={data.edges}
            hoveredNode={hoveredNode}
            onHover={setHoveredNode}
            onCompanyClick={onCompanyClick}
          />
        </div>
      </div>
    </div>
  );
};

// ============ 子组件 ============

interface ChainColumnProps {
  title: string;
  titleColor: string;
  bgColor: string;
  borderColor: string;
  segments: GraphNode[];
  companies: GraphNode[];
  edges: Array<{ source: string; target: string; relation: string }>;
  hoveredNode: string | null;
  onHover: (id: string | null) => void;
  onCompanyClick?: (symbol: string) => void;
}

const ChainColumn: React.FC<ChainColumnProps> = ({
  title,
  titleColor,
  bgColor,
  borderColor,
  segments,
  companies,
  edges,
  hoveredNode,
  onHover,
  onCompanyClick,
}) => {
  const getCompaniesForSegment = (segmentId: string) =>
    companies.filter((c) =>
      edges.some((e) => e.source === segmentId && e.target === c.id)
    );

  return (
    <div className={`flex-1 min-w-[240px] rounded-lg border ${borderColor} ${bgColor} p-3`}>
      <h4 className={`text-sm font-medium ${titleColor} mb-3 text-center`}>{title}</h4>

      <div className="space-y-3">
        {segments.map((segment) => {
          const segCompanies = getCompaniesForSegment(segment.id);

          return (
            <div key={segment.id} className="bg-surface-overlay/50 rounded p-2">
              <div className="text-stone-300 text-xs font-medium mb-1.5 px-1">
                {segment.label}
              </div>
              <div className="space-y-1">
                {segCompanies.map((company) => (
                  <CompanyNode
                    key={company.id}
                    node={company}
                    isHovered={hoveredNode === company.id}
                    onHover={onHover}
                    onClick={onCompanyClick}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const CompanyNode: React.FC<{
  node: GraphNode;
  isHovered: boolean;
  onHover: (id: string | null) => void;
  onClick?: (symbol: string) => void;
}> = ({ node, isHovered, onHover, onClick }) => {
  const changePct = node.change_pct;
  const changeColor =
    changePct && changePct > 0
      ? 'text-red-400'
      : changePct && changePct < 0
        ? 'text-green-400'
        : 'text-stone-500';

  const ChangeIcon =
    changePct && changePct > 0
      ? TrendingUp
      : changePct && changePct < 0
        ? TrendingDown
        : Minus;

  return (
    <div
      className={`flex items-center justify-between px-2 py-1 rounded text-xs cursor-pointer transition-colors ${
        isHovered ? 'bg-surface-muted' : 'hover:bg-surface-muted/50'
      }`}
      onMouseEnter={() => onHover(node.id)}
      onMouseLeave={() => onHover(null)}
      onClick={() => node.symbol && onClick?.(node.symbol)}
    >
      <div className="flex items-center gap-1.5 min-w-0">
        <span className="text-white truncate">{node.label}</span>
        {node.code && <span className="text-stone-600 flex-shrink-0">{node.code}</span>}
      </div>
      <div className="flex items-center gap-1 flex-shrink-0 ml-2">
        {node.price && (
          <span className="text-stone-400">{node.price.toFixed(2)}</span>
        )}
        {changePct !== null && changePct !== undefined && (
          <span className={`flex items-center gap-0.5 ${changeColor}`}>
            <ChangeIcon className="w-2.5 h-2.5" />
            {Math.abs(changePct).toFixed(1)}%
          </span>
        )}
      </div>
    </div>
  );
};

export default SupplyChainGraph;
