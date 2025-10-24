"use client";

import { useEffect, useState, useCallback } from "react";
import type { TradingSignal, StreamEvent } from "@tradingagents/shared/domain";
import { SSEClient } from "@tradingagents/shared/clients";

export interface UseRealtimeSignalsOptions {
  portfolioId?: number;
  enabled?: boolean;
  baseUrl?: string;
  maxSignals?: number;
}

export function useRealtimeSignals(options: UseRealtimeSignalsOptions = {}) {
  const { portfolioId, enabled = true, baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000", maxSignals = 50 } = options;
  const [signals, setSignals] = useState<TradingSignal[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const streamEvent: StreamEvent = JSON.parse(event.data);
      
      if (streamEvent.type === "signal") {
        setSignals((prev) => {
          const updated = [streamEvent.data, ...prev];
          return updated.slice(0, maxSignals);
        });
      } else if (streamEvent.type === "error") {
        setError(new Error(streamEvent.data.message));
      }
    } catch (err) {
      console.error("Error parsing SSE message:", err);
      setError(err instanceof Error ? err : new Error("Failed to parse message"));
    }
  }, [maxSignals]);

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

    const endpoint = portfolioId 
      ? `${baseUrl}/api/stream/signals/${portfolioId}`
      : `${baseUrl}/api/stream/signals`;

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
  }, [portfolioId, enabled, baseUrl, handleMessage, handleError, handleOpen]);

  return { signals, isConnected, error };
}
