"use client";

import { useEffect, useState, useCallback } from "react";
import type { AgentActivity, StreamEvent } from "@tradingagents/shared/domain";
import { SSEClient } from "@tradingagents/shared/clients";

export interface UseRealtimeAgentActivityOptions {
  sessionId?: string;
  enabled?: boolean;
  baseUrl?: string;
  maxActivities?: number;
}

export function useRealtimeAgentActivity(options: UseRealtimeAgentActivityOptions = {}) {
  const { sessionId, enabled = true, baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000", maxActivities = 100 } = options;
  const [activities, setActivities] = useState<AgentActivity[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const streamEvent: StreamEvent = JSON.parse(event.data);
      
      if (streamEvent.type === "agent_activity") {
        setActivities((prev) => {
          const updated = [streamEvent.data, ...prev];
          return updated.slice(0, maxActivities);
        });
      } else if (streamEvent.type === "error") {
        setError(new Error(streamEvent.data.message));
      }
    } catch (err) {
      console.error("Error parsing SSE message:", err);
      setError(err instanceof Error ? err : new Error("Failed to parse message"));
    }
  }, [maxActivities]);

  const handleError = useCallback((event: Event) => {
    console.error("SSE connection error:", event);
    setIsConnected(false);
    setError(new Error("Connection error"));
  }, []);

  const handleOpen = useCallback(() => {
    setIsConnected(true);
    setError(null);
  }, []);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    const endpoint = sessionId 
      ? `${baseUrl}/api/stream/agent-activity/${sessionId}`
      : `${baseUrl}/api/stream/agent-activity`;

    const client = new SSEClient({
      url: endpoint,
      onMessage: handleMessage,
      onError: handleError,
      onOpen: handleOpen,
    });

    client.connect();

    return () => {
      client.disconnect();
      setIsConnected(false);
    };
  }, [sessionId, enabled, baseUrl, handleMessage, handleError, handleOpen]);

  return { activities, isConnected, error };
}
