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

// A股市场专用分析数据
export interface RetailSentimentAnalysis {
  fomoLevel: 'High' | 'Medium' | 'Low' | 'None';
  fudLevel: 'High' | 'Medium' | 'Low' | 'None';
  overallMood: 'Greedy' | 'Neutral' | 'Fearful';
  keyIndicators: string[];
}

export interface PolicyAnalysis {
  recentPolicies: string[];
  impact: 'Positive' | 'Neutral' | 'Negative';
  riskFactors: string[];
  opportunities: string[];
}

export interface ChinaMarketAnalysis {
  retailSentiment: RetailSentimentAnalysis;
  policyAnalysis: PolicyAnalysis;
}

// ============ Agentic UI Hints ============
// UI Hints 由 AI 生成，指导前端如何自适应展示分析结果

export type AlertLevel = 'none' | 'info' | 'warning' | 'critical';
export type VisualStyle = 'default' | 'prominent' | 'subtle' | 'highlight';

/** AI 生成的 UI 展示提示 */
export interface UIHints {
  // 警示级别
  alertLevel: AlertLevel;
  alertMessage?: string;

  // 突出显示的区域
  highlightSections: Array<'signal' | 'risk' | 'debate' | 'trade_setup' | 'news' | 'planner'>;

  // 关键指标（应在顶部突出显示）
  keyMetrics: string[];

  // 数据质量问题（来自 DataValidator）
  dataQualityIssues?: string[];

  // 置信度可视化建议
  confidenceDisplay: 'gauge' | 'progress' | 'badge' | 'number';

  // 辩论展示建议
  debateDisplay: {
    showWinnerBadge: boolean;
    emphasisLevel: VisualStyle;
    expandByDefault: boolean;
  };

  // Planner 决策透明度（是否展示分析师选择逻辑）
  showPlannerReasoning: boolean;
  plannerInsight?: string;

  // 动态建议（如"高风险，建议谨慎"）
  actionSuggestions: string[];

  // 相关历史案例数量（来自分层记忆）
  historicalCasesCount?: number;

  // 分析级别标记
  analysisLevel: 'L1' | 'L2';

  // 市场特殊提示（如 A股政策敏感期）
  marketSpecificHints?: string[];
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
  anchor_script?: string; // AI-generated TTS script
  chinaMarket?: ChinaMarketAnalysis; // A股市场专用分析（仅 CN 市场股票）

  // Agentic UI Hints（AI 生成的展示指导）
  uiHints?: UIHints;

  // 诊断信息
  diagnostics?: {
    task_id?: string;
    elapsed_seconds?: number;
    analysts_used?: string[];
    planner_decision?: string;
  };
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

// ============ API Response Types (Backend snake_case) ============
// 这些类型对应后端 API 的原始响应格式

/** 后端返回的 K 线数据 */
export interface KlineDataResponse {
  datetime: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

/** 后端返回的价格数据 */
export interface StockPriceResponse {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  timestamp: string;
  market: string;
}

/** 后端返回的全球市场指数 */
export interface GlobalIndexResponse {
  name: string;
  value: number;
  change: number;
  change_percent: number;
}

/** 后端返回的全球市场数据 */
export interface GlobalMarketResponse {
  sentiment?: string;
  summary?: string;
  indices: GlobalIndexResponse[];
}

/** 后端返回的记忆搜索结果 */
export interface MemorySearchResponse {
  query: string;
  results: AnalysisMemory[];
  count: number;
}

/** 后端返回的新闻源信息 */
export interface NewsSourcesResponse {
  rss_feeds: Array<{ name: string; url: string; category: string }>;
  finnhub_enabled: boolean;
  total_sources: number;
}

/** 后端返回的错误列表 */
export interface HealthErrorsResponse {
  errors: ErrorRecord[];
  total: number;
}

/** 服务状态响应 */
export interface ServiceStatusResponse {
  status: string;
  message?: string;
}

/** 区域情绪数据 */
export interface RegionSentimentInfo {
  indices_count: number;
  avg_change_percent: number;
  sentiment: string;
}

/** 组件健康信息 */
export interface ComponentHealthInfo {
  status: string;
  message?: string;
  latency_ms?: number;
}

/** SSE 事件数据类型 */
export type SSEEventData = Record<string, unknown>;

// ============ 北向资金类型 (A股特有) ============

/** 北向资金流向 */
export interface NorthMoneyFlow {
  date: string;
  shanghai_connect: number;  // 沪股通（亿元）
  shenzhen_connect: number;  // 深股通（亿元）
  total_net: number;         // 北向合计（亿元）
  cumulative_net: number;    // 累计净流入（亿元）
  shanghai_buy: number;      // 沪股通买入
  shanghai_sell: number;     // 沪股通卖出
  shenzhen_buy: number;      // 深股通买入
  shenzhen_sell: number;     // 深股通卖出
}

/** 北向资金历史记录 */
export interface NorthMoneyHistory {
  date: string;
  total_net: number;
  shanghai_connect: number;
  shenzhen_connect: number;
}

/** 北向资金持股 */
export interface NorthMoneyHolding {
  symbol: string;
  name: string;
  holding_shares: number;     // 持股数量（万股）
  holding_value: number;      // 持股市值（亿元）
  holding_ratio: number;      // 持股比例（%）
  change_shares: number;      // 持股变动（万股）
  change_ratio: number;       // 变动比例（%）
}

/** 北向资金 TOP 股票 */
export interface NorthMoneyTopStock {
  symbol: string;
  name: string;
  net_buy: number;            // 净买入（亿元）
  buy_amount: number;         // 买入金额（亿元）
  sell_amount: number;        // 卖出金额（亿元）
  holding_ratio: number;      // 持股比例（%）
}

/** 北向资金概览 */
export interface NorthMoneySummary {
  date: string;
  flow: NorthMoneyFlow;
  trend: 'Inflow' | 'Outflow' | 'Neutral';
  trend_days: number;         // 连续流入/流出天数
  recent_history: NorthMoneyHistory[];
  top_buys: NorthMoneyTopStock[];
  top_sells: NorthMoneyTopStock[];
}

/** 盘中分时流向数据点 */
export interface IntradayFlowPoint {
  time: string;                // 时间 (HH:MM)
  sh_connect: number;          // 沪股通净流入（亿元）
  sz_connect: number;          // 深股通净流入（亿元）
  total: number;               // 北向资金净流入合计（亿元）
  cumulative_total: number;    // 累计净流入（亿元）
}

/** 盘中实时流向汇总 */
export interface IntradayFlowSummary {
  date: string;
  last_update: string;         // 最后更新时间
  current_total: number;       // 当前累计净流入（亿元）
  flow_points: IntradayFlowPoint[];
  peak_inflow: number;         // 盘中峰值净流入
  peak_outflow: number;        // 盘中峰值净流出
  flow_volatility: number;     // 流向波动率
  momentum: 'accelerating' | 'decelerating' | 'stable';
}

/** 北向资金异常信号 */
export interface NorthMoneyAnomaly {
  timestamp: string;
  anomaly_type: 'sudden_inflow' | 'sudden_outflow' | 'reversal' | 'volume_spike' | 'concentration';
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  affected_stocks: string[];
  flow_change: number;         // 流向变化（亿元）
  recommendation: string;      // 操作建议
}

/** 北向资金实时全景 */
export interface NorthMoneyRealtime {
  summary: NorthMoneySummary;
  intraday: IntradayFlowSummary | null;
  anomalies: NorthMoneyAnomaly[];
  index_correlation: Record<string, number> | null;
  is_trading_hours: boolean;
}

/** 北向资金板块流向 */
export interface NorthMoneySectorFlow {
  sector: string;              // 板块名称
  sector_code: string;         // 板块代码
  net_buy: number;             // 净买入金额（亿元）
  stock_count: number;         // 涉及股票数量
  top_stocks: string[];        // TOP 净买入个股
  flow_direction: 'inflow' | 'outflow' | 'neutral';
  change_ratio: number;        // 较昨日变化比例（%）
}

/** 板块轮动信号 */
export interface SectorRotationSignal {
  date: string;
  inflow_sectors: string[];    // 资金流入板块
  outflow_sectors: string[];   // 资金流出板块
  rotation_pattern: 'defensive' | 'aggressive' | 'mixed' | 'broad_inflow' | 'broad_outflow' | 'unclear';
  signal_strength: number;     // 信号强度 0-100
  interpretation: string;      // 信号解读
}

// ============ 龙虎榜类型 (A股特有) ============

/** 龙虎榜席位 */
export interface LHBSeat {
  seat_name: string;
  buy_amount: number;
  sell_amount: number;
  net_amount: number;
  seat_type: '机构' | '游资' | '普通';
  hot_money_name: string | null;
}

/** 龙虎榜股票 */
export interface LHBStock {
  symbol: string;
  name: string;
  close_price: number;
  change_percent: number;
  turnover_rate: number;
  lhb_net_buy: number;
  lhb_buy_amount: number;
  lhb_sell_amount: number;
  reason: string;
  buy_seats: LHBSeat[];
  sell_seats: LHBSeat[];
  institution_net: number;
  hot_money_involved: boolean;
}

/** 知名游资席位 */
export interface HotMoneySeat {
  seat_name: string;
  alias: string;
  style: string;
  recent_stocks: Array<{
    symbol: string;
    name: string;
    action: string;
    amount: number;
  }>;
  win_rate: number | null;
}

/** 龙虎榜概览 */
export interface LHBSummary {
  date: string;
  total_stocks: number;
  total_net_buy: number;
  institution_net_buy: number;
  top_buys: LHBStock[];
  top_sells: LHBStock[];
  hot_money_active: HotMoneySeat[];
}

// ============ 限售解禁类型 (A股特有) ============

/** 解禁股票 */
export interface JiejinStock {
  symbol: string;
  name: string;
  jiejin_date: string;
  jiejin_shares: number;        // 解禁数量（万股）
  jiejin_market_value: number;  // 解禁市值（亿元）
  jiejin_ratio: number;         // 解禁比例（%）
  jiejin_type: string;
  pressure_level: '高' | '中' | '低';
}

/** 解禁日历 */
export interface JiejinCalendar {
  date: string;
  stock_count: number;
  total_shares: number;         // 亿股
  total_market_value: number;   // 亿元
  stocks: JiejinStock[];
}

/** 解禁概览 */
export interface JiejinSummary {
  date_range: string;
  total_stocks: number;
  total_market_value: number;
  daily_average: number;
  high_pressure_stocks: JiejinStock[];
  calendar: JiejinCalendar[];
}

// ============ Prompt 配置类型 ============

/** Agent 分类 */
export type AgentCategory = 'analyst' | 'researcher' | 'manager' | 'risk' | 'trader' | 'synthesizer';

/** Agent Prompt 配置 */
export interface AgentPrompt {
  id: number;
  agent_key: string;
  category: AgentCategory;
  display_name: string;
  description: string;
  system_prompt: string;
  user_prompt_template: string;
  available_variables: string[];
  version: number;
  is_active: boolean;
  updated_at: string;
}

/** Prompt 版本历史 */
export interface PromptVersionHistory {
  version: number;
  change_note: string;
  created_at: string;
  created_by: string;
}

/** Prompt 详情（含版本历史） */
export interface AgentPromptDetail extends AgentPrompt {
  created_at: string;
  version_history: PromptVersionHistory[];
}

/** Prompt 服务状态 */
export interface PromptServiceStatus {
  initialized: boolean;
  prompts_count: number;
  cached_agents: string[];
  last_refresh: string | null;
}

// ============ 分析历史类型 ============

/** 分析历史列表项 */
export interface AnalysisHistoryItem {
  id: number;
  symbol: string;
  date: string;
  signal: string;
  confidence: number;
  created_at: string;
  task_id: string | null;
  status: string;
  elapsed_seconds: number | null;
}

/** 分析任务状态 */
export interface AnalysisTaskStatus {
  task_id: string;
  symbol: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress?: number;
  current_stage?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

// ============ Portfolio 类型 ============

/** 相关性矩阵 */
export interface CorrelationMatrix {
  symbols: string[];
  matrix: number[][];
  period: string;
  calculated_at: string;
}

/** 风险聚类 */
export interface RiskCluster {
  cluster_id: number;
  symbols: string[];
  avg_correlation: number;
  risk_level: 'low' | 'medium' | 'high';
}

/** Portfolio 分析结果 */
export interface PortfolioAnalysisResult {
  symbols: string[];
  correlation: CorrelationMatrix;
  risk_clusters: RiskCluster[];
  diversification_score: number;
  recommendations: string[];
  analyzed_at: string;
}

/** 快速检查结果 */
export interface QuickPortfolioCheck {
  symbols: string[];
  high_correlations: Array<{
    pair: [string, string];
    correlation: number;
  }>;
  risk_warning: boolean;
  message: string;
}

// ============ 宏观经济类型 ============

/** 宏观概览 */
export interface MacroOverview {
  indicators: Record<string, {
    value: number;
    change: number;
    trend: 'up' | 'down' | 'stable';
    updated_at: string;
  }>;
  market_environment: 'favorable' | 'neutral' | 'unfavorable';
  summary: string;
  updated_at: string;
}

/** 宏观影响分析 */
export interface MacroImpactAnalysis {
  market: string;
  impacts: Array<{
    factor: string;
    impact: 'positive' | 'negative' | 'neutral';
    magnitude: 'high' | 'medium' | 'low';
    description: string;
  }>;
  overall_outlook: string;
  analyzed_at: string;
}