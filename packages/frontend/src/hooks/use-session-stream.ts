"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { SSEClient } from "@tradingagents/shared/clients";

export interface SessionEvent {
  type: string;
  message?: string;
  payload?: Record<string, unknown>;
}

interface UseSessionStreamOptions {
  sessionId: string;
  enabled?: boolean;
  baseUrl?: string;
}

interface UseSessionStreamReturn {
  events: SessionEvent[];
  isConnected: boolean;
  error: Error | null;
  addBufferedEvents: (events: SessionEvent[]) => void;
  clearEvents: () => void;
}

export function useSessionStream({
  sessionId,
  enabled = true,
  baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
}: UseSessionStreamOptions): UseSessionStreamReturn {
  const [events, setEvents] = useState<SessionEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const clientRef = useRef<SSEClient | null>(null);

  const addBufferedEvents = useCallback((bufferedEvents: SessionEvent[]) => {
    setEvents(prev => {
      // Add buffered events if they don't already exist
      const existingIds = new Set(
        prev.map((e, i) => `${e.type}-${e.message}-${i}`)
      );
      const newEvents = bufferedEvents.filter((e, i) => 
        !existingIds.has(`${e.type}-${e.message}-${i}`)
      );
      return [...newEvents, ...prev];
    });
  }, []);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  useEffect(() => {
    if (!enabled || !sessionId) {
      return;
    }

    const url = `${baseUrl}/sessions/${sessionId}/events`;

    const client = new SSEClient({
      url,
      onMessage: (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          
          // Handle different event structures
          const sessionEvent: SessionEvent = {
            type: data.type || "event",
            message: data.message,
            payload: data.payload || {},
            ...data, // Include any other fields
          };

          setEvents(prev => [...prev, sessionEvent]);
          setError(null);
        } catch (err) {
          console.error("Error parsing SSE message:", err);
          setError(
            err instanceof Error ? err : new Error("Failed to parse message")
          );
        }
      },
      onError: () => {
        setIsConnected(false);
        setError(new Error("Connection error"));
      },
      onOpen: () => {
        setIsConnected(true);
        setError(null);
      },
    });

    client.connect();
    clientRef.current = client;

    return () => {
      client.disconnect();
      clientRef.current = null;
      setIsConnected(false);
    };
  }, [sessionId, enabled, baseUrl]);

  return {
    events,
    isConnected,
    error,
    addBufferedEvents,
    clearEvents,
  };
}
