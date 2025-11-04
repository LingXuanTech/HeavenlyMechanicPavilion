"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowUpRight, CircleDot } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { tradingAgentsGradients } from "@tradingagents/shared/theme";
import { api } from "@/lib/api/client";
import type { TradingSession } from "@tradingagents/shared/domain";
import { formatDate, formatPercent } from "@tradingagents/shared/utils/format";
import { SessionEventTimeline, type SessionEvent } from "@/components/sessions/session-event-timeline";
import { useSessionStream } from "@/hooks/use-session-stream";

export default function SessionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;
  const [session, setSession] = useState<TradingSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { showToast } = useToast();

  // Session stream for real-time updates
  const {
    events: streamEvents,
    isConnected,
    error: streamError,
    addBufferedEvents,
  } = useSessionStream({
    sessionId,
    enabled: !!sessionId && !!session,
  });

  useEffect(() => {
    async function fetchSession() {
      if (!sessionId) return;
      try {
        setIsLoading(true);
        
        // Fetch session details
        const response = await api.sessions.get(sessionId);
        setSession(response);
        
        // Fetch buffered events separately
        try {
          const eventsResponse = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/sessions/${sessionId}/events-history`
          );
          
          if (eventsResponse.ok) {
            const eventsData = await eventsResponse.json();
            if (eventsData.events && eventsData.events.length > 0) {
              const bufferedEvents: SessionEvent[] = eventsData.events.map((e: { timestamp: string; event: Record<string, unknown> }) => ({
                type: (e.event.type as string) || "event",
                message: e.event.message as string | undefined,
                payload: e.event.payload as Record<string, unknown> | undefined,
                timestamp: e.timestamp,
              }));
              addBufferedEvents(bufferedEvents);
            }
          }
        } catch (eventsErr) {
          // Non-critical error - just log it
          console.warn("Failed to fetch buffered events:", eventsErr);
        }
      } catch (err) {
        setError("Failed to fetch session details.");
        showToast({
          type: "error",
          title: "Error",
          description: "Failed to load session details. Please try again.",
        });
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    }
    fetchSession();
  }, [sessionId, showToast, addBufferedEvents]);

  // Show toast on stream errors
  useEffect(() => {
    if (streamError) {
      showToast({
        type: "error",
        title: "Connection Error",
        description: "Lost connection to live session updates. Reconnecting...",
        duration: 3000,
      });
    }
  }, [streamError, showToast]);

  if (isLoading) {
    return <div className="text-center p-12">Loading session...</div>;
  }

  if (error) {
    return <div className="text-center p-12 text-destructive">{error}</div>;
  }

  if (!session) {
    return <div className="text-center p-12">Session not found.</div>;
  }
  
  const activeAgents = session.agents.filter((agent) => agent.status !== "idle");

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
              Session {session.id}
            </Badge>
            <div>
              <CardTitle className="text-3xl font-semibold">
                {session.ticker} multi-agent briefing
              </CardTitle>
              <CardDescription>
                Updated {formatDate(session.updatedAt ?? session.createdAt)}
              </CardDescription>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              <span className="inline-flex items-center gap-1 rounded-full bg-surface-muted/70 px-3 py-1">
                <CircleDot className="h-3.5 w-3.5 text-success" /> {session.status.toUpperCase()}
              </span>
              <span>Conviction {formatPercent(session.decision?.conviction ?? 0)}</span>
              <span>Risk {session.risk ? session.risk.overall.toUpperCase() : "N/A"}</span>
            </div>
          </div>
          <div className="relative z-10 flex flex-col gap-3 sm:flex-row sm:items-center">
            <Button variant="outline" className="border-border/70">
              Download Report
            </Button>
            <Button className="gap-2" onClick={() => router.push('/dashboard')}>
              Go to Dashboard
              <ArrowUpRight className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="relative z-10 grid gap-4 pt-6 text-sm text-muted-foreground sm:grid-cols-2 lg:grid-cols-4">
          {session.agents.length > 0 && (
            <div>
              <p className="font-medium text-foreground">Active Agents</p>
              <p className="text-2xl font-bold text-foreground">{activeAgents.length}</p>
            </div>
          )}
          {session.insights.length > 0 && (
            <div>
              <p className="font-medium text-foreground">Insights</p>
              <p className="text-2xl font-bold text-foreground">{session.insights.length}</p>
            </div>
          )}
          {session.decision && (
            <div>
              <p className="font-medium text-foreground">Decision</p>
              <p className="text-2xl font-bold text-foreground uppercase">{session.decision.action}</p>
            </div>
          )}
          <div>
            <p className="font-medium text-foreground">Events</p>
            <p className="text-2xl font-bold text-foreground">{streamEvents.length}</p>
          </div>
        </CardContent>
      </Card>
      
      {/* Session Event Timeline */}
      <SessionEventTimeline 
        events={streamEvents} 
        isConnected={isConnected}
        error={streamError}
      />
    </div>
  );
}