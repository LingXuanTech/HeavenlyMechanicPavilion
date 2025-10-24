export type AgentRole =
  | "analyst"
  | "researcher"
  | "trader"
  | "risk_manager"
  | "portfolio_manager";

export type AgentStatus = "idle" | "running" | "completed" | "error";

export interface AgentSnapshot {
  id: string;
  role: AgentRole;
  status: AgentStatus;
  headline: string;
  startedAt: string;
  completedAt?: string;
  summary?: string;
}

export interface TradingInsight {
  id: string;
  agentId: string;
  title: string;
  body: string;
  confidence: number;
  createdAt: string;
}

export type TradingDecision = "buy" | "sell" | "hold" | "watchlist";

export interface RiskSignal {
  id: string;
  category: "liquidity" | "volatility" | "macro" | "compliance";
  severity: "low" | "medium" | "high" | "critical";
  narrative: string;
}

export interface TradingSession {
  id: string;
  ticker: string;
  asOfDate: string;
  status: "pending" | "running" | "completed" | "failed";
  createdAt: string;
  updatedAt?: string;
  agents: AgentSnapshot[];
  insights: TradingInsight[];
  decision?: {
    action: TradingDecision;
    conviction: number;
    rationale: string;
  };
  risk?: {
    overall: "low" | "medium" | "high";
    summary: string;
    signals: RiskSignal[];
  };
}
