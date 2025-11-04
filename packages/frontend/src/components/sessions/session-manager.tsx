"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Plus, Search, Bot } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { tradingAgentsGradients } from "@tradingagents/shared/theme";
import { api } from "@/lib/api/client";
import type { TradingSession } from "@tradingagents/shared/domain";
import { formatDate } from "@tradingagents/shared/utils/format";

const SKELETON_COUNT = 3;

export function SessionManager() {
  const [sessions, setSessions] = useState<TradingSession[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [newTicker, setNewTicker] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const router = useRouter();
  const { showToast } = useToast();
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    abortControllerRef.current = controller;

    async function fetchSessions() {
      try {
        setIsLoading(true);
        const response = await api.sessions.list();
        if (!controller.signal.aborted) {
          setSessions(response);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          showToast({
            type: "error",
            title: "Failed to fetch sessions",
            description: err instanceof Error ? err.message : "An error occurred while loading sessions.",
          });
          console.error(err);
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    fetchSessions();

    return () => {
      controller.abort();
    };
  }, [showToast]);

  const handleStartSession = async () => {
    if (!newTicker.trim()) return;

    setIsSubmitting(true);
    try {
      const response = await api.sessions.run({
        ticker: newTicker.trim().toUpperCase(),
      });
      setNewTicker("");
      router.push(`/sessions/${response.session_id}`);
    } catch (err) {
      showToast({
        type: "error",
        title: `Failed to start session for ${newTicker}`,
        description: err instanceof Error ? err.message : "An error occurred while starting the session.",
      });
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-8">
      <Card className="relative overflow-hidden border-none bg-surface text-foreground shadow-pop">
        <div
          className="pointer-events-none absolute inset-0 opacity-90"
          style={{ backgroundImage: tradingAgentsGradients.sunrise }}
        />
        <CardHeader className="relative z-10">
          <CardTitle className="text-3xl font-semibold">Trading Sessions</CardTitle>
          <CardDescription>
            Manage and launch multi-agent trading analysis sessions.
          </CardDescription>
        </CardHeader>
        <CardContent className="relative z-10">
          <div className="flex flex-col gap-4 sm:flex-row">
            <div className="relative flex-grow">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Enter a stock ticker (e.g., AAPL)"
                className="pl-10"
                value={newTicker}
                onChange={(e) => setNewTicker(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleStartSession()}
                disabled={isSubmitting}
              />
            </div>
            <Button 
              onClick={handleStartSession} 
              disabled={!newTicker.trim() || isSubmitting}
            >
              <Plus className="mr-2 h-4 w-4" />
              {isSubmitting ? "Starting..." : "Start New Session"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: SKELETON_COUNT }).map((_, i) => (
            <Card key={i} className="overflow-hidden">
              <CardHeader>
                <div className="flex justify-between items-start gap-4">
                  <Skeleton className="h-6 w-24" />
                  <Skeleton className="h-6 w-16" />
                </div>
                <Skeleton className="h-4 w-40 mt-2" />
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-4 w-40" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : sessions.length === 0 ? (
        <div className="text-center py-12">
          <Bot className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-semibold">No active sessions</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Start a new session above to begin your analysis.
          </p>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {sessions.map((session) => (
            <Card 
              key={session.id} 
              className="cursor-pointer hover:border-primary/80 transition-colors"
              onClick={() => router.push(`/sessions/${session.id}`)}
            >
              <CardHeader>
                <CardTitle className="flex justify-between items-center">
                  <span>{session.ticker}</span>
                  <span className={`text-xs uppercase px-2 py-1 rounded-full ${
                    session.status === 'running' ? 'bg-primary/20 text-primary' : 'bg-muted/40 text-muted-foreground'
                  }`}>
                    {session.status}
                  </span>
                </CardTitle>
                <CardDescription>Session ID: {session.id}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-sm text-muted-foreground space-y-2">
                  <p>Started: {formatDate(session.createdAt)}</p>
                  <p>Last Update: {formatDate(session.updatedAt ?? session.createdAt)}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}