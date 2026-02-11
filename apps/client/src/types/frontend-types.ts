/**
 * 前端专用类型定义
 *
 * 分为两部分：
 * 1. 纯前端类型 — 后端不存在对应 schema，永久保留在此文件
 * 2. 待迁移类型 — 后端 schema 已定义（api/schemas/），等 api.ts 重新生成后
 *    切换为 Schemas['xxx'] 并从此文件移除
 */

import type { CorrelationResult, NewsCategory, NewsSentiment } from './schema';

// ============================================================
// 第一部分：纯前端类型（后端无对应 schema）
// ============================================================

/**
 * 市场状态（Dashboard 顶栏展示）
 */
export interface MarketStatus {
  sentiment: 'Bullish' | 'Bearish' | 'Neutral';
  lastUpdated: string;
  activeAgents: number;
}

/**
 * 快讯新闻
 */
export interface FlashNews {
  id: string;
  time: string;
  headline: string;
  impact: 'High' | 'Medium' | 'Low';
  sentiment: 'Positive' | 'Negative';
  relatedSymbols: string[];
}

/**
 * 市场机会（Scout Agent 返回）
 */
export interface MarketOpportunity {
  symbol: string;
  name: string;
  market: 'US' | 'HK' | 'CN';
  reason: string;
  score: number;
}

/**
 * 投资组合分析结果
 */
export interface PortfolioAnalysisResult {
  correlation: CorrelationResult;
  diversification_score: number;
  risk_clusters: Array<{
    stocks: string[];
    avg_correlation: number;
    risk_level: string;
  }>;
  recommendations: string[];
}

/**
 * 市场情绪数据
 */
export interface MarketSentiment {
  global_sentiment: string;
  risk_level: number;
  regions: Record<string, {
    indices_count: number;
    avg_change_percent: number;
    sentiment: string;
  }>;
  updated_at: string;
}

/**
 * 聚合新闻条目
 */
export interface AggregatedNewsItem {
  id: string;
  title: string;
  summary?: string | null;
  source: string;
  url: string;
  category: NewsCategory;
  sentiment: NewsSentiment;
  symbols: string[];
  published_at: string;
  fetched_at: string;
}

/**
 * 灰度发布设置
 */
export interface RolloutSettings {
  subgraph_rollout_percentage: number;
  subgraph_force_enabled_users: string[];
}

// ============================================================
// 第二部分：待迁移类型
// 后端 schema 已定义于 api/schemas/{alternative,vision,supply_chain}.py
// 重新生成 api.ts 后，将这些类型切换为 Schemas['xxx'] 并从此处移除
// ============================================================

// --- 另类数据（对应 api/schemas/alternative.py） ---

export interface AHPremiumStock {
  a_code: string;
  h_code: string;
  name: string;
  a_price: number;
  h_price: number;
  premium_rate: number;
  premium_pct: number;
}

export interface AHPremiumStats {
  avg_premium_pct: number;
  max_premium_pct: number;
  min_premium_pct: number;
  median_premium_pct: number;
  discount_count: number;
  premium_count: number;
  total_count: number;
}

export interface AHPremiumListResponse {
  timestamp: string;
  total: number;
  stocks: AHPremiumStock[];
  stats: AHPremiumStats;
}

export interface ArbitrageSignal {
  signal: string;
  description: string;
  percentile?: number;
  current_premium_pct?: number;
  historical_avg?: number;
}

export interface AHPremiumDetailResponse {
  found: boolean;
  current: AHPremiumStock;
  history: Array<{ date: string; ratio: number }>;
  signal: ArbitrageSignal;
  timestamp: string;
}

export interface PatentNewsItem {
  title: string;
  body: string;
  url: string;
}

export interface PatentAnalysisResponse {
  symbol: string;
  company_name: string;
  timestamp: string;
  patent_news: PatentNewsItem[];
  tech_trends: PatentNewsItem[];
  analysis_hint: string;
}

// --- Vision 分析（对应 api/schemas/vision.py） ---

export interface VisionKeyDataPoint {
  label: string;
  value: string;
}

export interface VisionAnalysisResult {
  chart_type: string;
  time_range?: string;
  key_data_points?: VisionKeyDataPoint[];
  trend: string;
  trend_description?: string;
  patterns?: string[];
  support_levels?: number[];
  resistance_levels?: number[];
  anomalies?: string[];
  signals?: string[];
  summary: string;
  recommendation?: string;
  confidence: number;
  raw_analysis?: string;
}

export interface VisionAnalysisResponse {
  success: boolean;
  symbol: string;
  description: string;
  analysis: VisionAnalysisResult;
  timestamp: string;
  image_size: number;
  processed_size: number;
  error?: string;
}

// --- 产业链（对应 api/schemas/supply_chain.py） ---

export interface ChainSummary {
  id: string;
  name: string;
  description: string;
  total_companies: number;
  segments: {
    upstream: number;
    midstream: number;
    downstream: number;
  };
}

export interface ChainListResponse {
  chains: ChainSummary[];
  total: number;
  timestamp: string;
}

export interface GraphNode {
  id: string;
  type: 'chain' | 'segment' | 'company';
  label: string;
  position: 'center' | 'upstream' | 'midstream' | 'downstream';
  symbol?: string;
  code?: string;
  segment?: string;
  price?: number | null;
  change_pct?: number | null;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
  style?: string;
}

export interface ChainGraphResponse {
  chain_id: string;
  chain_name: string;
  description: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: {
    total_nodes: number;
    total_edges: number;
    upstream_count: number;
    midstream_count: number;
    downstream_count: number;
  };
  timestamp: string;
}

export interface ChainPosition {
  chain_id: string;
  chain_name: string;
  position: string;
  segment: string;
  full_name: string;
}

export interface StockChainPositionResponse {
  symbol: string;
  found: boolean;
  chains?: ChainPosition[];
  chain_count?: number;
  industry_info?: Record<string, unknown>;
  suggestion?: string;
  timestamp?: string;
}

export interface SupplyChainImpact {
  chain_id: string;
  chain_name: string;
  position: string;
  segment: string;
  upstream_companies: string[];
  downstream_companies: string[];
  impact_analysis: {
    upstream_risk: string;
    downstream_demand: string;
    position_advantage: string;
  };
}

export interface SupplyChainImpactResponse {
  symbol: string;
  analyses: SupplyChainImpact[];
  timestamp: string;
}
