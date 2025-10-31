"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Plus, Search, Bot } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { tradingAgentsGradients } from "@tradingagents/shared/theme";
import { api } from "@/lib/api/client";
import type { TradingSession } from "@tradingagents/shared/domain";
import { formatDate } from "@tradingagents/shared/utils/format";

export function SessionManager() {
  const [sessions, setSessions] = useState<TradingSession[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newTicker, setNewTicker] = useState("");
  const router = useRouter();

  useEffect(() => {
    async function fetchSessions() {
      try {
        setIsLoading(true);
        const response = await api.sessions.list();
        setSessions(response);
      } catch (err) {
        setError("Failed to fetch trading sessions.");
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    }
    fetchSessions();
  }, []);

  const handleStartSession = async () => {
    if (!newTicker.trim()) return;
    try {
      const response = await api.sessions.run({
        ticker: newTicker.trim().toUpperCase(),
      });
      router.push(`/sessions/${response.session_id}`);
    } catch (err) {
      setError(`Failed to start session for ${newTicker}.`);
      console.error(err);
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
              />
            </div>
            <Button onClick={handleStartSession} disabled={!newTicker.trim()}>
              <Plus className="mr-2 h-4 w-4" />
              Start New Session
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-center">
          <p className="text-sm font-semibold text-destructive">{error}</p>
        </div>
      )}

      {isLoading ? (
        <div className="text-center text-muted-foreground">Loading sessions...</div>
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