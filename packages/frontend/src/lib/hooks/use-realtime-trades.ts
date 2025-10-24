"use client";

import { useEffect, useState, useCallback } from "react";
import type { Trade, StreamEvent } from "@tradingagents/shared/domain";
import { SSEClient } from "@tradingagents/shared/clients";

export interface UseRealtimeTradesOptions {
  portfolioId: number;
  enabled?: boolean;
  baseUrl?: string;
  maxTrades?: number;
}

export function useRealtimeTrades(options: UseRealtimeTradesOptions) {
  const { portfolioId, enabled = true, baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000", maxTrades = 50 } = options;
  const [trades, setTrades] = useState<Trade[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const streamEvent: StreamEvent = JSON.parse(event.data);
      
      if (streamEvent.type === "trade") {
        setTrades((prev) => {
          const updated = [streamEvent.data, ...prev];
          return updated.slice(0, maxTrades);
        });
      } else if (streamEvent.type === "error") {
        setError(new Error(streamEvent.data.message));
      }
    } catch (err) {
      console.error("Error parsing SSE message:", err);
      setError(err instanceof Error ? err : new Error("Failed to parse message"));
    }
  }, [maxTrades]);

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

    const client = new SSEClient({
      url: `${baseUrl}/api/stream/trades/${portfolioId}`,
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

  return { trades, isConnected, error };
}
