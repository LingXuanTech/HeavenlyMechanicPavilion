"use client";

import { create } from "zustand";
import type {
  PortfolioUpdate,
  TradingSignal,
  Trade,
  AgentActivity,
  StreamEvent,
} from "@tradingagents/shared/domain";
import { SSEClient } from "@tradingagents/shared/clients";

interface RealtimeState {
  // Portfolio state
  portfolio: PortfolioUpdate | null;
  portfolioConnected: boolean;
  portfolioError: Error | null;

  // Signals state
  signals: TradingSignal[];
  signalsConnected: boolean;
  signalsError: Error | null;

  // Trades state
  trades: Trade[];
  tradesConnected: boolean;
  tradesError: Error | null;

  // Agent activity state
  agentActivities: AgentActivity[];
  agentActivitiesConnected: boolean;
  agentActivitiesError: Error | null;

  // SSE clients
  clients: {
    portfolio?: SSEClient;
    signals?: SSEClient;
    trades?: SSEClient;
    agentActivities?: SSEClient;
  };

  // Configuration
  config: {
    portfolioId?: number;
    sessionId?: string;
    baseUrl: string;
    maxSignals: number;
    maxTrades: number;
    maxActivities: number;
  };

  // Actions
  setPortfolio: (data: PortfolioUpdate | null) => void;
  setPortfolioConnected: (connected: boolean) => void;
  setPortfolioError: (error: Error | null) => void;

  addSignal: (signal: TradingSignal) => void;
  setSignalsConnected: (connected: boolean) => void;
  setSignalsError: (error: Error | null) => void;
  clearSignals: () => void;

  addTrade: (trade: Trade) => void;
  setTradesConnected: (connected: boolean) => void;
  setTradesError: (error: Error | null) => void;
  clearTrades: () => void;

  addAgentActivity: (activity: AgentActivity) => void;
  setAgentActivitiesConnected: (connected: boolean) => void;
  setAgentActivitiesError: (error: Error | null) => void;
  clearAgentActivities: () => void;

  // Connection management
  connectPortfolio: (portfolioId: number) => void;
  disconnectPortfolio: () => void;

  connectSignals: (portfolioId?: number) => void;
  disconnectSignals: () => void;

  connectTrades: (portfolioId: number) => void;
  disconnectTrades: () => void;

  connectAgentActivities: (sessionId?: string) => void;
  disconnectAgentActivities: () => void;

  disconnectAll: () => void;

  // Configuration
  updateConfig: (config: Partial<RealtimeState["config"]>) => void;
}

export const useRealtimeStore = create<RealtimeState>((set, get) => ({
  // Initial state
  portfolio: null,
  portfolioConnected: false,
  portfolioError: null,

  signals: [],
  signalsConnected: false,
  signalsError: null,

  trades: [],
  tradesConnected: false,
  tradesError: null,

  agentActivities: [],
  agentActivitiesConnected: false,
  agentActivitiesError: null,

  clients: {},

  config: {
    baseUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    maxSignals: 50,
    maxTrades: 50,
    maxActivities: 100,
  },

  // Portfolio actions
  setPortfolio: (data) => set({ portfolio: data }),
  setPortfolioConnected: (connected) => set({ portfolioConnected: connected }),
  setPortfolioError: (error) => set({ portfolioError: error }),

  // Signals actions
  addSignal: (signal) =>
    set((state) => ({
      signals: [signal, ...state.signals].slice(0, state.config.maxSignals),
    })),
  setSignalsConnected: (connected) => set({ signalsConnected: connected }),
  setSignalsError: (error) => set({ signalsError: error }),
  clearSignals: () => set({ signals: [] }),

  // Trades actions
  addTrade: (trade) =>
    set((state) => ({
      trades: [trade, ...state.trades].slice(0, state.config.maxTrades),
    })),
  setTradesConnected: (connected) => set({ tradesConnected: connected }),
  setTradesError: (error) => set({ tradesError: error }),
  clearTrades: () => set({ trades: [] }),

  // Agent activities actions
  addAgentActivity: (activity) =>
    set((state) => ({
      agentActivities: [activity, ...state.agentActivities].slice(
        0,
        state.config.maxActivities
      ),
    })),
  setAgentActivitiesConnected: (connected) =>
    set({ agentActivitiesConnected: connected }),
  setAgentActivitiesError: (error) => set({ agentActivitiesError: error }),
  clearAgentActivities: () => set({ agentActivities: [] }),

  // Portfolio connection
  connectPortfolio: (portfolioId) => {
    const state = get();
    
    // Disconnect existing client
    state.clients.portfolio?.disconnect();

    const client = new SSEClient({
      url: `${state.config.baseUrl}/api/stream/portfolio/${portfolioId}`,
      onMessage: (event: MessageEvent) => {
        try {
          const streamEvent: StreamEvent = JSON.parse(event.data);
          
          if (streamEvent.type === "portfolio_update") {
            state.setPortfolio(streamEvent.data);
          } else if (streamEvent.type === "error") {
            state.setPortfolioError(new Error(streamEvent.data.message));
          }
        } catch (err) {
          console.error("Error parsing portfolio SSE message:", err);
          state.setPortfolioError(
            err instanceof Error ? err : new Error("Failed to parse message")
          );
        }
      },
      onError: () => {
        state.setPortfolioConnected(false);
        state.setPortfolioError(new Error("Connection error"));
      },
      onOpen: () => {
        state.setPortfolioConnected(true);
        state.setPortfolioError(null);
      },
    });

    client.connect();

    set((state) => ({
      clients: { ...state.clients, portfolio: client },
      config: { ...state.config, portfolioId },
    }));
  },

  disconnectPortfolio: () => {
    const state = get();
    state.clients.portfolio?.disconnect();
    set((state) => ({
      clients: { ...state.clients, portfolio: undefined },
      portfolioConnected: false,
    }));
  },

  // Signals connection
  connectSignals: (portfolioId) => {
    const state = get();
    
    // Disconnect existing client
    state.clients.signals?.disconnect();

    const endpoint = portfolioId
      ? `${state.config.baseUrl}/api/stream/signals/${portfolioId}`
      : `${state.config.baseUrl}/api/stream/signals`;

    const client = new SSEClient({
      url: endpoint,
      onMessage: (event: MessageEvent) => {
        try {
          const streamEvent: StreamEvent = JSON.parse(event.data);
          
          if (streamEvent.type === "signal") {
            state.addSignal(streamEvent.data);
          } else if (streamEvent.type === "error") {
            state.setSignalsError(new Error(streamEvent.data.message));
          }
        } catch (err) {
          console.error("Error parsing signals SSE message:", err);
          state.setSignalsError(
            err instanceof Error ? err : new Error("Failed to parse message")
          );
        }
      },
      onError: () => {
        state.setSignalsConnected(false);
        state.setSignalsError(new Error("Connection error"));
      },
      onOpen: () => {
        state.setSignalsConnected(true);
        state.setSignalsError(null);
      },
    });

    client.connect();

    set((state) => ({
      clients: { ...state.clients, signals: client },
    }));
  },

  disconnectSignals: () => {
    const state = get();
    state.clients.signals?.disconnect();
    set((state) => ({
      clients: { ...state.clients, signals: undefined },
      signalsConnected: false,
    }));
  },

  // Trades connection
  connectTrades: (portfolioId) => {
    const state = get();
    
    // Disconnect existing client
    state.clients.trades?.disconnect();

    const client = new SSEClient({
      url: `${state.config.baseUrl}/api/stream/trades/${portfolioId}`,
      onMessage: (event: MessageEvent) => {
        try {
          const streamEvent: StreamEvent = JSON.parse(event.data);
          
          if (streamEvent.type === "trade") {
            state.addTrade(streamEvent.data);
          } else if (streamEvent.type === "error") {
            state.setTradesError(new Error(streamEvent.data.message));
          }
        } catch (err) {
          console.error("Error parsing trades SSE message:", err);
          state.setTradesError(
            err instanceof Error ? err : new Error("Failed to parse message")
          );
        }
      },
      onError: () => {
        state.setTradesConnected(false);
        state.setTradesError(new Error("Connection error"));
      },
      onOpen: () => {
        state.setTradesConnected(true);
        state.setTradesError(null);
      },
    });

    client.connect();

    set((state) => ({
      clients: { ...state.clients, trades: client },
    }));
  },

  disconnectTrades: () => {
    const state = get();
    state.clients.trades?.disconnect();
    set((state) => ({
      clients: { ...state.clients, trades: undefined },
      tradesConnected: false,
    }));
  },

  // Agent activities connection
  connectAgentActivities: (sessionId) => {
    const state = get();
    
    // Disconnect existing client
    state.clients.agentActivities?.disconnect();

    const endpoint = sessionId
      ? `${state.config.baseUrl}/api/stream/agent-activity/${sessionId}`
      : `${state.config.baseUrl}/api/stream/agent-activity`;

    const client = new SSEClient({
      url: endpoint,
      onMessage: (event: MessageEvent) => {
        try {
          const streamEvent: StreamEvent = JSON.parse(event.data);
          
          if (streamEvent.type === "agent_activity") {
            state.addAgentActivity(streamEvent.data);
          } else if (streamEvent.type === "error") {
            state.setAgentActivitiesError(new Error(streamEvent.data.message));
          }
        } catch (err) {
          console.error("Error parsing agent activities SSE message:", err);
          state.setAgentActivitiesError(
            err instanceof Error ? err : new Error("Failed to parse message")
          );
        }
      },
      onError: () => {
        state.setAgentActivitiesConnected(false);
        state.setAgentActivitiesError(new Error("Connection error"));
      },
      onOpen: () => {
        state.setAgentActivitiesConnected(true);
        state.setAgentActivitiesError(null);
      },
    });

    client.connect();

    set((state) => ({
      clients: { ...state.clients, agentActivities: client },
      config: { ...state.config, sessionId },
    }));
  },

  disconnectAgentActivities: () => {
    const state = get();
    state.clients.agentActivities?.disconnect();
    set((state) => ({
      clients: { ...state.clients, agentActivities: undefined },
      agentActivitiesConnected: false,
    }));
  },

  disconnectAll: () => {
    const state = get();
    Object.values(state.clients).forEach((client) => client?.disconnect());
    set({
      clients: {},
      portfolioConnected: false,
      signalsConnected: false,
      tradesConnected: false,
      agentActivitiesConnected: false,
    });
  },

  updateConfig: (newConfig) =>
    set((state) => ({
      config: { ...state.config, ...newConfig },
    })),
}));