"use client";

import * as React from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Loader2, RefreshCw } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { formatCurrency, formatDate } from "@tradingagents/shared/utils/format";

export type TimeRangeOption = "7d" | "30d" | "90d" | "all";

export interface AgentListEntry {
  id: number;
  name: string;
  role: string;
}

export interface AgentLLMUsageRecord {
  id: number;
  agent_id: number;
  provider: string;
  model_name: string;
  is_fallback: boolean;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
  created_at: string;
  metadata?: Record<string, any> | null;
}

export interface AgentLLMUsageSummary {
  agent_id: number;
  total_calls: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_cost_usd: number;
  records: AgentLLMUsageRecord[];
}

interface LLMUsageDashboardProps {
  agents: AgentListEntry[];
  summaries: Record<number, AgentLLMUsageSummary | undefined>;
  timeRange: TimeRangeOption;
  onTimeRangeChange: (range: TimeRangeOption) => void;
  isLoading?: boolean;
  onRefresh?: () => void;
}

const COLORS = ["#6366F1", "#EC4899", "#14B8A6", "#F59E0B", "#8B5CF6", "#F87171"];

export function LLMUsageDashboard({
  agents,
  summaries,
  timeRange,
  onTimeRangeChange,
  isLoading = false,
  onRefresh,
}: LLMUsageDashboardProps) {
  const agentMap = React.useMemo(() => new Map(agents.map((agent) => [agent.id, agent])), [agents]);

  const sortedAgents = React.useMemo(() => {
    return agents
      .map((agent) => ({
        agent,
        totalTokens: summaries[agent.id]?.total_tokens ?? 0,
        totalCost: summaries[agent.id]?.total_cost_usd ?? 0,
      }))
      .sort((a, b) => b.totalTokens - a.totalTokens);
  }, [agents, summaries]);

  const topAgents = React.useMemo(() => sortedAgents.slice(0, 5), [sortedAgents]);
  const topAgentIds = React.useMemo(() => new Set(topAgents.map((entry) => entry.agent.id)), [topAgents]);

  const chartData = React.useMemo(() => {
    const aggregated = new Map<string, Record<string, number>>();

    topAgents.forEach(({ agent }) => {
      const summary = summaries[agent.id];
      if (!summary) return;
      summary.records.forEach((record) => {
        const dateKey = new Date(record.created_at).toISOString().split("T")[0];
        if (!aggregated.has(dateKey)) {
          aggregated.set(dateKey, { date: dateKey });
        }
        const entry = aggregated.get(dateKey)!;
        entry[agent.name] = (entry[agent.name] ?? 0) + record.total_tokens;
      });
    });

    return Array.from(aggregated.values()).sort((a, b) =>
      String(a.date).localeCompare(String(b.date)),
    );
  }, [summaries, topAgents]);

  const costBreakdown = React.useMemo(() => {
    const totals = new Map<string, number>();
    Object.values(summaries).forEach((summary) => {
      summary?.records.forEach((record) => {
        totals.set(record.provider, (totals.get(record.provider) ?? 0) + record.cost_usd);
      });
    });
    return Array.from(totals.entries()).sort((a, b) => b[1] - a[1]);
  }, [summaries]);

  const agentPerformance = React.useMemo(() => {
    return sortedAgents.slice(0, 6).map(({ agent }) => {
      const summary = summaries[agent.id];
      if (!summary) {
        return {
          agent,
          avgLatency: null,
          successRate: null,
          totalCalls: 0,
          totalTokens: 0,
          totalCost: 0,
        };
      }

      let latencySum = 0;
      let latencyCount = 0;
      let successCount = 0;
      let successTotal = 0;

      summary.records.forEach((record) => {
        const latency = record.metadata?.latency_ms ?? record.metadata?.latencyMs;
        if (typeof latency === "number" && Number.isFinite(latency)) {
          latencySum += latency;
          latencyCount += 1;
        }
        if (record.metadata && "success" in record.metadata) {
          successTotal += 1;
          if (record.metadata.success) {
            successCount += 1;
          }
        }
      });

      const avgLatency = latencyCount > 0 ? latencySum / latencyCount : null;
      const successRate = successTotal > 0 ? successCount / successTotal : null;

      return {
        agent,
        avgLatency,
        successRate,
        totalCalls: summary.total_calls,
        totalTokens: summary.total_tokens,
        totalCost: summary.total_cost_usd,
      };
    });
  }, [sortedAgents, summaries]);

  const timeRangeOptions: Array<{ label: string; value: TimeRangeOption }> = [
    { label: "7d", value: "7d" },
    { label: "30d", value: "30d" },
    { label: "90d", value: "90d" },
    { label: "All", value: "all" },
  ];

  const hasUsage = chartData.length > 0;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-col gap-4 border-b border-border/60 bg-surface/70 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle>Token usage over time</CardTitle>
            <CardDescription>
              Track token consumption for the most active agents.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 rounded-md border border-border/60 bg-background p-1">
              {timeRangeOptions.map((option) => (
                <Button
                  key={option.value}
                  variant={timeRange === option.value ? "default" : "ghost"}
                  size="sm"
                  onClick={() => onTimeRangeChange(option.value)}
                >
                  {option.label}
                </Button>
              ))}
            </div>
            {onRefresh && (
              <Button variant="outline" size="sm" onClick={onRefresh} disabled={isLoading}>
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="pt-6">
          {isLoading ? (
            <div className="flex h-64 items-center justify-center text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : hasUsage ? (
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.2} />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(value: string) => formatDate(value, undefined, {
                      month: "short",
                      day: "numeric",
                    })}
                  />
                  <YAxis tickFormatter={(value: number) => `${Math.round(value / 1000)}k`} />
                  <Tooltip
                    contentStyle={{ background: "hsl(var(--background))", borderRadius: 8 }}
                    formatter={(value: number, name: string) => [value.toLocaleString(), name]}
                    labelFormatter={(label: string) => formatDate(label)}
                  />
                  <Legend />
                  {topAgents.map(({ agent }, index) => (
                    <Area
                      key={agent.id}
                      type="monotone"
                      dataKey={agent.name}
                      stroke={COLORS[index % COLORS.length]}
                      fill={`${COLORS[index % COLORS.length]}33`}
                      stackId={undefined}
                    />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex h-64 flex-col items-center justify-center text-center text-muted-foreground">
              <p className="text-sm">No usage data available for the selected time range.</p>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Cost by provider</CardTitle>
            <CardDescription>Aggregate spend for the selected window</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {costBreakdown.length === 0 ? (
              <p className="text-sm text-muted-foreground">No cost recorded yet.</p>
            ) : (
              costBreakdown.map(([provider, cost]) => (
                <div
                  key={provider}
                  className="flex items-center justify-between rounded-md border border-border/60 bg-surface-muted/50 p-3"
                >
                  <div>
                    <p className="font-medium capitalize">{provider}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatCurrency(cost)} total spend
                    </p>
                  </div>
                  <Badge variant="outline">{formatCurrency(cost)}</Badge>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Agent performance</CardTitle>
            <CardDescription>
              Success rate, latency, and token footprint per agent
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {agentPerformance.length === 0 ? (
              <p className="text-sm text-muted-foreground">No agents found.</p>
            ) : (
              agentPerformance.map((row, index) => (
                <div
                  key={row.agent.id}
                  className="flex flex-col gap-3 rounded-md border border-border/60 bg-surface-muted/40 p-3 md:flex-row md:items-center md:justify-between"
                >
                  <div className="flex items-center gap-3">
                    <Badge style={{ backgroundColor: `${COLORS[index % COLORS.length]}1a`, color: COLORS[index % COLORS.length] }}>
                      {row.agent.name}
                    </Badge>
                    <div className="text-sm text-muted-foreground capitalize">{row.agent.role}</div>
                  </div>
                  <div className="flex flex-wrap gap-4 text-sm">
                    <Metric label="Calls" value={row.totalCalls.toLocaleString()} />
                    <Metric label="Tokens" value={row.totalTokens.toLocaleString()} />
                    <Metric label="Cost" value={formatCurrency(row.totalCost)} />
                    <Metric
                      label="Latency"
                      value={row.avgLatency !== null ? `${row.avgLatency.toFixed(0)} ms` : "N/A"}
                    />
                    <Metric
                      label="Success"
                      value={
                        row.successRate !== null
                          ? `${Math.round(row.successRate * 100)}%`
                          : "N/A"
                      }
                    />
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="font-semibold text-foreground">{value}</p>
    </div>
  );
}
