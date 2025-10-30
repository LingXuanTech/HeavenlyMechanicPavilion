"use client";

import * as React from "react";
import { SSEClient } from "@tradingagents/shared/clients";

interface UseLLMConfigUpdatesOptions {
  enabled?: boolean;
  onEvent?: (event: Record<string, unknown>) => void;
}

export function useLLMConfigUpdates({ enabled = true, onEvent }: UseLLMConfigUpdatesOptions = {}) {
  const [isConnected, setIsConnected] = React.useState(false);
  const [lastEvent, setLastEvent] = React.useState<Record<string, unknown> | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!enabled) {
      return undefined;
    }

    const baseUrl = process.env.NEXT_PUBLIC_LLM_CONFIG_STREAM_URL
      || `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/stream/llm-config`;

    let cancelled = false;

    const client = new SSEClient({
      url: baseUrl,
      onOpen: () => {
        if (cancelled) return;
        setIsConnected(true);
        setError(null);
      },
      onError: (event) => {
        console.error("LLM config SSE error", event);
        if (cancelled) return;
        setIsConnected(false);
        setError("Connection error");
      },
      onMessage: (event) => {
        if (cancelled) return;
        try {
          const payload = JSON.parse(event.data);
          setLastEvent(payload);
          onEvent?.(payload);
        } catch (err) {
          console.warn("Unable to parse LLM config event", err);
        }
      },
    });

    client.connect();

    return () => {
      cancelled = true;
      client.disconnect();
      setIsConnected(false);
    };
  }, [enabled, onEvent]);

  return { isConnected, lastEvent, error };
}
