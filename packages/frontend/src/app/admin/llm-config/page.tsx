"use client";

import * as React from "react";
import {
  Settings,
  Edit,
  Upload,
  Download,
  Users,
  Loader2,
  RefreshCw,
  CheckCircle,
  AlertCircle,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";
import { api, APIError } from "@/lib/api/client";
import {
  LLMConfigForm,
  LLMConfigFormErrors,
  LLMConfigFormValues,
  LLMProviderSummary,
} from "@/components/admin/llm/llm-config-form";
import {
  LLMProviderGrid,
  ProviderStatusRecord,
  ProviderHealthState,
} from "@/components/admin/llm/llm-provider-grid";
import {
  AgentLLMTestDialog,
  AgentLLMConfig,
} from "@/components/admin/llm/agent-llm-test-dialog";
import {
  LLMUsageDashboard,
  TimeRangeOption,
  AgentLLMUsageSummary,
} from "@/components/admin/llm/llm-usage-dashboard";
import { useLLMConfigUpdates } from "@/lib/hooks/use-llm-config-updates";
import { formatDate } from "@tradingagents/shared/utils/format";

interface AgentListItem {
  id: number;
  name: string;
  role: string;
  is_active: boolean;
  updated_at: string;
  llm_provider: string;
  llm_model: string;
  temperature: number;
  max_tokens: number | null;
  active_llm_config?: AgentLLMConfig;
}

const DEFAULT_TIME_RANGE: TimeRangeOption = "30d";

function getPrimaryConfig(agent: AgentListItem): AgentLLMConfig | null {
  return agent.active_llm_config ?? null;
}

function buildDefaultForm(
  providers: LLMProviderSummary[],
  seed?: Partial<LLMConfigFormValues>,
): LLMConfigFormValues {
  const fallbackProvider = providers[0];
  return {
    provider: seed?.provider || fallbackProvider?.provider || "",
    model_name:
      seed?.model_name
      || fallbackProvider?.models[0]?.name
      || "",
    temperature: seed?.temperature ?? 0.7,
    max_tokens: seed?.max_tokens ?? null,
    api_key: seed?.api_key,
    fallback_provider: seed?.fallback_provider ?? null,
    fallback_model: seed?.fallback_model ?? null,
  };
}

function validateLLMValues(values: LLMConfigFormValues): LLMConfigFormErrors {
  const errors: LLMConfigFormErrors = {};
  if (!values.provider) {
    errors.provider = "Provider is required";
  }
  if (!values.model_name) {
    errors.model_name = "Model is required";
  }
  if (values.temperature < 0 || values.temperature > 2 || Number.isNaN(values.temperature)) {
    errors.temperature = "Temperature must be between 0 and 2";
  }
  if (
    values.max_tokens !== null
    && values.max_tokens !== undefined
    && values.max_tokens < 1
  ) {
    errors.max_tokens = "Max tokens must be at least 1";
  }
  if (values.fallback_provider && !values.fallback_model) {
    errors.fallback_model = "Select a fallback model";
  }
  return errors;
}

function computeStartFromRange(range: TimeRangeOption): string | undefined {
  if (range === "all") {
    return undefined;
  }
  const now = new Date();
  const days = range === "7d" ? 7 : range === "30d" ? 30 : 90;
  const start = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
  return start.toISOString();
}

export default function LLMConfigurationAdminPage() {
  const { showToast } = useToast();
  const [agents, setAgents] = React.useState<AgentListItem[]>([]);
  const [loadingAgents, setLoadingAgents] = React.useState(false);
  const [providers, setProviders] = React.useState<LLMProviderSummary[]>([]);
  const [loadingProviders, setLoadingProviders] = React.useState(false);
  const [selectedAgents, setSelectedAgents] = React.useState<Set<number>>(new Set());
  const [bulkForm, setBulkForm] = React.useState<LLMConfigFormValues>({
    provider: "",
    model_name: "",
    temperature: 0.7,
    max_tokens: null,
    api_key: undefined,
    fallback_provider: null,
    fallback_model: null,
  });
  const [bulkErrors, setBulkErrors] = React.useState<LLMConfigFormErrors>({});
  const [bulkSaving, setBulkSaving] = React.useState(false);

  const [editAgent, setEditAgent] = React.useState<AgentListItem | null>(null);
  const [editForm, setEditForm] = React.useState<LLMConfigFormValues | null>(null);
  const [editErrors, setEditErrors] = React.useState<LLMConfigFormErrors>({});
  const [editSaving, setEditSaving] = React.useState(false);

  const [testAgent, setTestAgent] = React.useState<AgentListItem | null>(null);

  const [providerStatuses, setProviderStatuses] = React.useState<
    Record<string, ProviderStatusRecord>
  >({});

  const [timeRange, setTimeRange] = React.useState<TimeRangeOption>(DEFAULT_TIME_RANGE);
  const [usageSummaries, setUsageSummaries] = React.useState<
    Record<number, AgentLLMUsageSummary>
  >({});
  const [usageLoading, setUsageLoading] = React.useState(false);

  const selectAll = agents.length > 0 && selectedAgents.size === agents.length;

  const loadProviders = React.useCallback(async () => {
    try {
      setLoadingProviders(true);
      const response = await api.llmProviders.list();
      setProviders(response ?? []);
    } catch (error) {
      showToast({
        type: "error",
        title: "Failed to load providers",
        description: error instanceof APIError ? error.message : "Unable to load provider metadata",
      });
    } finally {
      setLoadingProviders(false);
    }
  }, [showToast]);

  const loadAgents = React.useCallback(async () => {
    try {
      setLoadingAgents(true);
      const response = await api.agents.list();
      const data: AgentListItem[] = response?.agents ?? [];
      setAgents(data);
      return data;
    } catch (error) {
      showToast({
        type: "error",
        title: "Failed to load agents",
        description: error instanceof APIError ? error.message : "Unable to fetch agents",
      });
      return [] as AgentListItem[];
    } finally {
      setLoadingAgents(false);
    }
  }, [showToast]);

  const refreshUsage = React.useCallback(
    async (agentBaseline?: AgentListItem[]) => {
      const agentList = agentBaseline ?? agents;
      if (agentList.length === 0) {
        setUsageSummaries({});
        return;
      }

      try {
        setUsageLoading(true);
        const start = computeStartFromRange(timeRange);
        const results = await Promise.all(
          agentList.map(async (agent) => {
            try {
              const summary = await api.agents.llmUsage(agent.id, {
                start,
                limit: 200,
              });
              return [agent.id, summary] as const;
            } catch (error) {
              console.warn("Failed to load usage for agent", agent.id, error);
              return null;
            }
          }),
        );
        const map: Record<number, AgentLLMUsageSummary> = {};
        results.forEach((entry) => {
          if (!entry) return;
          const [agentId, summary] = entry;
          map[agentId] = summary;
        });
        setUsageSummaries(map);
      } catch (error) {
        showToast({
          type: "error",
          title: "Failed to load usage",
          description: error instanceof APIError ? error.message : "Unable to refresh usage analytics",
        });
      } finally {
        setUsageLoading(false);
      }
    },
    [agents, showToast, timeRange],
  );

  React.useEffect(() => {
    loadProviders();
    loadAgents().then((list) => {
      refreshUsage(list);
    });
  }, [loadAgents, loadProviders, refreshUsage]);

  React.useEffect(() => {
    if (!providers.length) {
      return;
    }
    setBulkForm((prev) => {
      if (prev.provider && providers.some((provider) => provider.provider === prev.provider)) {
        return prev;
      }
      return buildDefaultForm(providers, prev);
    });
  }, [providers]);

  React.useEffect(() => {
    if (agents.length === 0) {
      setSelectedAgents(new Set());
    } else {
      setSelectedAgents((prev) => {
        const next = new Set<number>();
        agents.forEach((agent) => {
          if (prev.has(agent.id)) {
            next.add(agent.id);
          }
        });
        return next;
      });
    }
  }, [agents]);

  React.useEffect(() => {
    if (agents.length === 0) {
      return;
    }
    refreshUsage();
  }, [agents, timeRange, refreshUsage]);

  const { isConnected: realtimeConnected } = useLLMConfigUpdates({
    onEvent: React.useCallback(
      (event) => {
        if (!event) return;
        const type = event.type ?? event.event ?? "";
        if (
          type === "llm_config_updated"
          || type === "agent_updated"
          || event.resource === "agent_llm_config"
        ) {
          loadAgents().then((list) => refreshUsage(list));
        }
      },
      [loadAgents, refreshUsage],
    ),
  });

  const handleProviderStatusUpdate = React.useCallback(
    (provider: string, update: ProviderStatusRecord) => {
      setProviderStatuses((prev) => ({
        ...prev,
        [provider]: update,
      }));
    },
    [],
  );

  const handleToggleAgentSelection = (agentId: number, checked: boolean) => {
    setSelectedAgents((prev) => {
      const next = new Set(prev);
      if (checked) {
        next.add(agentId);
      } else {
        next.delete(agentId);
      }
      return next;
    });
  };

  const handleSelectAll = (checked: boolean) => {
    if (!checked) {
      setSelectedAgents(new Set());
      return;
    }
    setSelectedAgents(new Set(agents.map((agent) => agent.id)));
  };

  const openEditDialog = (agent: AgentListItem) => {
    const primary = getPrimaryConfig(agent);
    const seed: Partial<LLMConfigFormValues> = primary
      ? {
          provider: primary.provider,
          model_name: primary.model_name,
          temperature: primary.temperature,
          max_tokens: primary.max_tokens ?? null,
          api_key: undefined,
          fallback_provider: primary.fallback_provider ?? null,
          fallback_model: primary.fallback_model ?? null,
        }
      : {
          provider: agent.llm_provider,
          model_name: agent.llm_model,
          temperature: agent.temperature,
          max_tokens: agent.max_tokens ?? null,
        };

    setEditAgent(agent);
    setEditErrors({});
    setEditForm(buildDefaultForm(providers, seed));
  };

  const closeEditDialog = () => {
    setEditAgent(null);
    setEditForm(null);
    setEditErrors({});
  };

  const applyBulkConfig = async (scope: "selected" | "all") => {
    const targets = scope === "selected"
      ? agents.filter((agent) => selectedAgents.has(agent.id))
      : agents;

    if (targets.length === 0) {
      showToast({
        type: "warning",
        title: "No agents selected",
        description: scope === "selected"
          ? "Select one or more agents to apply the configuration."
          : "No agents available to update.",
      });
      return;
    }

    const errors = validateLLMValues(bulkForm);
    setBulkErrors(errors);
    if (Object.keys(errors).length > 0) {
      showToast({
        type: "error",
        title: "Invalid configuration",
        description: "Fix the highlighted fields before applying the update.",
      });
      return;
    }

    const payload = {
      agent_ids: targets.map((agent) => agent.id),
      config: {
        provider: bulkForm.provider,
        model_name: bulkForm.model_name,
        temperature: bulkForm.temperature,
        max_tokens: bulkForm.max_tokens ?? undefined,
        fallback_provider: bulkForm.fallback_provider ?? undefined,
        fallback_model: bulkForm.fallback_model ?? undefined,
        api_key: bulkForm.api_key ?? undefined,
        enabled: true,
      },
    };

    try {
      setBulkSaving(true);
      await api.agents.bulkAssignLLMConfigs(payload);
      showToast({
        type: "success",
        title: "Bulk update queued",
        description: `${targets.length} agents updated successfully`,
      });
      const list = await loadAgents();
      await refreshUsage(list);
    } catch (error) {
      showToast({
        type: "error",
        title: "Bulk update failed",
        description: error instanceof APIError ? error.message : "Unable to apply configuration",
      });
    } finally {
      setBulkSaving(false);
    }
  };

  const submitEdit = async () => {
    if (!editAgent || !editForm) {
      return;
    }
    const errors = validateLLMValues(editForm);
    setEditErrors(errors);
    if (Object.keys(errors).length > 0) {
      showToast({
        type: "error",
        title: "Invalid configuration",
        description: "Fix the highlighted fields before saving.",
      });
      return;
    }

    const payload = {
      provider: editForm.provider,
      model_name: editForm.model_name,
      temperature: editForm.temperature,
      max_tokens: editForm.max_tokens ?? undefined,
      fallback_provider: editForm.fallback_provider ?? undefined,
      fallback_model: editForm.fallback_model ?? undefined,
      api_key: editForm.api_key ?? undefined,
      enabled: true,
    };

    try {
      setEditSaving(true);
      await api.agents.upsertLLMConfig(editAgent.id, payload);
      showToast({
        type: "success",
        title: "Configuration saved",
        description: `${editAgent.name} updated successfully`,
      });
      closeEditDialog();
      const list = await loadAgents();
      await refreshUsage(list);
    } catch (error) {
      showToast({
        type: "error",
        title: "Failed to save",
        description: error instanceof APIError ? error.message : "Unable to save configuration",
      });
    } finally {
      setEditSaving(false);
    }
  };

  const handleExport = (scope: "selected" | "all") => {
    const targets = scope === "selected"
      ? agents.filter((agent) => selectedAgents.has(agent.id))
      : agents;

    const exportPayload = targets
      .map((agent) => {
        const config = getPrimaryConfig(agent);
        if (!config) return null;
        return {
          agent_ids: [agent.id],
          config: {
            provider: config.provider,
            model_name: config.model_name,
            temperature: config.temperature,
            max_tokens: config.max_tokens,
            fallback_provider: config.fallback_provider,
            fallback_model: config.fallback_model,
          },
        };
      })
      .filter(Boolean);

    if (exportPayload.length === 0) {
      showToast({
        type: "warning",
        title: "Nothing to export",
        description: "Selected agents do not have any saved configuration.",
      });
      return;
    }

    const blob = new Blob([JSON.stringify(exportPayload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `llm-configs-${scope}-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    showToast({
      type: "success",
      title: "Export complete",
      description: `${exportPayload.length} configuration entries exported`,
    });
  };

  const fileInputRef = React.useRef<HTMLInputElement | null>(null);
  const [importing, setImporting] = React.useState(false);

  const handleImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setImporting(true);
      const text = await file.text();
      const parsed = JSON.parse(text);
      const entries = Array.isArray(parsed) ? parsed : [parsed];
      const validEntries = entries.filter((entry) => Array.isArray(entry.agent_ids) && entry.agent_ids.length > 0 && entry.config);
      if (validEntries.length === 0) {
        throw new Error("Invalid import format");
      }

      for (const entry of validEntries) {
        await api.agents.bulkAssignLLMConfigs(entry);
      }

      showToast({
        type: "success",
        title: "Import complete",
        description: `${validEntries.length} configuration batches applied`,
      });
      const list = await loadAgents();
      await refreshUsage(list);
    } catch (error) {
      console.error("Failed to import configs", error);
      showToast({
        type: "error",
        title: "Import failed",
        description:
          error instanceof Error ? error.message : "Unable to import configurations",
      });
    } finally {
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      setImporting(false);
    }
  };

  const handleProviderTest = async ({
    provider,
    apiKey,
    modelName,
  }: {
    provider: string;
    apiKey: string;
    modelName: string;
  }) => {
    if (!apiKey) {
      showToast({
        type: "warning",
        title: "API key required",
        description: "Provide a provider-specific key to run connectivity tests.",
      });
      return;
    }

    const markStatus = (state: ProviderHealthState, detail?: string) => {
      handleProviderStatusUpdate(provider, {
        state,
        detail,
        lastChecked: new Date().toISOString(),
      });
    };

    try {
      markStatus("degraded", "Testing connectivity...");
      const start = performance.now();
      const response = await api.llmProviders.validateKey({
        provider,
        api_key: apiKey,
        model_name: modelName,
      });
      const latency = performance.now() - start;
      handleProviderStatusUpdate(provider, {
        state: response.valid ? "healthy" : "error",
        detail: response.detail,
        lastChecked: new Date().toISOString(),
        latencyMs: latency,
      });
      showToast({
        type: response.valid ? "success" : "error",
        title: response.valid ? "Provider validated" : "Provider validation failed",
        description: response.detail ?? `${provider} responded in ${latency.toFixed(0)} ms`,
      });
    } catch (error) {
      handleProviderStatusUpdate(provider, {
        state: "error",
        detail: error instanceof APIError ? error.message : "Connectivity failed",
        lastChecked: new Date().toISOString(),
      });
      showToast({
        type: "error",
        title: "Connectivity check failed",
        description: error instanceof APIError ? error.message : "Unable to validate provider",
      });
    }
  };

  const selectedCount = selectedAgents.size;
  const agentsWithConfigs = agents.filter((agent) => getPrimaryConfig(agent));

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-heading font-semibold">LLM Configuration</h1>
          <p className="mt-2 max-w-2xl text-muted-foreground">
            Manage per-agent LLM allocations, provider credentials, and runtime performance.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-sm">
            <span
              className={cn(
                "h-2.5 w-2.5 rounded-full",
                realtimeConnected ? "bg-success animate-pulse" : "bg-muted-foreground",
              )}
            />
            <span className="text-muted-foreground">
              {realtimeConnected ? "Realtime updates" : "Realtime offline"}
            </span>
          </div>
          <Button variant="outline" onClick={() => loadAgents().then((list) => refreshUsage(list))}>
            {loadingAgents ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            Refresh
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Managed agents</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold text-foreground">{agents.length}</div>
            <p className="text-xs text-muted-foreground">{agentsWithConfigs.length} with explicit configs</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Providers</CardTitle>
            <Settings className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold text-foreground">{providers.length}</div>
            <p className="text-xs text-muted-foreground">Configured provider registries</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Selected agents</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold text-foreground">{selectedCount}</div>
            <p className="text-xs text-muted-foreground">Ready for bulk operations</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <CardTitle>Agent configurations</CardTitle>
              <CardDescription>
                Inspect and override per-agent LLM settings. Changes apply immediately to new runs.
              </CardDescription>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Badge variant="outline">Primary</Badge>
              <span>denotes active routing for each agent.</span>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loadingAgents ? (
            <div className="flex h-56 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">
                    <Checkbox
                      checked={selectAll}
                      aria-label="Select all agents"
                      onCheckedChange={(checked) => handleSelectAll(Boolean(checked))}
                    />
                  </TableHead>
                  <TableHead>Agent</TableHead>
                  <TableHead>Primary LLM</TableHead>
                  <TableHead>Temperature</TableHead>
                  <TableHead>Fallback</TableHead>
                  <TableHead>Override</TableHead>
                  <TableHead>Updated</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {agents.map((agent) => {
                  const primary = getPrimaryConfig(agent);
                  return (
                    <TableRow key={agent.id} className="align-middle">
                      <TableCell>
                        <Checkbox
                          checked={selectedAgents.has(agent.id)}
                          onCheckedChange={(checked) => handleToggleAgentSelection(agent.id, Boolean(checked))}
                          aria-label={`Select ${agent.name}`}
                        />
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-foreground">{agent.name}</span>
                            <Badge variant={agent.is_active ? "outline" : "destructive"} className="capitalize">
                              {agent.role}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground">ID #{agent.id}</p>
                        </div>
                      </TableCell>
                      <TableCell>
                        {primary ? (
                          <div className="space-y-1 text-sm">
                            <div className="flex flex-wrap items-center gap-2">
                              <Badge variant="outline">{primary.provider}</Badge>
                              <span>{primary.model_name}</span>
                            </div>
                            <p className="text-xs text-muted-foreground">
                              Cost: in {primary.cost_per_1k_input_tokens?.toFixed(4)} / out {primary.cost_per_1k_output_tokens?.toFixed(4)}
                            </p>
                          </div>
                        ) : (
                          <div className="space-y-1 text-sm">
                            <div>{agent.llm_provider}/{agent.llm_model}</div>
                            <p className="text-xs text-muted-foreground">Inherits global defaults</p>
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {(primary?.temperature ?? agent.temperature).toFixed(2)}
                        {primary?.max_tokens ?? agent.max_tokens ? (
                          <div className="text-xs">Max {(primary?.max_tokens ?? agent.max_tokens)?.toLocaleString()}</div>
                        ) : null}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {primary?.fallback_provider ? (
                          <div>
                            <span className="font-medium">{primary.fallback_provider}</span>
                            {primary.fallback_model && (
                              <span className="ml-1 text-xs">({primary.fallback_model})</span>
                            )}
                          </div>
                        ) : (
                          <span className="text-xs">None</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {primary?.has_api_key_override ? (
                          <Badge variant="outline">Override</Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">Inherit</span>
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {formatDate(primary?.updated_at ?? agent.updated_at)}
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openEditDialog(agent)}
                            aria-label={`Edit ${agent.name}`}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setTestAgent(agent)}
                            aria-label={`Test ${agent.name}`}
                          >
                            <Settings className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
                {agents.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={8} className="h-32 text-center text-sm text-muted-foreground">
                      No agents registered.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Bulk operations</CardTitle>
          <CardDescription>
            Apply consistent LLM settings across multiple agents. Leave API key blank to retain shared credentials.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {providers.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Provider metadata is required before bulk updates can be configured.
            </p>
          ) : (
            <LLMConfigForm
              value={bulkForm}
              onChange={(update) =>
                setBulkForm((prev) => ({
                  ...prev,
                  ...update,
                }))
              }
              providers={providers}
              errors={bulkErrors}
            />
          )}
        </CardContent>
        <CardFooter className="flex flex-wrap gap-2">
          <Button
            onClick={() => applyBulkConfig("selected")}
            disabled={bulkSaving || selectedAgents.size === 0}
          >
            {bulkSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Apply to selected
          </Button>
          <Button
            variant="outline"
            onClick={() => applyBulkConfig("all")}
            disabled={bulkSaving || agents.length === 0}
          >
            Apply to all
          </Button>
          <Button
            variant="outline"
            onClick={() => handleExport("selected")}
            disabled={selectedAgents.size === 0}
          >
            <Download className="mr-2 h-4 w-4" /> Export selected
          </Button>
          <Button
            variant="outline"
            onClick={() => handleExport("all")}
            disabled={agentsWithConfigs.length === 0}
          >
            <Download className="mr-2 h-4 w-4" /> Export all
          </Button>
          <Button
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
          >
            {importing ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Upload className="mr-2 h-4 w-4" />
            )}
            Import JSON
          </Button>
        </CardFooter>
      </Card>

      <input
        ref={fileInputRef}
        type="file"
        accept="application/json"
        className="hidden"
        onChange={handleImport}
      />

      <Card>
        <CardHeader>
          <CardTitle>Provider management</CardTitle>
          <CardDescription>
            Monitor provider health, available models, and validate credentials.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <LLMProviderGrid
            providers={providers}
            statusMap={providerStatuses}
            onTestConnection={handleProviderTest}
            isLoading={loadingProviders}
          />
          {providers.length === 0 && !loadingProviders && (
            <div className="flex items-center gap-2 rounded-md border border-border/60 bg-surface-muted/40 p-3 text-sm text-muted-foreground">
              <AlertCircle className="h-4 w-4" />
              <span>No providers detected. Ensure backend registry is loaded.</span>
            </div>
          )}
        </CardContent>
      </Card>

      <LLMUsageDashboard
        agents={agents.map(({ id, name, role }) => ({ id, name, role }))}
        summaries={usageSummaries}
        timeRange={timeRange}
        onTimeRangeChange={setTimeRange}
        isLoading={usageLoading}
        onRefresh={() => {
          void refreshUsage();
        }}
      />

      {editAgent && editForm && (
        <Dialog
          open
          onOpenChange={(open) => {
            if (!open) closeEditDialog();
          }}
        >
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Edit {editAgent.name}'s LLM configuration</DialogTitle>
              <DialogDescription>
                Overrides apply immediately to new agent actions.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <LLMConfigForm
                value={editForm}
                onChange={(update) =>
                  setEditForm((prev) => (prev ? { ...prev, ...update } : prev))
                }
                providers={providers}
                errors={editErrors}
              />
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={closeEditDialog} disabled={editSaving}>
                Cancel
              </Button>
              <Button onClick={submitEdit} disabled={editSaving}>
                {editSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Save changes
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {testAgent && (
        <AgentLLMTestDialog
          agentId={testAgent.id}
          agentName={testAgent.name}
          open={Boolean(testAgent)}
          onOpenChange={(open) => {
            if (!open) setTestAgent(null);
          }}
          providers={providers}
        />
      )}
    </div>
  );
}
