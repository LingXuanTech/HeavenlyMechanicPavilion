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

/**
 * Lightweight summary of a persisted session.
 * Maps to backend session storage without full event history.
 */
export interface SessionSummary {
  id: string;
  ticker: string;
  asOfDate: string;
  status: "pending" | "running" | "completed" | "failed";
  createdAt: string;
  updatedAt?: string;
}

/**
 * A single buffered event with timestamp.
 * Maps to backend's BufferedSessionEvent schema.
 */
export interface SessionEventSummary {
  timestamp: string;
  event: Record<string, unknown>;
}

/**
 * Response containing recent events buffered for a session.
 * Maps to backend's SessionEventsHistoryResponse schema.
 */
export interface SessionEventsHistory {
  session_id: string;
  events: SessionEventSummary[];
  count: number;
}

// Type Guards

export function isSessionSummary(value: unknown): value is SessionSummary {
  if (typeof value !== "object" || value === null) return false;
  const obj = value as Record<string, unknown>;
  
  return (
    typeof obj.id === "string" &&
    typeof obj.ticker === "string" &&
    typeof obj.asOfDate === "string" &&
    (obj.status === "pending" ||
      obj.status === "running" ||
      obj.status === "completed" ||
      obj.status === "failed") &&
    typeof obj.createdAt === "string" &&
    (obj.updatedAt === undefined || typeof obj.updatedAt === "string")
  );
}

export function isSessionEventSummary(
  value: unknown
): value is SessionEventSummary {
  if (typeof value !== "object" || value === null) return false;
  const obj = value as Record<string, unknown>;
  
  return (
    typeof obj.timestamp === "string" &&
    typeof obj.event === "object" &&
    obj.event !== null
  );
}

export function isSessionEventsHistory(
  value: unknown
): value is SessionEventsHistory {
  if (typeof value !== "object" || value === null) return false;
  const obj = value as Record<string, unknown>;
  
  return (
    typeof obj.session_id === "string" &&
    Array.isArray(obj.events) &&
    obj.events.every(isSessionEventSummary) &&
    typeof obj.count === "number"
  );
}

// Normalizers

/**
 * Normalizes a raw backend response into a typed SessionSummary.
 * Returns null if the payload is malformed.
 */
export function normalizeSessionSummary(
  raw: unknown
): SessionSummary | null {
  if (!isSessionSummary(raw)) return null;
  return raw;
}

/**
 * Normalizes a raw backend response into typed SessionEventsHistory.
 * Returns null if the payload is malformed.
 */
export function normalizeSessionEventsHistory(
  raw: unknown
): SessionEventsHistory | null {
  if (!isSessionEventsHistory(raw)) return null;
  return raw;
}

// Transformation Helpers

/**
 * Merges event history data into a base SessionSummary to create a richer TradingSession.
 * Extracts agents, insights, decision, and risk from event payloads when available.
 */
export function enrichSessionWithEvents(
  summary: SessionSummary,
  eventsHistory?: SessionEventsHistory
): TradingSession {
  const agents: AgentSnapshot[] = [];
  const insights: TradingInsight[] = [];
  let decision: TradingSession["decision"] | undefined;
  let risk: TradingSession["risk"] | undefined;

  if (eventsHistory) {
    for (const eventSummary of eventsHistory.events) {
      const { event } = eventSummary;
      const eventType = event.type as string;

      // Extract agent snapshots
      if (eventType === "agent_update" && isAgentSnapshot(event.payload)) {
        agents.push(event.payload as AgentSnapshot);
      }

      // Extract insights
      if (eventType === "insight" && isTradingInsight(event.payload)) {
        insights.push(event.payload as TradingInsight);
      }

      // Extract final decision
      if (eventType === "decision" && isDecision(event.payload)) {
        decision = event.payload as TradingSession["decision"];
      }

      // Extract risk assessment
      if (eventType === "risk" && isRisk(event.payload)) {
        risk = event.payload as TradingSession["risk"];
      }
    }
  }

  return {
    ...summary,
    agents,
    insights,
    decision,
    risk,
  };
}

// Helper type guards for event payloads

function isAgentSnapshot(value: unknown): value is AgentSnapshot {
  if (typeof value !== "object" || value === null) return false;
  const obj = value as Record<string, unknown>;
  
  return (
    typeof obj.id === "string" &&
    typeof obj.role === "string" &&
    typeof obj.status === "string" &&
    typeof obj.headline === "string" &&
    typeof obj.startedAt === "string"
  );
}

function isTradingInsight(value: unknown): value is TradingInsight {
  if (typeof value !== "object" || value === null) return false;
  const obj = value as Record<string, unknown>;
  
  return (
    typeof obj.id === "string" &&
    typeof obj.agentId === "string" &&
    typeof obj.title === "string" &&
    typeof obj.body === "string" &&
    typeof obj.confidence === "number" &&
    typeof obj.createdAt === "string"
  );
}

function isDecision(value: unknown): boolean {
  if (typeof value !== "object" || value === null) return false;
  const obj = value as Record<string, unknown>;
  
  return (
    (obj.action === "buy" ||
      obj.action === "sell" ||
      obj.action === "hold" ||
      obj.action === "watchlist") &&
    typeof obj.conviction === "number" &&
    typeof obj.rationale === "string"
  );
}

function isRisk(value: unknown): boolean {
  if (typeof value !== "object" || value === null) return false;
  const obj = value as Record<string, unknown>;
  
  return (
    (obj.overall === "low" ||
      obj.overall === "medium" ||
      obj.overall === "high") &&
    typeof obj.summary === "string" &&
    Array.isArray(obj.signals)
  );
}
