import {
  Activity,
  ArrowUpRight,
  Brain,
  Cable,
  CircleDot,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  formatDate,
  formatPercent,
} from "@tradingagents/shared/utils/format";
import type { TradingSession } from "@tradingagents/shared/domain";
import { tradingAgentsGradients } from "@tradingagents/shared/theme";

const mockSession: TradingSession = {
  id: "session-nvda",
  ticker: "NVDA",
  asOfDate: "2024-10-24",
  status: "running",
  createdAt: "2024-10-24T12:40:00Z",
  updatedAt: "2024-10-24T13:15:00Z",
  agents: [
    {
      id: "analyst-team",
      role: "analyst",
      status: "completed",
      headline: "Structural demand intact despite cyclical noise",
      startedAt: "2024-10-24T12:40:00Z",
      completedAt: "2024-10-24T12:55:00Z",
      summary:
        "Technical and fundamentals aligned: hyperscaler capex and AI inference workloads keep top-line resilient.",
    },
    {
      id: "research-alpha",
      role: "researcher",
      status: "running",
      headline: "Bull-bear debate converging on staggered entries",
      startedAt: "2024-10-24T12:55:30Z",
      summary:
        "Bull researcher advocates scaling into momentum continuation; bear researcher flags supply tightness easing in Q1.",
    },
    {
      id: "trader-desk",
      role: "trader",
      status: "idle",
      headline: "Awaiting final risk clearance",
      startedAt: "2024-10-24T13:10:00Z",
    },
    {
      id: "risk-ops",
      role: "risk_manager",
      status: "running",
      headline: "Volatility maps within mandate",
      startedAt: "2024-10-24T13:12:00Z",
    },
  ],
  insights: [
    {
      id: "insight-1",
      agentId: "analyst-team",
      title: "Options flow",
      body: "Call skew steepening into print with pronounced demand for weekly 10% OTM strikes.",
      confidence: 0.74,
      createdAt: "2024-10-24T12:53:00Z",
    },
    {
      id: "insight-2",
      agentId: "research-alpha",
      title: "Macro overlay",
      body: "Fed commentary today implied tolerance for higher-for-longer. NVDA remains a secular growth proxy less rate sensitive.",
      confidence: 0.67,
      createdAt: "2024-10-24T13:05:00Z",
    },
    {
      id: "insight-3",
      agentId: "risk-ops",
      title: "Risk windows",
      body: "Max drawdown scenario limited to -4.7% with hedges applied; dynamic delta hedging triggers at -2%.",
      confidence: 0.62,
      createdAt: "2024-10-24T13:11:00Z",
    },
  ],
  decision: {
    action: "buy",
    conviction: 0.78,
    rationale:
      "Scale into pre-earnings continuation with staggered entries and protective put spread to cap tail risk.",
  },
  risk: {
    overall: "medium",
    summary:
      "Volatility elevated but contained within mandate. Liquidity depth supports multiday scaling strategy.",
    signals: [
      {
        id: "risk-1",
        category: "volatility",
        severity: "medium",
        narrative: "Implied vol ranks at 78th percentile — monitor for blowout if guidance disappoints.",
      },
      {
        id: "risk-2",
        category: "liquidity",
        severity: "low",
        narrative: "Depth across L2 books is supportive; cross-venue routing recommended for first tranche.",
      },
      {
        id: "risk-3",
        category: "macro",
        severity: "medium",
        narrative: "Dollar strength could pressure EPS conversion — hedge via MXWO exposure if conviction persists.",
      },
    ],
  },
};

const activeAgents = mockSession.agents.filter((agent) => agent.status !== "idle");
const completedInsights = mockSession.insights.slice(0, 3);
const riskSignals = mockSession.risk?.signals ?? [];
const riskSummary =
  mockSession.risk?.summary ?? "Risk controls are recalibrating across volatility and liquidity modules.";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <Card className="relative overflow-hidden border-none bg-surface text-foreground shadow-pop">
        <div
          className="pointer-events-none absolute inset-0 opacity-90"
          style={{ backgroundImage: tradingAgentsGradients.sunrise }}
        />
        <CardHeader className="relative z-10 flex flex-col gap-6 pb-0 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-3">
            <Badge variant="accent" className="uppercase">
              Session {mockSession.id}
            </Badge>
            <div>
              <CardTitle className="text-3xl font-semibold">
                {mockSession.ticker} multi-agent briefing
              </CardTitle>
              <CardDescription>
                Updated {formatDate(mockSession.updatedAt ?? mockSession.createdAt)} ·
                Decision desk preparing execution playbook.
              </CardDescription>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              <span className="inline-flex items-center gap-1 rounded-full bg-surface-muted/70 px-3 py-1">
                <CircleDot className="h-3.5 w-3.5 text-success" /> {mockSession.status.toUpperCase()}
              </span>
              <span>Conviction {formatPercent(mockSession.decision?.conviction ?? 0)}</span>
              <span>Risk {mockSession.risk ? mockSession.risk.overall.toUpperCase() : "N/A"}</span>
            </div>
          </div>
          <div className="relative z-10 flex flex-col gap-3 sm:flex-row sm:items-center">
            <Button variant="outline" className="border-border/70">
              Download dossier
            </Button>
            <Button className="gap-2">
              Proceed to trade room
              <ArrowUpRight className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="relative z-10 grid gap-4 pt-6 text-sm text-muted-foreground sm:grid-cols-2 lg:grid-cols-4">
          <SessionMeta label="Created" value={formatDate(mockSession.createdAt)} />
          <SessionMeta label="Last sync" value={formatDate(mockSession.updatedAt ?? mockSession.createdAt)} />
          <SessionMeta label="Active agents" value={`${activeAgents.length}/${mockSession.agents.length}`} />
          <SessionMeta label="Insights processed" value={`${mockSession.insights.length}`} />
        </CardContent>
      </Card>

      <section className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
        <KpiCard
          title="Momentum complexion"
          description="Composite of flow, sentiment, and price structure"
          icon={TrendingUp}
          metric="+3.4%"
          trend="Bullish bias"
        />
        <KpiCard
          title="Risk envelope"
          description="Mandate consumption across liquidity and VAR"
          icon={ShieldAlert}
          metric="52%"
          trend="Within guardrails"
          tone="warning"
        />
        <KpiCard
          title="Agent cadence"
          description="Average turnaround across collaborating agents"
          icon={Activity}
          metric="4m 12s"
          trend="Improving throughput"
          tone="accent"
        />
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.45fr_1fr]">
        <Card className="border-border/70">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-xl">
              <Brain className="h-5 w-5 text-primary" /> Latest insights
            </CardTitle>
            <CardDescription>
              Synthesised narratives from analyst, research, and risk teams.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {completedInsights.map((insight) => (
              <article key={insight.id} className="space-y-2 rounded-lg border border-surface-muted bg-surface/80 p-5 shadow-subtle">
                <div className="flex items-center justify-between">
                  <Badge variant="muted" className="uppercase">
                    Confidence {formatPercent(insight.confidence)}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {formatDate(insight.createdAt)}
                  </span>
                </div>
                <h3 className="text-lg font-heading font-semibold text-foreground">
                  {insight.title}
                </h3>
                <p className="text-sm text-muted-foreground">{insight.body}</p>
              </article>
            ))}
            <Button variant="ghost" className="w-fit">
              View analyst log
            </Button>
          </CardContent>
        </Card>

        <Card className="border-border/70">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-xl">
              <Cable className="h-5 w-5 text-accent" /> Risk console
            </CardTitle>
            <CardDescription>
              Summary of guardrails that must be satisfied prior to routing orders.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="rounded-lg border border-border/60 bg-surface-muted/50 p-4 shadow-subtle">
              <p className="text-sm text-muted-foreground">{riskSummary}</p>
            </div>
            <div className="space-y-4">
              {riskSignals.length > 0 ? (
                riskSignals.map((signal) => (
                  <div
                    key={signal.id}
                    className="flex items-start gap-3 rounded-md border border-border/60 bg-surface/90 p-3"
                  >
                    <Badge
                      variant={
                        signal.severity === "high"
                          ? "destructive"
                          : signal.severity === "medium"
                            ? "warning"
                            : "success"
                      }
                      className="shrink-0"
                    >
                      {signal.category}
                    </Badge>
                    <p className="text-xs text-muted-foreground">{signal.narrative}</p>
                  </div>
                ))
              ) : (
                <p className="text-xs text-muted-foreground">
                  Awaiting updated guardrails from the risk management pod.
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </section>

      <Card className="border-border/70">
        <CardHeader className="pb-4">
          <CardTitle className="text-xl">Agent runway</CardTitle>
          <CardDescription>
            Track each role&apos;s output cadence and current focus area across the session lifecycle.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {mockSession.agents.map((agent) => (
            <div
              key={agent.id}
              className="rounded-lg border border-border/60 bg-surface-muted/40 p-4 shadow-subtle"
            >
              <div className="flex items-center justify-between text-xs uppercase tracking-wider text-muted-foreground">
                <span>{agent.role.replace("_", " ")}</span>
                <StatusPill status={agent.status} />
              </div>
              <p className="mt-2 text-sm font-medium text-foreground">{agent.headline}</p>
              {agent.summary ? (
                <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{agent.summary}</p>
              ) : null}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

interface SessionMetaProps {
  label: string;
  value: string;
}

const SessionMeta = ({ label, value }: SessionMetaProps) => (
  <div className="rounded-lg border border-border/70 bg-surface/60 p-4 shadow-subtle">
    <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">{label}</p>
    <p className="mt-1 text-sm font-semibold text-foreground">{value}</p>
  </div>
);

interface KpiCardProps {
  title: string;
  description: string;
  metric: string;
  trend: string;
  icon: (props: React.SVGProps<SVGSVGElement>) => JSX.Element;
  tone?: "default" | "warning" | "accent";
}

const KpiCard = ({ title, description, metric, trend, icon: Icon, tone = "default" }: KpiCardProps) => {
  const accentClass =
    tone === "warning"
      ? "text-warning"
      : tone === "accent"
        ? "text-accent"
        : "text-primary";

  return (
    <Card className="border-border/70">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold">{title}</CardTitle>
          <Icon className={cn("h-5 w-5", accentClass)} />
        </div>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        <p className="text-3xl font-heading font-semibold text-foreground">{metric}</p>
        <p className="text-sm text-muted-foreground">{trend}</p>
      </CardContent>
    </Card>
  );
};

interface StatusPillProps {
  status: "idle" | "running" | "completed" | "error";
}

const StatusPill = ({ status }: StatusPillProps) => {
  const palette = {
    idle: "bg-muted/40 text-muted-foreground",
    running: "bg-primary/20 text-primary",
    completed: "bg-success/20 text-success",
    error: "bg-destructive/20 text-destructive",
  } as const;

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[0.65rem] font-semibold uppercase",
        palette[status],
      )}
    >
      {status}
    </span>
  );
};
