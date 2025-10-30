"use client";

import * as React from "react";
import { Loader2, Sparkles, Timer } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { formatCurrency, formatDate } from "@tradingagents/shared/utils/format";
import { api, APIError } from "@/lib/api/client";

import type { LLMConfigFormValues, LLMProviderSummary } from "./llm-config-form";

export interface AgentLLMConfig extends LLMConfigFormValues {
  id: number;
  agent_id: number;
  has_api_key_override: boolean;
  enabled: boolean;
  cost_per_1k_input_tokens: number;
  cost_per_1k_output_tokens: number;
  created_at: string;
  updated_at: string;
  top_p?: number | null;
}

interface AgentLLMTestDialogProps {
  agentId: number;
  agentName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  providers: LLMProviderSummary[];
}

interface TestResultSummary {
  valid: boolean;
  detail?: string | null;
  latencyMs: number;
  timestamp: string;
  provider: string;
  model: string;
  estimatedTokens: {
    prompt: number;
    completion: number;
    total: number;
  };
  estimatedCostUsd: number;
}

const DEFAULT_PROMPT = "Provide a 2 sentence market outlook for the S&P 500.";

export function AgentLLMTestDialog({
  agentId,
  agentName,
  open,
  onOpenChange,
  providers,
}: AgentLLMTestDialogProps) {
  const { showToast } = useToast();
  const [configs, setConfigs] = React.useState<AgentLLMConfig[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [loadingConfigs, setLoadingConfigs] = React.useState(false);
  const [selectedConfigId, setSelectedConfigId] = React.useState<number | null>(null);
  const [prompt, setPrompt] = React.useState(DEFAULT_PROMPT);
  const [result, setResult] = React.useState<TestResultSummary | null>(null);

  React.useEffect(() => {
    if (!open) return;
    const fetchConfigs = async () => {
      try {
        setLoadingConfigs(true);
        const response = await api.agents.listLLMConfigs(agentId);
        const configList = Array.isArray(response) ? response : response?.configs ?? [];
        setConfigs(configList);
        setSelectedConfigId((prev) => {
          if (prev) return prev;
          return configList[0]?.id ?? null;
        });
      } catch (error) {
        showToast({
          type: "error",
          title: "Failed to load configurations",
          description: error instanceof APIError ? error.message : "Unable to load agent configs",
        });
      } finally {
        setLoadingConfigs(false);
      }
    };

    fetchConfigs();
  }, [agentId, open, showToast]);

  const selectedConfig = React.useMemo(
    () => configs.find((config) => config.id === selectedConfigId) ?? configs[0],
    [configs, selectedConfigId],
  );

  const providerLookup = React.useMemo(() => {
    const map = new Map<string, LLMProviderSummary>();
    providers.forEach((provider) => map.set(provider.provider, provider));
    return map;
  }, [providers]);

  const estimateTokens = React.useCallback((text: string) => {
    const clean = text.trim();
    if (!clean) return 0;
    return Math.max(1, Math.round(clean.length / 4));
  }, []);

  const runTest = async () => {
    if (!selectedConfig) return;
    try {
      setLoading(true);
      const start = performance.now();
      const response = await api.agents.testLLM(agentId, selectedConfig.id);
      const latency = performance.now() - start;
      const detail = response?.detail ?? (response?.valid ? "Connection validated successfully" : "Validation failed");

      const promptTokens = estimateTokens(prompt);
      const completionTokens = Math.max(1, Math.round(promptTokens * 0.5));
      const totalTokens = promptTokens + completionTokens;

      const providerMeta = providerLookup.get(selectedConfig.provider);
      const modelMeta = providerMeta?.models.find((model) => model.name === selectedConfig.model_name);
      const costPer1kIn = selectedConfig.cost_per_1k_input_tokens ?? modelMeta?.cost_per_1k_input_tokens ?? 0;
      const costPer1kOut = selectedConfig.cost_per_1k_output_tokens ?? modelMeta?.cost_per_1k_output_tokens ?? 0;
      const estimatedCost = ((promptTokens / 1000) * costPer1kIn) + ((completionTokens / 1000) * costPer1kOut);

      setResult({
        valid: Boolean(response?.valid),
        detail,
        latencyMs: latency,
        timestamp: new Date().toISOString(),
        provider: selectedConfig.provider,
        model: selectedConfig.model_name,
        estimatedTokens: {
          prompt: promptTokens,
          completion: completionTokens,
          total: totalTokens,
        },
        estimatedCostUsd: estimatedCost,
      });

      showToast({
        type: response?.valid ? "success" : "error",
        title: response?.valid ? "LLM test passed" : "LLM test failed",
        description: detail,
      });
    } catch (error) {
      showToast({
        type: "error",
        title: "LLM test failed",
        description: error instanceof APIError ? error.message : "Unable to validate configuration",
      });
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    if (!open) {
      setPrompt(DEFAULT_PROMPT);
      setResult(null);
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Test LLM configuration</DialogTitle>
          <DialogDescription>
            Run a synthetic prompt against <span className="font-semibold text-foreground">{agentName}</span>'s active configuration.
          </DialogDescription>
        </DialogHeader>

        {loadingConfigs ? (
          <div className="flex h-56 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : configs.length === 0 ? (
          <div className="rounded-lg border border-border/60 bg-surface-muted/40 p-6 text-center text-sm text-muted-foreground">
            This agent does not have any LLM configuration yet.
          </div>
        ) : (
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-[2fr,1fr]">
              <div className="space-y-3">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Configuration</label>
                  <Select
                    value={selectedConfig?.id ? String(selectedConfig.id) : configs[0] ? String(configs[0].id) : ""}
                    onValueChange={(value) => setSelectedConfigId(Number(value))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select configuration" />
                    </SelectTrigger>
                    <SelectContent>
                      {configs.map((config) => (
                        <SelectItem key={config.id} value={String(config.id)}>
                          {config.provider}/{config.model_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Sample prompt</label>
                  <Textarea
                    rows={5}
                    value={prompt}
                    onChange={(event) => setPrompt(event.target.value)}
                    placeholder={DEFAULT_PROMPT}
                  />
                  <p className="text-xs text-muted-foreground">
                    Prompt not transmitted to provider during validation. Used to estimate token footprint.
                  </p>
                </div>
              </div>

              {selectedConfig && (
                <Card className="self-start border-border/60 bg-surface-muted/40">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-semibold">Configuration details</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline">{selectedConfig.provider}</Badge>
                      <Badge variant="outline">{selectedConfig.model_name}</Badge>
                      {selectedConfig.fallback_provider && (
                        <Badge variant="muted">
                          Fallback: {selectedConfig.fallback_provider}/{selectedConfig.fallback_model ?? "auto"}
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Updated {formatDate(selectedConfig.updated_at)} • Temp {selectedConfig.temperature.toFixed(2)}
                    </p>
                    {selectedConfig.max_tokens && (
                      <p className="text-xs text-muted-foreground">
                        Max tokens: {selectedConfig.max_tokens.toLocaleString()}
                      </p>
                    )}
                    {selectedConfig.has_api_key_override && (
                      <p className="text-xs text-muted-foreground">
                        API key override stored
                      </p>
                    )}
                  </CardContent>
                </Card>
              )}
            </div>

            {result && (
              <Card className="border-border/60 bg-surface/70">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Sparkles className={result.valid ? "text-success" : "text-destructive"} />
                    Test results
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div className="flex flex-wrap items-center gap-3">
                    <Badge variant={result.valid ? "outline" : "destructive"}>
                      {result.valid ? "Validation success" : "Validation failed"}
                    </Badge>
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Timer className="h-4 w-4" /> {result.latencyMs.toFixed(0)} ms
                    </div>
                    <span className="text-muted-foreground">
                      {formatDate(result.timestamp)}
                    </span>
                  </div>
                  <p>{result.detail}</p>
                  <div className="grid gap-2 md:grid-cols-2">
                    <Metric
                      label="Estimated tokens"
                      value={`${result.estimatedTokens.total.toLocaleString()} (prompt ${result.estimatedTokens.prompt.toLocaleString()} / completion ${result.estimatedTokens.completion.toLocaleString()})`}
                    />
                    <Metric
                      label="Estimated cost"
                      value={formatCurrency(result.estimatedCostUsd)}
                    />
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <Button onClick={runTest} disabled={loading || loadingConfigs || !selectedConfig}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Run test
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border/60 bg-surface-muted/40 p-3 text-sm">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="font-semibold text-foreground">{value}</p>
    </div>
  );
}
