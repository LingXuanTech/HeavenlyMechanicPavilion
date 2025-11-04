"use client";

import { Activity, CheckCircle, AlertCircle, Loader2, FileText } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { formatDate } from "@tradingagents/shared/utils/format";

export interface SessionEvent {
  type: string;
  message?: string;
  payload?: Record<string, unknown>;
  timestamp?: string;
}

interface SessionEventTimelineProps {
  events: SessionEvent[];
  isConnected: boolean;
  error?: Error | null;
}

const eventTypeConfig = {
  status: {
    icon: Loader2,
    color: "text-blue-500",
    bgColor: "bg-blue-500/10",
    label: "Status Update",
  },
  result: {
    icon: FileText,
    color: "text-success",
    bgColor: "bg-success/10",
    label: "Results",
  },
  completed: {
    icon: CheckCircle,
    color: "text-success",
    bgColor: "bg-success/10",
    label: "Completed",
  },
  error: {
    icon: AlertCircle,
    color: "text-destructive",
    bgColor: "bg-destructive/10",
    label: "Error",
  },
  default: {
    icon: Activity,
    color: "text-primary",
    bgColor: "bg-primary/10",
    label: "Event",
  },
};

export function SessionEventTimeline({ events, isConnected, error }: SessionEventTimelineProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              Session Activity
            </CardTitle>
            <CardDescription>
              Real-time session events and updates ({events.length} events)
            </CardDescription>
          </div>
          <ConnectionIndicator isConnected={isConnected} error={error} />
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[600px]">
          <div className="space-y-3">
            {events.length > 0 ? (
              events.map((event, index) => (
                <EventCard key={`${event.type}-${index}`} event={event} />
              ))
            ) : (
              <div className="flex h-40 items-center justify-center">
                <p className="text-sm text-muted-foreground">
                  {isConnected 
                    ? "Waiting for session events..."
                    : "No events yet. Connect to see live updates."}
                </p>
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

interface EventCardProps {
  event: SessionEvent;
}

function EventCard({ event }: EventCardProps) {
  const config = eventTypeConfig[event.type as keyof typeof eventTypeConfig] || eventTypeConfig.default;
  const Icon = config.icon;

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
          <Icon className={cn("h-5 w-5", config.color, event.type === "status" && "animate-spin")} />
        </div>

        <div className="flex-1 space-y-2">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant="outline" className={cn("text-xs", config.color)}>
                {config.label}
              </Badge>
              {event.message && (
                <span className="font-semibold text-foreground">{event.message}</span>
              )}
            </div>
            {event.timestamp && (
              <span className="text-xs text-muted-foreground whitespace-nowrap ml-2">
                {formatDate(event.timestamp)}
              </span>
            )}
          </div>

          {event.payload && Object.keys(event.payload).length > 0 && (
            <div className="space-y-2">
              {renderPayload(event.payload)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function renderPayload(payload: Record<string, unknown>) {
  const entries = Object.entries(payload).filter(([key]) => 
    !['type', 'message'].includes(key)
  );

  if (entries.length === 0) return null;

  return (
    <div className="space-y-1 rounded-md bg-surface-muted/50 p-3 border-t border-border/40">
      {entries.map(([key, value]) => (
        <div key={key} className="text-xs">
          <span className="font-medium text-foreground">{formatKey(key)}:</span>{" "}
          <span className="text-muted-foreground">
            {renderValue(value)}
          </span>
        </div>
      ))}
    </div>
  );
}

function formatKey(key: string): string {
  return key
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function renderValue(value: unknown): string {
  if (value === null || value === undefined) return 'N/A';
  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}

function ConnectionIndicator({ isConnected, error }: { isConnected: boolean; error?: Error | null }) {
  if (error) {
    return (
      <div className="flex items-center gap-2">
        <div className="h-2 w-2 rounded-full bg-destructive" />
        <span className="text-xs text-destructive">
          Error
        </span>
      </div>
    );
  }

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
