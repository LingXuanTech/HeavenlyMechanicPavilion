"use client";

import * as React from "react";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export interface LLMModelInfo {
  name: string;
  context_window: number;
  cost_per_1k_input_tokens: number;
  cost_per_1k_output_tokens: number;
  supports_streaming: boolean;
  supports_function_calling: boolean;
  supports_vision: boolean;
  max_output_tokens?: number | null;
}

export interface LLMProviderSummary {
  provider: string;
  display_name: string;
  models: LLMModelInfo[];
}

export interface LLMConfigFormValues {
  provider: string;
  model_name: string;
  temperature: number;
  max_tokens?: number | null;
  api_key?: string;
  fallback_provider?: string | null;
  fallback_model?: string | null;
}

export interface LLMConfigFormErrors {
  provider?: string;
  model_name?: string;
  temperature?: string;
  max_tokens?: string;
  api_key?: string;
  fallback_provider?: string;
  fallback_model?: string;
}

interface LLMConfigFormProps {
  value: LLMConfigFormValues;
  onChange: (update: Partial<LLMConfigFormValues>) => void;
  providers: LLMProviderSummary[];
  disabled?: boolean;
  errors?: LLMConfigFormErrors;
  hideApiKey?: boolean;
  hideFallback?: boolean;
  className?: string;
}

function formatCost(value: number) {
  return `$${value.toFixed(value < 0.001 ? 5 : 4)}`;
}

export function LLMConfigForm({
  value,
  onChange,
  providers,
  disabled = false,
  errors,
  hideApiKey = false,
  hideFallback = false,
  className,
}: LLMConfigFormProps) {
  const selectedProvider = React.useMemo(
    () => providers.find((provider) => provider.provider === value.provider),
    [providers, value.provider],
  );

  const fallbackProvider = React.useMemo(
    () => providers.find((provider) => provider.provider === value.fallback_provider),
    [providers, value.fallback_provider],
  );

  const availableModels = selectedProvider?.models ?? [];
  const availableFallbackModels = fallbackProvider?.models ?? [];

  React.useEffect(() => {
    if (!selectedProvider || availableModels.length === 0) {
      return;
    }

    const hasModel = availableModels.some((model) => model.name === value.model_name);
    if (!hasModel) {
      onChange({ model_name: availableModels[0].name });
    }
  }, [availableModels, onChange, selectedProvider, value.model_name]);

  const temperature = Number.isFinite(value.temperature) ? value.temperature : 0.7;

  const selectedModel = React.useMemo(
    () => availableModels.find((model) => model.name === value.model_name),
    [availableModels, value.model_name],
  );

  return (
    <div className={cn("grid gap-6", className)}>
      <div className="grid gap-3 md:grid-cols-2">
        <div className="space-y-2">
          <Label>Provider</Label>
          <Select
            disabled={disabled}
            value={value.provider || ""}
            onValueChange={(provider) => {
              onChange({ provider, model_name: "" });
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select provider" />
            </SelectTrigger>
            <SelectContent>
              {providers.map((provider) => (
                <SelectItem key={provider.provider} value={provider.provider}>
                  {provider.display_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {errors?.provider && (
            <p className="text-sm text-destructive">{errors.provider}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label>Model</Label>
          <Select
            disabled={disabled || !selectedProvider || availableModels.length === 0}
            value={value.model_name || ""}
            onValueChange={(model_name) => onChange({ model_name })}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select model" />
            </SelectTrigger>
            <SelectContent>
              {availableModels.length === 0 ? (
                <div className="p-3 text-sm text-muted-foreground">
                  Select a provider first
                </div>
              ) : (
                availableModels.map((model) => (
                  <SelectItem key={model.name} value={model.name}>
                    {model.name}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
          {errors?.model_name && (
            <p className="text-sm text-destructive">{errors.model_name}</p>
          )}
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="space-y-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <Label>Temperature</Label>
              <span className="text-muted-foreground">{temperature.toFixed(2)}</span>
            </div>
            <Slider
              disabled={disabled}
              min={0}
              max={2}
              step={0.01}
              value={[temperature]}
              onValueChange={(vals) => onChange({ temperature: Number(vals[0].toFixed(2)) })}
            />
            {errors?.temperature && (
              <p className="text-sm text-destructive">{errors.temperature}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="max-tokens">Max tokens</Label>
            <Input
              id="max-tokens"
              type="number"
              min={1}
              placeholder="e.g. 4096"
              disabled={disabled}
              value={value.max_tokens ?? ""}
              onChange={(event) => {
                const parsed = Number(event.target.value);
                onChange({ max_tokens: event.target.value ? Math.max(1, parsed) : null });
              }}
            />
            {errors?.max_tokens && (
              <p className="text-sm text-destructive">{errors.max_tokens}</p>
            )}
          </div>
        </div>

        {!hideApiKey && (
          <div className="space-y-2">
            <Label htmlFor="api-key">API key override (optional)</Label>
            <Input
              id="api-key"
              type="password"
              autoComplete="off"
              placeholder="Provide to override default credentials"
              disabled={disabled}
              value={value.api_key ?? ""}
              onChange={(event) => onChange({ api_key: event.target.value || undefined })}
            />
            <p className="text-xs text-muted-foreground">
              Stored securely. Leave blank to inherit environment configuration.
            </p>
            {errors?.api_key && (
              <p className="text-sm text-destructive">{errors.api_key}</p>
            )}
          </div>
        )}
      </div>

      {!hideFallback && (
        <div className="grid gap-3 md:grid-cols-2">
          <div className="space-y-2">
            <Label>Fallback provider</Label>
            <Select
              disabled={disabled}
              value={value.fallback_provider ?? "none"}
              onValueChange={(fallback) => {
                if (fallback === "none") {
                  onChange({ fallback_provider: null, fallback_model: null });
                  return;
                }
                onChange({ fallback_provider: fallback, fallback_model: null });
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select fallback provider" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">None</SelectItem>
                {providers
                  .filter((provider) => provider.provider !== value.provider)
                  .map((provider) => (
                    <SelectItem key={provider.provider} value={provider.provider}>
                      {provider.display_name}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
            {errors?.fallback_provider && (
              <p className="text-sm text-destructive">{errors.fallback_provider}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label>Fallback model</Label>
            <Select
              disabled={
                disabled || !value.fallback_provider || availableFallbackModels.length === 0
              }
              value={value.fallback_model ?? ""}
              onValueChange={(fallback_model) => onChange({ fallback_model })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select fallback model" />
              </SelectTrigger>
              <SelectContent>
                {value.fallback_provider ? (
                  availableFallbackModels.map((model) => (
                    <SelectItem key={model.name} value={model.name}>
                      {model.name}
                    </SelectItem>
                  ))
                ) : (
                  <div className="p-3 text-sm text-muted-foreground">
                    Select a fallback provider first
                  </div>
                )}
              </SelectContent>
            </Select>
            {errors?.fallback_model && (
              <p className="text-sm text-destructive">{errors.fallback_model}</p>
            )}
          </div>
        </div>
      )}

      {selectedModel && (
        <div className="rounded-lg border border-border/60 bg-surface-muted/40 p-4 text-sm">
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant="outline">Context: {selectedModel.context_window.toLocaleString()} tokens</Badge>
            {selectedModel.max_output_tokens && (
              <Badge variant="outline">
                Output max: {selectedModel.max_output_tokens.toLocaleString()} tokens
              </Badge>
            )}
            <Badge variant="outline">
              Cost in: {formatCost(selectedModel.cost_per_1k_input_tokens)}/1K tokens
            </Badge>
            <Badge variant="outline">
              Cost out: {formatCost(selectedModel.cost_per_1k_output_tokens)}/1K tokens
            </Badge>
            {selectedModel.supports_streaming && <Badge variant="muted">Streaming</Badge>}
            {selectedModel.supports_function_calling && (
              <Badge variant="muted">Functions</Badge>
            )}
            {selectedModel.supports_vision && <Badge variant="muted">Vision</Badge>}
          </div>
        </div>
      )}
    </div>
  );
}
