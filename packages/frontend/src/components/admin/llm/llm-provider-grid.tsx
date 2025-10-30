"use client";

import * as React from "react";
import { Loader2, ShieldAlert, ShieldCheck, ShieldQuestion } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

import type { LLMModelInfo, LLMProviderSummary } from "./llm-config-form";

export type ProviderHealthState = "unknown" | "healthy" | "degraded" | "error";

export interface ProviderStatusRecord {
  state: ProviderHealthState;
  detail?: string | null;
  lastChecked?: string;
  latencyMs?: number;
}

interface LLMProviderGridProps {
  providers: LLMProviderSummary[];
  statusMap: Record<string, ProviderStatusRecord | undefined>;
  onTestConnection: (args: {
    provider: string;
    apiKey: string;
    modelName: string;
  }) => Promise<void>;
  isLoading?: boolean;
}

function StatusIndicator({ state }: { state: ProviderHealthState }) {
  switch (state) {
    case "healthy":
      return <ShieldCheck className="h-4 w-4 text-success" />;
    case "degraded":
      return <ShieldAlert className="h-4 w-4 text-warning" />;
    case "error":
      return <ShieldAlert className="h-4 w-4 text-destructive" />;
    default:
      return <ShieldQuestion className="h-4 w-4 text-muted-foreground" />;
  }
}

const STATUS_LABELS: Record<ProviderHealthState, string> = {
  unknown: "Unknown",
  healthy: "Healthy",
  degraded: "Degraded",
  error: "Error",
};

function formatCost(value: number) {
  return `$${value.toFixed(value < 0.001 ? 5 : 4)}`;
}

function summarizeModel(model: LLMModelInfo) {
  return `${model.context_window.toLocaleString()} ctx • ${formatCost(model.cost_per_1k_input_tokens)}/1K in • ${formatCost(model.cost_per_1k_output_tokens)}/1K out`;
}

export function LLMProviderGrid({ providers, statusMap, onTestConnection, isLoading }: LLMProviderGridProps) {
  const [apiKeys, setApiKeys] = React.useState<Record<string, string>>({});
  const [selectedModels, setSelectedModels] = React.useState<Record<string, string>>({});
  const [testingProvider, setTestingProvider] = React.useState<string | null>(null);

  const handleTest = async (provider: LLMProviderSummary) => {
    const apiKey = apiKeys[provider.provider]?.trim() ?? "";
    const models = provider.models;
    if (!models.length) {
      return;
    }
    const modelName = selectedModels[provider.provider] ?? models[0].name;
    try {
      setTestingProvider(provider.provider);
      await onTestConnection({ provider: provider.provider, apiKey, modelName });
    } finally {
      setTestingProvider(null);
    }
  };

  const hasProviders = providers.length > 0;

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {!hasProviders && !isLoading && (
        <Card className="md:col-span-2 xl:col-span-3">
          <CardContent className="py-10 text-center text-muted-foreground">
            No providers discovered.
          </CardContent>
        </Card>
      )}

      {providers.map((provider) => {
        const status = statusMap[provider.provider] ?? { state: "unknown" as const };
        const isTesting = testingProvider === provider.provider;
        const models = provider.models;
        const selectedModel = selectedModels[provider.provider] ?? models[0]?.name;

        return (
          <Card key={provider.provider} className="flex flex-col border-border/80 bg-surface/70">
            <CardHeader>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    {provider.display_name}
                    <Badge variant="outline">{provider.provider}</Badge>
                  </CardTitle>
                  <CardDescription>
                    {models.length} model{models.length === 1 ? "" : "s"} available
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <StatusIndicator state={status.state} />
                  <span
                    className={cn(
                      "font-medium",
                      status.state === "healthy" && "text-success",
                      status.state === "degraded" && "text-warning",
                      status.state === "error" && "text-destructive",
                      status.state === "unknown" && "text-muted-foreground",
                    )}
                  >
                    {STATUS_LABELS[status.state]}
                  </span>
                </div>
              </div>
            </CardHeader>

            <CardContent className="flex flex-1 flex-col gap-4">
              <div className="space-y-2">
                <LabelledField label="Model">
                  <Select
                    disabled={isTesting || !models.length}
                    value={selectedModel}
                    onValueChange={(modelName) =>
                      setSelectedModels((prev) => ({ ...prev, [provider.provider]: modelName }))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select model" />
                    </SelectTrigger>
                    <SelectContent>
                      {models.map((model) => (
                        <SelectItem key={model.name} value={model.name}>
                          {model.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </LabelledField>

                <LabelledField label="API Key">
                  <Input
                    type="password"
                    autoComplete="off"
                    placeholder="Override key for validation"
                    value={apiKeys[provider.provider] ?? ""}
                    disabled={isTesting}
                    onChange={(event) =>
                      setApiKeys((prev) => ({ ...prev, [provider.provider]: event.target.value }))
                    }
                  />
                </LabelledField>

                <Button onClick={() => handleTest(provider)} disabled={isTesting || !models.length}>
                  {isTesting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Testing
                    </>
                  ) : (
                    "Test connection"
                  )}
                </Button>

                {status.detail && (
                  <p
                    className={cn(
                      "text-sm",
                      status.state === "healthy"
                        ? "text-success"
                        : status.state === "error"
                          ? "text-destructive"
                          : "text-muted-foreground",
                    )}
                  >
                    {status.detail}
                  </p>
                )}

                {status.latencyMs !== undefined && (
                  <p className="text-xs text-muted-foreground">
                    Latency: {status.latencyMs.toFixed(0)} ms
                  </p>
                )}
                {status.lastChecked && (
                  <p className="text-xs text-muted-foreground">
                    Last check: {new Date(status.lastChecked).toLocaleString()}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-foreground">Available models</h4>
                <ScrollArea className="max-h-40 rounded-md border border-border/60">
                  <div className="space-y-2 p-3">
                    {models.map((model) => (
                      <div key={model.name} className="space-y-1 rounded-md border border-border/40 bg-surface-muted/40 p-2">
                        <div className="flex items-center justify-between gap-2 text-sm font-medium">
                          <span>{model.name}</span>
                          {model.supports_streaming && <Badge variant="muted">Streaming</Badge>}
                        </div>
                        <p className="text-xs text-muted-foreground">{summarizeModel(model)}</p>
                        <div className="flex flex-wrap gap-1 text-[11px] text-muted-foreground">
                          {model.supports_function_calling && <Badge variant="outline">Functions</Badge>}
                          {model.supports_vision && <Badge variant="outline">Vision</Badge>}
                          {model.max_output_tokens && (
                            <Badge variant="outline">
                              Output max {model.max_output_tokens.toLocaleString()}
                            </Badge>
                          )}
                        </div>
                      </div>
                    ))}
                    {models.length === 0 && (
                      <p className="text-sm text-muted-foreground">No models registered</p>
                    )}
                  </div>
                </ScrollArea>
              </div>
            </CardContent>
          </Card>
        );
      })}

      {isLoading && (
        <Card className="md:col-span-2 xl:col-span-3">
          <CardContent className="flex items-center justify-center gap-2 py-10 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading providers
          </CardContent>
        </Card>
      )}
    </div>
  );
}

interface LabelledFieldProps {
  label: string;
  children: React.ReactNode;
}

function LabelledField({ label, children }: LabelledFieldProps) {
  return (
    <div className="space-y-1">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      {children}
    </div>
  );
}
