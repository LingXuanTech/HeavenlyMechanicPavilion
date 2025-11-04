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

interface LLMConfig {
  provider: string;
  model: string;
  temperature?: number;
  max_tokens?: number;
  base_url?: string;
  api_key_env?: string;
}

interface Agent {
  id: number;
  name: string;
  role: string;
  llm_config: Record<string, unknown>;
  is_active: boolean;
}

type LLMConfigFormData = LLMConfig;

const OPENAI_MODELS = [
  { value: "gpt-4", label: "GPT-4" },
  { value: "gpt-4-turbo", label: "GPT-4 Turbo" },
  { value: "gpt-3.5-turbo", label: "GPT-3.5 Turbo" },
];

export default function AgentLLMConfigPage() {
  const [agents, setAgents] = React.useState<Agent[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [editingAgent, setEditingAgent] = React.useState<Agent | null>(null);
  const [editDialogOpen, setEditDialogOpen] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [formData, setFormData] = React.useState<LLMConfigFormData>({
    provider: "openai",
    model: "gpt-4o-mini",
    temperature: 0.7,
  });
  const { showToast } = useToast();

  const loadData = React.useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.agents.list({ limit: 1000 });
      setAgents(response.agents || []);
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

  const handleEdit = (agent: Agent) => {
    setEditingAgent(agent);
    setFormData(agent.llm_config as unknown as LLMConfig);
    setEditDialogOpen(true);
  };

  const handleSave = async () => {
    if (!editingAgent) return;

    try {
      setSaving(true);
      await api.agents.update(editingAgent.id, { llm_config: formData as unknown as Record<string, unknown> });
      
      showToast({
        type: "success",
        title: "Configuration updated",
        description: `LLM config for ${editingAgent.name} has been updated`,
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
            {agents.length} agent{agents.length !== 1 ? "s" : ""} configured · {agents.filter((a) => a.is_active).length} active
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
              {agents.map((agent) => (
                <TableRow key={agent.id}>
                  <TableCell>
                    <p className="font-medium">{agent.name}</p>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{agent.role}</Badge>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">{(agent.llm_config as unknown as LLMConfig).provider}</span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm font-mono">{(agent.llm_config as unknown as LLMConfig).model}</span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">{((agent.llm_config as unknown as LLMConfig).temperature ?? 0).toFixed(1)}</span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">{(agent.llm_config as unknown as LLMConfig).max_tokens || "N/A"}</span>
                  </TableCell>
                  <TableCell>
                    {agent.is_active ? (
                      <Badge variant="default" className="bg-green-500">Active</Badge>
                    ) : (
                      <Badge variant="secondary">Inactive</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEdit(agent)}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {agents.length === 0 && (
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

      {editingAgent && (
        <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>Edit LLM Configuration</DialogTitle>
              <DialogDescription>
                Update LLM settings for {editingAgent.name}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="model">Model</Label>
                <Select
                  value={formData.model}
                  onValueChange={(value) =>
                    setFormData((prev) => ({ ...prev, model: value }))
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
                    {(formData.temperature ?? 0).toFixed(1)}
                  </span>
                </div>
                <Slider
                  id="temperature"
                  min={0}
                  max={2}
                  step={0.1}
                  value={[formData.temperature ?? 0.7]}
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
                  max={16000}
                  value={formData.max_tokens || ""}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      max_tokens: e.target.value ? parseInt(e.target.value) : undefined,
                    }))
                  }
                  placeholder="e.g., 2000"
                />
                <p className="text-xs text-muted-foreground">
                  Maximum number of tokens to generate (100-16000)
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
