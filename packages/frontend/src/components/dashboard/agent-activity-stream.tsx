"use client";

import { useState } from "react";
import { Activity, Brain, Search, TrendingUp, ShieldAlert, Briefcase, Filter } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { formatDate } from "@tradingagents/shared/utils/format";
import type { AgentActivity } from "@tradingagents/shared/domain";

interface AgentActivityStreamProps {
  activities: AgentActivity[];
  isConnected: boolean;
}

type ActivityFilter = "all" | "analyst" | "researcher" | "trader" | "risk_manager" | "portfolio_manager";

const agentRoleConfig = {
  analyst: {
    icon: Brain,
    color: "text-primary",
    bgColor: "bg-primary/10",
    label: "Analyst",
  },
  researcher: {
    icon: Search,
    color: "text-accent",
    bgColor: "bg-accent/10",
    label: "Researcher",
  },
  trader: {
    icon: TrendingUp,
    color: "text-success",
    bgColor: "bg-success/10",
    label: "Trader",
  },
  risk_manager: {
    icon: ShieldAlert,
    color: "text-warning",
    bgColor: "bg-warning/10",
    label: "Risk Manager",
  },
  portfolio_manager: {
    icon: Briefcase,
    color: "text-purple-500",
    bgColor: "bg-purple-500/10",
    label: "Portfolio Manager",
  },
};

export function AgentActivityStream({ activities, isConnected }: AgentActivityStreamProps) {
  const [filter, setFilter] = useState<ActivityFilter>("all");

  const filteredActivities = activities.filter(activity => {
    if (filter === "all") return true;
    return activity.agentRole === filter;
  });

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              Agent Activity Stream
            </CardTitle>
            <CardDescription>
              Real-time updates from all trading agents ({filteredActivities.length} activities)
            </CardDescription>
          </div>
          <ConnectionIndicator isConnected={isConnected} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="mb-4 flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select value={filter} onValueChange={(value) => setFilter(value as ActivityFilter)}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Filter by agent" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Agents</SelectItem>
              <SelectItem value="analyst">Analyst</SelectItem>
              <SelectItem value="researcher">Researcher</SelectItem>
              <SelectItem value="trader">Trader</SelectItem>
              <SelectItem value="risk_manager">Risk Manager</SelectItem>
              <SelectItem value="portfolio_manager">Portfolio Manager</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <ScrollArea className="h-[600px]">
          <div className="space-y-3">
            {filteredActivities.length > 0 ? (
              filteredActivities.map((activity) => (
                <ActivityCard key={activity.id} activity={activity} />
              ))
            ) : (
              <div className="flex h-40 items-center justify-center">
                <p className="text-sm text-muted-foreground">
                  {activities.length === 0 
                    ? "No agent activity yet. Waiting for updates..."
                    : "No activities match the current filter"}
                </p>
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

interface ActivityCardProps {
  activity: AgentActivity;
}

function ActivityCard({ activity }: ActivityCardProps) {
  const config = agentRoleConfig[activity.agentRole];
  const Icon = config.icon;

  const statusConfig = {
    started: {
      color: "text-blue-500",
      bgColor: "bg-blue-500/10",
      label: "Started",
    },
    in_progress: {
      color: "text-warning",
      bgColor: "bg-warning/10",
      label: "In Progress",
    },
    completed: {
      color: "text-success",
      bgColor: "bg-success/10",
      label: "Completed",
    },
    failed: {
      color: "text-destructive",
      bgColor: "bg-destructive/10",
      label: "Failed",
    },
  };

  const status = statusConfig[activity.status];

  const activityTypeLabels = {
    analysis: "Analysis",
    signal: "Signal Generated",
    trade: "Trade Execution",
    risk_check: "Risk Check",
    insight: "Insight",
  };

  return (
    <div className={cn(
      "rounded-lg border border-border/60 p-4 transition-colors hover:bg-surface-muted/50",
      config.bgColor
    )}>
      <div className="flex items-start gap-3">
        <div className={cn(
          "flex h-10 w-10 items-center justify-center rounded-full",
          config.bgColor
        )}>
          <Icon className={cn("h-5 w-5", config.color)} />
        </div>

        <div className="flex-1 space-y-2">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-foreground">{config.label}</span>
              <Badge variant="outline" className="text-xs">
                {activityTypeLabels[activity.activityType]}
              </Badge>
              <Badge 
                variant="outline" 
                className={cn("text-xs", status.color, status.bgColor)}
              >
                {status.label}
              </Badge>
            </div>
            <span className="text-xs text-muted-foreground whitespace-nowrap ml-2">
              {formatDate(activity.timestamp)}
            </span>
          </div>

          <p className="text-sm text-foreground/90">
            {activity.message}
          </p>

          {activity.metadata && Object.keys(activity.metadata).length > 0 && (
            <div className="flex flex-wrap gap-2 pt-2 border-t border-border/40">
              {Object.entries(activity.metadata).map(([key, value]) => (
                <span key={key} className="text-xs text-muted-foreground">
                  <span className="font-medium">{key}:</span>{" "}
                  {typeof value === "object" ? JSON.stringify(value) : String(value)}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ConnectionIndicator({ isConnected }: { isConnected: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <div
        className={cn(
          "h-2 w-2 rounded-full",
          isConnected ? "bg-success animate-pulse" : "bg-muted-foreground"
        )}
      />
      <span className="text-xs text-muted-foreground">
        {isConnected ? "Live" : "Offline"}
      </span>
    </div>
  );
}
