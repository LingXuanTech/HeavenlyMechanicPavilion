"use client";

import * as React from "react";
import { Edit, Loader2, Save } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Slider } from "@/components/ui/slider";
import { api, APIError } from "@/lib/api/client";
import { useToast } from "@/components/ui/toast";

interface Agent {
  id: number;
  name: string;
  role: string;
}

interface AgentLLMConfig {
  id: number;
  agent_id: number;
  provider: string;
  model_name: string;
  temperature: number;
  max_tokens: number | null;
  top_p: number | null;
  fallback_provider: string | null;
  fallback_model: string | null;
  enabled: boolean;
  has_api_key_override: boolean;
  cost_per_1k_input_tokens: number;
  cost_per_1k_output_tokens: number;
  created_at: string;
  updated_at: string;
  metadata: Record<string, any> | null;
}

interface AgentLLMConfigWithAgent extends AgentLLMConfig {
  agent_name?: string;
  agent_role?: string;
}

interface LLMConfigFormData {
  provider: string;
  model_name: string;
  temperature: number;
  max_tokens: number | null;
}

const OPENAI_MODELS = [
  { value: "gpt-4", label: "GPT-4" },
  { value: "gpt-4-turbo", label: "GPT-4 Turbo" },
  { value: "gpt-3.5-turbo", label: "GPT-3.5 Turbo" },
];

export default function AgentLLMConfigPage() {
  const [configs, setConfigs] = React.useState<AgentLLMConfigWithAgent[]>([]);
  const [agents, setAgents] = React.useState<Agent[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [editConfig, setEditConfig] = React.useState<AgentLLMConfigWithAgent | null>(null);
  const [editDialogOpen, setEditDialogOpen] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [formData, setFormData] = React.useState<LLMConfigFormData>({
    provider: "openai",
    model_name: "gpt-4",
    temperature: 0.7,
    max_tokens: 2000,
  });
  const { showToast } = useToast();

  const loadData = React.useCallback(async () => {
    try {
      setLoading(true);
      const [configsResponse, agentsResponse] = await Promise.all([
        api.agents.listLLMConfigs({ limit: 1000 }),
        api.agents.list({ limit: 1000 }),
      ]);
      
      const agentsList = agentsResponse?.agents || [];
      const configsList = configsResponse || [];
      
      const configsWithAgentInfo = configsList.map((config: AgentLLMConfig) => {
        const agent = agentsList.find((a: Agent) => a.id === config.agent_id);
        return {
          ...config,
          agent_name: agent?.name || `Agent ${config.agent_id}`,
          agent_role: agent?.role || "unknown",
        };
      });

      setAgents(agentsList);
      setConfigs(configsWithAgentInfo);
    } catch (error) {
      showToast({
        type: "error",
        title: "Failed to load data",
        description: error instanceof APIError ? error.message : "An error occurred",
      });
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  React.useEffect(() => {
    loadData();
  }, [loadData]);

  const handleEdit = (config: AgentLLMConfigWithAgent) => {
    setEditConfig(config);
    setFormData({
      provider: config.provider,
      model_name: config.model_name,
      temperature: config.temperature,
      max_tokens: config.max_tokens,
    });
    setEditDialogOpen(true);
  };

  const handleSave = async () => {
    if (!editConfig) return;

    try {
      setSaving(true);
      await api.agents.updateLLMConfig(editConfig.agent_id, formData);
      
      showToast({
        type: "success",
        title: "Configuration updated",
        description: `LLM config for ${editConfig.agent_name} has been updated`,
      });
      
      setEditDialogOpen(false);
      await loadData();
    } catch (error) {
      showToast({
        type: "error",
        title: "Failed to update configuration",
        description: error instanceof APIError ? error.message : "An error occurred",
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-heading font-semibold">Agent LLM Configuration</h1>
          <p className="mt-2 text-muted-foreground">
            Manage LLM settings for each agent
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>LLM Configurations</CardTitle>
          <CardDescription>
            {configs.length} agent{configs.length !== 1 ? "s" : ""} configured · {configs.filter((c) => c.enabled).length} enabled
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Agent</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Provider</TableHead>
                <TableHead>Model</TableHead>
                <TableHead>Temperature</TableHead>
                <TableHead>Max Tokens</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {configs.map((config) => (
                <TableRow key={config.id}>
                  <TableCell>
                    <p className="font-medium">{config.agent_name}</p>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{config.agent_role}</Badge>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">{config.provider}</span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm font-mono">{config.model_name}</span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">{config.temperature.toFixed(1)}</span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">{config.max_tokens || "N/A"}</span>
                  </TableCell>
                  <TableCell>
                    {config.enabled ? (
                      <Badge variant="default" className="bg-green-500">Enabled</Badge>
                    ) : (
                      <Badge variant="secondary">Disabled</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEdit(config)}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {configs.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground">
                    No configurations found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {editConfig && (
        <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>Edit LLM Configuration</DialogTitle>
              <DialogDescription>
                Update LLM settings for {editConfig.agent_name}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="model">Model</Label>
                <Select
                  value={formData.model_name}
                  onValueChange={(value) =>
                    setFormData((prev) => ({ ...prev, model_name: value }))
                  }
                >
                  <SelectTrigger id="model">
                    <SelectValue placeholder="Select a model" />
                  </SelectTrigger>
                  <SelectContent>
                    {OPENAI_MODELS.map((model) => (
                      <SelectItem key={model.value} value={model.value}>
                        {model.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="temperature">Temperature</Label>
                  <span className="text-sm text-muted-foreground">
                    {formData.temperature.toFixed(1)}
                  </span>
                </div>
                <Slider
                  id="temperature"
                  min={0}
                  max={2}
                  step={0.1}
                  value={[formData.temperature]}
                  onValueChange={(value) =>
                    setFormData((prev) => ({ ...prev, temperature: value[0] }))
                  }
                />
                <p className="text-xs text-muted-foreground">
                  Lower values make output more focused, higher values more creative
                </p>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="max_tokens">Max Tokens</Label>
                <Input
                  id="max_tokens"
                  type="number"
                  min={100}
                  max={8000}
                  value={formData.max_tokens || ""}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      max_tokens: e.target.value ? parseInt(e.target.value) : null,
                    }))
                  }
                  placeholder="e.g., 2000"
                />
                <p className="text-xs text-muted-foreground">
                  Maximum number of tokens to generate (100-8000)
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setEditDialogOpen(false)}
                disabled={saving}
              >
                Cancel
              </Button>
              <Button onClick={handleSave} disabled={saving}>
                {saving ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="mr-2 h-4 w-4" />
                    Save Changes
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
