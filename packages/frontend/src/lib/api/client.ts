const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: any
  ) {
    super(message);
    this.name = "APIError";
  }
}

async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new APIError(
      errorData.detail || `Request failed with status ${response.status}`,
      response.status,
      errorData
    );
  }

  if (response.status === 204) {
    return null as T;
  }

  const text = await response.text();
  if (!text) {
    return null as T;
  }

  return JSON.parse(text) as T;
}

export const api = {
  // Vendor endpoints
  vendors: {
    list: () => fetchAPI<any>("/api/vendors"),
    get: (vendorName: string) => fetchAPI<any>(`/api/vendors/${vendorName}`),
    getConfig: (vendorName: string) => fetchAPI<any>(`/api/vendors/${vendorName}/config`),
    updateConfig: (vendorName: string, config: any) =>
      fetchAPI<any>(`/api/vendors/${vendorName}/config`, {
        method: "PUT",
        body: JSON.stringify({ config }),
      }),
    getCapabilities: (capability: string) =>
      fetchAPI<any>(`/api/vendors/capabilities/${capability}`),
    getRoutingConfig: () => fetchAPI<any>("/api/vendors/routing/config"),
    getMethodRoutingConfig: (method: string) =>
      fetchAPI<any>(`/api/vendors/routing/config/${method}`),
    updateRoutingConfig: (method: string, vendors: string[]) =>
      fetchAPI<any>("/api/vendors/routing/config", {
        method: "PUT",
        body: JSON.stringify({ method, vendors }),
      }),
    reloadConfig: () =>
      fetchAPI<any>("/api/vendors/config/reload", { method: "POST" }),
  },

  // LLM provider endpoints
  llmProviders: {
    list: () => fetchAPI<any>("/api/llm-providers"),
    listModels: (provider: string) => fetchAPI<any>(`/api/llm-providers/${provider}/models`),
    validateKey: (payload: {
      provider: string;
      api_key: string;
      model_name?: string;
      temperature?: number;
      max_tokens?: number;
      top_p?: number;
    }) =>
      fetchAPI<any>("/api/llm-providers/validate-key", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  },

  // Agent endpoints
  agents: {
    list: (params?: { role?: string; is_active?: boolean; skip?: number; limit?: number }) => {
      const queryParams = new URLSearchParams();
      if (params?.role) queryParams.append("role", params.role);
      if (params?.is_active !== undefined) queryParams.append("is_active", String(params.is_active));
      if (params?.skip !== undefined) queryParams.append("skip", String(params.skip));
      if (params?.limit !== undefined) queryParams.append("limit", String(params.limit));

      const query = queryParams.toString();
      return fetchAPI<any>(`/api/agents${query ? `?${query}` : ""}`);
    },
    get: (agentId: number) => fetchAPI<any>(`/api/agents/${agentId}`),
    getByName: (agentName: string) => fetchAPI<any>(`/api/agents/by-name/${agentName}`),
    create: (data: any) =>
      fetchAPI<any>("/api/agents", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (agentId: number, data: any) =>
      fetchAPI<any>(`/api/agents/${agentId}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    delete: (agentId: number) =>
      fetchAPI<void>(`/api/agents/${agentId}`, { method: "DELETE" }),
    activate: (agentId: number) =>
      fetchAPI<any>(`/api/agents/${agentId}/activate`, { method: "POST" }),
    deactivate: (agentId: number) =>
      fetchAPI<any>(`/api/agents/${agentId}/deactivate`, { method: "POST" }),
    reload: () => fetchAPI<any>("/api/agents/reload", { method: "POST" }),
    listLLMConfigs: (
      agentId: number,
      options?: { enabledOnly?: boolean },
    ) => {
      const query = options?.enabledOnly ? "?enabled_only=true" : "";
      return fetchAPI<any>(`/api/agents/${agentId}/llm-config${query}`);
    },
    upsertLLMConfig: (agentId: number, config: any) =>
      fetchAPI<any>(`/api/agents/${agentId}/llm-config`, {
        method: "PUT",
        body: JSON.stringify(config),
      }),
    bulkAssignLLMConfigs: (payload: any) =>
      fetchAPI<any>("/api/agents/bulk-llm-config", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    testLLM: (agentId: number, configId?: number) => {
      const query = configId ? `?config_id=${configId}` : "";
      return fetchAPI<any>(`/api/agents/${agentId}/test-llm${query}`, {
        method: "POST",
      });
    },
    llmUsage: (
      agentId: number,
      params?: { start?: string; end?: string; limit?: number },
    ) => {
      const queryParams = new URLSearchParams();
      if (params?.start) queryParams.append("start", params.start);
      if (params?.end) queryParams.append("end", params.end);
      if (params?.limit !== undefined) queryParams.append("limit", String(params.limit));
      const query = queryParams.toString();
      return fetchAPI<any>(`/api/agents/${agentId}/llm-usage${query ? `?${query}` : ""}`);
    },
  },
};
