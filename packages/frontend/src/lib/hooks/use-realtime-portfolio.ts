"use client";

import { useEffect, useState, useCallback } from "react";
import type { PortfolioUpdate, StreamEvent } from "@tradingagents/shared/domain";
import { SSEClient } from "@tradingagents/shared/clients";

export interface UseRealtimePortfolioOptions {
  portfolioId: number;
  enabled?: boolean;
  baseUrl?: string;
}

export function useRealtimePortfolio(options: UseRealtimePortfolioOptions) {
  const { portfolioId, enabled = true, baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000" } = options;
  const [data, setData] = useState<PortfolioUpdate | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const streamEvent: StreamEvent = JSON.parse(event.data);
      
      if (streamEvent.type === "portfolio_update") {
        setData(streamEvent.data);
      } else if (streamEvent.type === "error") {
        setError(new Error(streamEvent.data.message));
      }
    } catch (err) {
      console.error("Error parsing SSE message:", err);
      setError(err instanceof Error ? err : new Error("Failed to parse message"));
    }
  }, []);

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
      url: `${baseUrl}/api/stream/portfolio/${portfolioId}`,
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

  return { data, isConnected, error };
}
