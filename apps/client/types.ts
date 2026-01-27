export enum SignalType {
  STRONG_BUY = 'Strong Buy',
  BUY = 'Buy',
  HOLD = 'Hold',
  SELL = 'Sell',
  STRONG_SELL = 'Strong Sell'
}

export interface Stock {
  symbol: string;
  name: string;
  market: 'US' | 'HK' | 'CN';
}

export interface StockPrice {
  price: number;
  change: number;
  changePercent: number;
  history: { time: string; value: number }[];
}

export interface WebSource {
  uri: string;
  title: string;
}

export interface CatalystEvent {
  name: string;
  date: string;
  impact: 'Positive' | 'Negative' | 'Neutral';
}

export interface PriceLevels {
  support: number;
  resistance: number;
}

export interface NewsItem {
  headline: string;
  sentiment: 'Positive' | 'Negative' | 'Neutral';
  summary: string;
}

export interface PeerData {
  name: string;
  comparison: string; // e.g. "Outperforming", "Lagging"
}

export interface TradeSetup {
  entryZone: string; 
  targetPrice: number;
  stopLossPrice: number;
  rewardToRiskRatio: number; 
  invalidationCondition: string; 
}

export interface MacroContext {
  relevantIndex: string; 
  correlation: 'High' | 'Medium' | 'Low' | 'Inverse';
  environment: 'Tailwind' | 'Headwind' | 'Neutral'; 
  summary: string;
}

// --- NEW STRUCTURES FOR MULTI-AGENT SIMULATION ---

export interface DebatePoint {
  argument: string;
  evidence: string;
  weight: 'High' | 'Medium' | 'Low';
}

export interface ResearcherDebate {
  bull: {
    thesis: string;
    points: DebatePoint[];
  };
  bear: {
    thesis: string;
    points: DebatePoint[];
  };
  winner: 'Bull' | 'Bear' | 'Neutral';
  conclusion: string;
}

export interface RiskAssessment {
  score: number; // 0 (Safe) to 10 (Extreme Risk)
  volatilityStatus: 'Low' | 'Moderate' | 'High' | 'Extreme';
  liquidityConcerns: boolean;
  maxDrawdownRisk: string; // Estimated downside
  verdict: 'Approved' | 'Caution' | 'Rejected';
}

export interface AgentAnalysis {
  symbol: string;
  timestamp: string;
  signal: SignalType;
  confidence: number;
  reasoning: string; // Final synthesis by Fund Manager
  
  // Simulation Components
  debate: ResearcherDebate;
  riskAssessment: RiskAssessment;
  
  // Supporting Data
  catalysts?: CatalystEvent[];
  priceLevels?: PriceLevels;
  technicalIndicators: {
    rsi: number;
    macd: string;
    trend: 'Bullish' | 'Bearish' | 'Neutral';
  };
  newsAnalysis: NewsItem[];
  peers: PeerData[];
  tradeSetup?: TradeSetup; 
  macroContext?: MacroContext; 
  webSources?: WebSource[];
}

export interface MarketIndex {
  name: string;
  value: number;
  change: number;
  changePercent: number;
}

export interface GlobalMarketAnalysis {
  sentiment: 'Bullish' | 'Bearish' | 'Neutral' | 'Mixed';
  summary: string;
  indices: MarketIndex[];
  lastUpdated: string;
}

export interface MarketStatus {
  sentiment: 'Bullish' | 'Bearish' | 'Neutral';
  lastUpdated: Date;
  activeAgents: number;
}

export interface ChatMessage {
  role: 'user' | 'model';
  text: string;
}

export interface MarketOpportunity {
  symbol: string;
  name: string;
  market: 'US' | 'HK' | 'CN';
  reason: string;
  score: number; 
}

export interface FlashNews {
  id: string;
  time: string;
  headline: string;
  impact: 'High' | 'Medium' | 'Low';
  sentiment: 'Positive' | 'Negative';
  relatedSymbols: string[];
}

// ============ Memory Service Types ============

export interface AnalysisMemory {
  symbol: string;
  date: string;
  signal: string;
  confidence: number;
  reasoning_summary: string;
  debate_winner?: string;
  risk_score?: number;
  entry_price?: number;
  target_price?: number;
  stop_loss?: number;
}

export interface MemoryRetrievalResult {
  memory: AnalysisMemory;
  similarity: number;
  days_ago: number;
}

export interface ReflectionReport {
  symbol: string;
  historical_analyses: MemoryRetrievalResult[];
  patterns: string[];
  lessons: string[];
  confidence_adjustment: number;
}

// ============ Market Watcher Types ============

export type MarketRegion = 'CN' | 'HK' | 'US' | 'GLOBAL';
export type IndexStatus = 'trading' | 'closed' | 'pre_market' | 'after_hours' | 'unknown';

export interface MarketWatcherIndex {
  code: string;
  name: string;
  name_en: string;
  region: MarketRegion;
  current: number;
  change: number;
  change_percent: number;
  high?: number;
  low?: number;
  open?: number;
  prev_close?: number;
  volume?: number;
  status: IndexStatus;
  updated_at: string;
}

export interface MarketWatcherOverview {
  indices: MarketWatcherIndex[];
  global_sentiment: 'Bullish' | 'Bearish' | 'Neutral';
  risk_level: number;
  updated_at: string;
}

export interface MarketSentimentData {
  global_sentiment: string;
  risk_level: number;
  regions: Record<string, {
    indices_count: number;
    avg_change_percent: number;
    sentiment: string;
  }>;
  updated_at: string;
}

// ============ News Aggregator Types ============

export type NewsCategory = 'market' | 'stock' | 'macro' | 'policy' | 'earnings' | 'ipo' | 'forex' | 'crypto' | 'general';
export type NewsSentiment = 'positive' | 'negative' | 'neutral';

export interface AggregatedNewsItem {
  id: string;
  title: string;
  summary?: string;
  url: string;
  source: string;
  category: NewsCategory;
  sentiment: NewsSentiment;
  symbols: string[];
  published_at: string;
  fetched_at: string;
}

export interface NewsAggregateResult {
  news: AggregatedNewsItem[];
  total: number;
  sources: string[];
  updated_at: string;
}

// ============ Health Monitor Types ============

export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy' | 'unknown';

export interface ComponentHealth {
  name: string;
  status: HealthStatus;
  message?: string;
  latency_ms?: number;
  last_check: string;
}

export interface SystemMetrics {
  cpu_percent: number;
  memory_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
}

export interface ErrorRecord {
  timestamp: string;
  component: string;
  error_type: string;
  message: string;
  count: number;
}

export interface HealthReport {
  overall_status: HealthStatus;
  components: ComponentHealth[];
  system_metrics: SystemMetrics;
  recent_errors: ErrorRecord[];
  uptime_seconds: number;
  checked_at: string;
}

export interface UptimeInfo {
  start_time: string;
  uptime_seconds: number;
  uptime_formatted: string;
  current_time: string;
}