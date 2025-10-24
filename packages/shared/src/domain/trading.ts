export interface Portfolio {
  id: number;
  name: string;
  description?: string;
  initialCapital: number;
  currentCapital: number;
  currency: string;
  createdAt: string;
  updatedAt: string;
}

export interface Position {
  id: number;
  portfolioId: number;
  symbol: string;
  quantity: number;
  averageCost: number;
  currentPrice: number;
  unrealizedPnl: number;
  realizedPnl: number;
  positionType: "LONG" | "SHORT";
  entryDate?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Trade {
  id: number;
  portfolioId: number;
  symbol: string;
  tradeType: "BUY" | "SELL";
  quantity: number;
  price: number;
  totalCost: number;
  executedAt: string;
  sessionId?: number;
  decisionRationale?: string;
  confidenceScore?: number;
  status: "pending" | "executed" | "failed" | "cancelled";
}

export interface TradingSignal {
  id: string;
  symbol: string;
  signal: "buy" | "sell" | "hold";
  strength: number;
  price: number;
  timestamp: string;
  source: string;
  indicators?: Record<string, number>;
  rationale?: string;
}

export interface AgentActivity {
  id: string;
  agentId: string;
  agentRole: "analyst" | "researcher" | "trader" | "risk_manager" | "portfolio_manager";
  activityType: "analysis" | "signal" | "trade" | "risk_check" | "insight";
  message: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
  status: "started" | "in_progress" | "completed" | "failed";
}

export interface PortfolioUpdate {
  portfolioId: number;
  totalValue: number;
  cash: number;
  totalUnrealizedPnl: number;
  totalRealizedPnl: number;
  dailyPnl: number;
  dailyPnlPercent: number;
  positions: Position[];
  timestamp: string;
}

export interface RiskMetrics {
  portfolioId: number;
  portfolioValue: number;
  var1day95: number;
  var1day99: number;
  var5day95: number;
  var5day99: number;
  portfolioVolatility: number;
  sharpeRatio: number;
  maxDrawdown: number;
  largestPositionWeight: number;
  top5Concentration: number;
  numberOfPositions: number;
  totalExposure: number;
  longExposure: number;
  shortExposure: number;
  netExposure: number;
  measuredAt: string;
}

export type StreamEvent =
  | { type: "portfolio_update"; data: PortfolioUpdate }
  | { type: "signal"; data: TradingSignal }
  | { type: "trade"; data: Trade }
  | { type: "agent_activity"; data: AgentActivity }
  | { type: "risk_update"; data: RiskMetrics }
  | { type: "error"; data: { message: string } }
  | { type: "heartbeat"; data: { timestamp: string } };
