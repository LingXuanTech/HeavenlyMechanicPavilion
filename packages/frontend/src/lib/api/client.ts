import { HttpClient } from "@tradingagents/shared/clients";
import {
  SessionSummary,
  SessionEventSummary,
  enrichSessionWithEvents,
  normalizeSessionSummary,
  TradingSession,
} from "@tradingagents/shared/domain";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ============================================================================
// Error Handling
// ============================================================================

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: unknown
  ) {
    super(message);
    this.name = "APIError";
  }
}

// Wrap HttpClient errors in APIError for backward compatibility
function wrapError(err: unknown): APIError {
  if (err instanceof Error) {
    const status = (err as Error & { status?: number }).status ?? 500;
    return new APIError(err.message, status);
  }
  return new APIError("Unknown error occurred", 500);
}

// ============================================================================
// Type Definitions - Vendors
// ============================================================================

export interface VendorPluginInfo {
  name: string;
  provider: string;
  description: string;
  version: string;
  priority: number;
  capabilities: string[];
  rate_limits: Record<string, number | null>;
  is_active: boolean;
}

export interface VendorPluginList {
  plugins: VendorPluginInfo[];
  count: number;
}

export interface VendorConfigResponse {
  vendor_name: string;
  config: Record<string, unknown>;
}

export interface VendorCapabilitiesResponse {
  capability: string;
  vendors: string[];
}

export interface AllRoutingConfigResponse {
  routing: Record<string, string[]>;
}

export interface RoutingConfigResponse {
  method: string;
  vendors: string[];
}

export interface ConfigReloadResponse {
  success: boolean;
  message: string;
  last_reload: string | null;
}

// ============================================================================
// Type Definitions - Agents
// ============================================================================

export interface AgentConfigResponse {
  id: number;
  name: string;
  agent_type: string;
  role: string;
  description: string | null;
  llm_config: Record<string, unknown>;
  prompt_template: string;
  capabilities?: string[];
  required_tools?: string[];
  requires_memory: boolean;
  memory_name: string | null;
  is_reserved: boolean;
  slot_name: string | null;
  is_active: boolean;
  version: string;
  config?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  active_llm_config: Record<string, unknown> | null;
}

export interface AgentConfigList {
  agents: AgentConfigResponse[];
  total: number;
}

export interface AgentConfigCreate {
  name: string;
  agent_type: string;
  role: string;
  description?: string;
  llm_config?: Record<string, unknown>;
  prompt_template?: string;
  capabilities?: string[];
  required_tools?: string[];
  requires_memory?: boolean;
  memory_name?: string;
  is_reserved?: boolean;
  slot_name?: string;
  is_active?: boolean;
  version?: string;
  config?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface AgentConfigUpdate {
  agent_type?: string;
  role?: string;
  description?: string;
  llm_config?: Record<string, unknown>;
  prompt_template?: string;
  capabilities?: string[];
  required_tools?: string[];
  requires_memory?: boolean;
  memory_name?: string;
  slot_name?: string;
  is_active?: boolean;
  version?: string;
  config?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface AgentLLMConfigResponse {
  id: number;
  agent_id: number;
  provider: string;
  model_name: string;
  temperature: number;
  max_tokens: number | null;
  top_p: number | null;
  has_api_key_override: boolean;
  fallback_provider: string | null;
  fallback_model: string | null;
  cost_per_1k_input_tokens: number;
  cost_per_1k_output_tokens: number;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  metadata_json: string | null;
}

export interface AgentLLMConfigUpsert {
  provider: string;
  model_name: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  api_key?: string;
  fallback_provider?: string;
  fallback_model?: string;
  cost_per_1k_input_tokens?: number;
  cost_per_1k_output_tokens?: number;
  enabled?: boolean;
  metadata_json?: string;
}

// ============================================================================
// Type Definitions - Sessions
// ============================================================================

export interface RunSessionRequest {
  ticker: string;
  trade_date?: string;
  selected_analysts?: string[];
}

export interface RunSessionResponse {
  session_id: string;
  stream_endpoint: string;
}

export interface SessionListResponse {
  sessions: SessionSummary[];
  total: number;
  skip: number;
  limit: number;
}

export interface SessionDetailResponse {
  session: SessionSummary;
  events: SessionEventSummary[];
}

// ============================================================================
// HTTP Client Instance
// ============================================================================

const httpClient = new HttpClient({
  baseUrl: API_BASE_URL,
});

// ============================================================================
// API Client
// ============================================================================

export const api = {
  // Vendor endpoints
  vendors: {
    list: async (): Promise<VendorPluginList> => {
      try {
        return await httpClient.get<VendorPluginList>("/api/vendors");
      } catch (err) {
        throw wrapError(err);
      }
    },

    get: async (vendorName: string): Promise<VendorPluginInfo> => {
      try {
        return await httpClient.get<VendorPluginInfo>(`/api/vendors/${vendorName}`);
      } catch (err) {
        throw wrapError(err);
      }
    },

    getConfig: async (vendorName: string): Promise<VendorConfigResponse> => {
      try {
        return await httpClient.get<VendorConfigResponse>(`/api/vendors/${vendorName}/config`);
      } catch (err) {
        throw wrapError(err);
      }
    },

    updateConfig: async (
      vendorName: string,
      config: Record<string, unknown>
    ): Promise<VendorConfigResponse> => {
      try {
        return await httpClient.put<VendorConfigResponse, { config: Record<string, unknown> }>(
          `/api/vendors/${vendorName}/config`,
          { config }
        );
      } catch (err) {
        throw wrapError(err);
      }
    },

    getCapabilities: async (capability: string): Promise<VendorCapabilitiesResponse> => {
      try {
        return await httpClient.get<VendorCapabilitiesResponse>(
          `/api/vendors/capabilities/${capability}`
        );
      } catch (err) {
        throw wrapError(err);
      }
    },

    getRoutingConfig: async (): Promise<AllRoutingConfigResponse> => {
      try {
        return await httpClient.get<AllRoutingConfigResponse>("/api/vendors/routing/config");
      } catch (err) {
        throw wrapError(err);
      }
    },

    getMethodRoutingConfig: async (method: string): Promise<RoutingConfigResponse> => {
      try {
        return await httpClient.get<RoutingConfigResponse>(`/api/vendors/routing/config/${method}`);
      } catch (err) {
        throw wrapError(err);
      }
    },

    updateRoutingConfig: async (
      method: string,
      vendors: string[]
    ): Promise<RoutingConfigResponse> => {
      try {
        return await httpClient.put<RoutingConfigResponse, { method: string; vendors: string[] }>(
          "/api/vendors/routing/config",
          { method, vendors }
        );
      } catch (err) {
        throw wrapError(err);
      }
    },

    reloadConfig: async (): Promise<ConfigReloadResponse> => {
      try {
        return await httpClient.post<ConfigReloadResponse>("/api/vendors/config/reload");
      } catch (err) {
        throw wrapError(err);
      }
    },
  },

  // Agent endpoints
  agents: {
    list: async (params?: {
      role?: string;
      is_active?: boolean;
      skip?: number;
      limit?: number;
    }): Promise<AgentConfigList> => {
      try {
        const queryParams = new URLSearchParams();
        if (params?.role) queryParams.append("role", params.role);
        if (params?.is_active !== undefined)
          queryParams.append("is_active", String(params.is_active));
        if (params?.skip !== undefined) queryParams.append("skip", String(params.skip));
        if (params?.limit !== undefined) queryParams.append("limit", String(params.limit));

        const query = queryParams.toString();
        return await httpClient.get<AgentConfigList>(`/api/agents${query ? `?${query}` : ""}`);
      } catch (err) {
        throw wrapError(err);
      }
    },

    get: async (agentId: number): Promise<AgentConfigResponse> => {
      try {
        return await httpClient.get<AgentConfigResponse>(`/api/agents/${agentId}`);
      } catch (err) {
        throw wrapError(err);
      }
    },

    getByName: async (agentName: string): Promise<AgentConfigResponse> => {
      try {
        return await httpClient.get<AgentConfigResponse>(`/api/agents/by-name/${agentName}`);
      } catch (err) {
        throw wrapError(err);
      }
    },

    create: async (data: AgentConfigCreate): Promise<AgentConfigResponse> => {
      try {
        return await httpClient.post<AgentConfigResponse, AgentConfigCreate>("/api/agents", data);
      } catch (err) {
        throw wrapError(err);
      }
    },

    update: async (agentId: number, data: AgentConfigUpdate): Promise<AgentConfigResponse> => {
      try {
        return await httpClient.put<AgentConfigResponse, AgentConfigUpdate>(
          `/api/agents/${agentId}`,
          data
        );
      } catch (err) {
        throw wrapError(err);
      }
    },

    delete: async (agentId: number): Promise<void> => {
      try {
        await httpClient.delete<void>(`/api/agents/${agentId}`);
      } catch (err) {
        throw wrapError(err);
      }
    },

    activate: async (agentId: number): Promise<AgentConfigResponse> => {
      try {
        return await httpClient.post<AgentConfigResponse>(`/api/agents/${agentId}/activate`);
      } catch (err) {
        throw wrapError(err);
      }
    },

    deactivate: async (agentId: number): Promise<AgentConfigResponse> => {
      try {
        return await httpClient.post<AgentConfigResponse>(`/api/agents/${agentId}/deactivate`);
      } catch (err) {
        throw wrapError(err);
      }
    },

    reload: async (): Promise<{ message: string }> => {
      try {
        return await httpClient.post<{ message: string }>("/api/agents/reload");
      } catch (err) {
        throw wrapError(err);
      }
    },

    getLLMConfig: async (agentId: number): Promise<AgentLLMConfigResponse> => {
      try {
        return await httpClient.get<AgentLLMConfigResponse>(`/api/agents/${agentId}/llm-config`);
      } catch (err) {
        throw wrapError(err);
      }
    },

    updateLLMConfig: async (
      agentId: number,
      config: AgentLLMConfigUpsert
    ): Promise<AgentLLMConfigResponse> => {
      try {
        return await httpClient.put<AgentLLMConfigResponse, AgentLLMConfigUpsert>(
          `/api/agents/${agentId}/llm-config`,
          config
        );
      } catch (err) {
        throw wrapError(err);
      }
    },

    listLLMConfigs: async (params?: {
      skip?: number;
      limit?: number;
    }): Promise<AgentLLMConfigResponse[]> => {
      try {
        const queryParams = new URLSearchParams();
        if (params?.skip !== undefined) queryParams.append("skip", String(params.skip));
        if (params?.limit !== undefined) queryParams.append("limit", String(params.limit));

        const query = queryParams.toString();
        return await httpClient.get<AgentLLMConfigResponse[]>(
          `/api/agents/llm-configs${query ? `?${query}` : ""}`
        );
      } catch (err) {
        throw wrapError(err);
      }
    },
  },

  // Session endpoints
  sessions: {
    list: async (params?: {
      skip?: number;
      limit?: number;
      status?: string;
      ticker?: string;
    }): Promise<TradingSession[]> => {
      try {
        const queryParams = new URLSearchParams();
        if (params?.skip !== undefined) queryParams.append("skip", String(params.skip));
        if (params?.limit !== undefined) queryParams.append("limit", String(params.limit));
        if (params?.status) queryParams.append("status", params.status);
        if (params?.ticker) queryParams.append("ticker", params.ticker);

        const query = queryParams.toString();
        const response = await httpClient.get<SessionListResponse>(
          `/api/sessions${query ? `?${query}` : ""}`
        );

        // Convert SessionSummary[] to TradingSession[] for backward compatibility
        // Since we don't have events here, we'll return sessions with empty agents/insights arrays
        return response.sessions.map((summary) => ({
          ...summary,
          agents: [],
          insights: [],
        }));
      } catch (err) {
        throw wrapError(err);
      }
    },

    get: async (sessionId: string): Promise<TradingSession> => {
      try {
        const response = await httpClient.get<SessionDetailResponse>(`/api/sessions/${sessionId}`);
        const summary = normalizeSessionSummary(response.session);
        if (!summary) {
          throw new Error("Invalid session data received from server");
        }

        // Create SessionEventsHistory from the events in the detail response
        const eventsHistory = {
          session_id: sessionId,
          events: response.events.map((e) => ({
            timestamp: e.timestamp,
            event: e.event as Record<string, unknown>,
          })),
          count: response.events.length,
        };

        // Use the enrichSessionWithEvents helper to build a full TradingSession
        return enrichSessionWithEvents(summary, eventsHistory);
      } catch (err) {
        throw wrapError(err);
      }
    },

    run: async (data: RunSessionRequest): Promise<RunSessionResponse> => {
      try {
        return await httpClient.post<RunSessionResponse, RunSessionRequest>("/api/sessions", data);
      } catch (err) {
        throw wrapError(err);
      }
    },
  },
};
