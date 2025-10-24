"use client";

import * as React from "react";
import {
  Plus,
  Edit,
  Trash2,
  Loader2,
  Save,
  RefreshCw,
} from "lucide-react";
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
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
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
import { api, APIError } from "@/lib/api/client";
import { useToast } from "@/components/ui/toast";
import { formatDate } from "@tradingagents/shared/utils/format";

interface Agent {
  id: number;
  name: string;
  agent_type: string;
  role: string;
  description: string | null;
  llm_provider: string;
  llm_model: string;
  llm_type: string;
  temperature: number;
  max_tokens: number | null;
  prompt_template: string | null;
  capabilities: string[];
  required_tools: string[];
  requires_memory: boolean;
  memory_name: string | null;
  is_reserved: boolean;
  slot_name: string | null;
  is_active: boolean;
  version: string;
  config: Record<string, any> | null;
  metadata: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

interface AgentFormData {
  name: string;
  agent_type: string;
  role: string;
  description: string;
  llm_provider: string;
  llm_model: string;
  llm_type: string;
  temperature: number;
  max_tokens: number | null;
  prompt_template: string;
  capabilities: string[];
  required_tools: string[];
  requires_memory: boolean;
  memory_name: string;
  slot_name: string;
  is_active: boolean;
  version: string;
}

interface AuditLogEntry {
  id: string;
  timestamp: string;
  action: string;
  details: string;
  actor: string;
}

const AGENT_ROLES = [
  "analyst",
  "researcher",
  "trader",
  "risk_manager",
  "portfolio_manager",
  "data_engineer",
  "custom",
];

const LLM_PROVIDERS = ["openai", "anthropic", "google", "local"];
const LLM_TYPES = ["quick", "deep"];

export default function AgentMarketplacePage() {
  const [agents, setAgents] = React.useState<Agent[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [filterRole, setFilterRole] = React.useState<string | null>(null);
  const [filterActive, setFilterActive] = React.useState<boolean | null>(null);
  const [editAgent, setEditAgent] = React.useState<Agent | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = React.useState(false);
  const [editDialogOpen, setEditDialogOpen] = React.useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);
  const [agentToDelete, setAgentToDelete] = React.useState<Agent | null>(null);
  const [reloadLoading, setReloadLoading] = React.useState(false);
  const [auditLog, setAuditLog] = React.useState<AuditLogEntry[]>([]);
  const { showToast } = useToast();

  const addAuditEvent = React.useCallback((action: string, details: string) => {
    const entry: AuditLogEntry = {
      id: Math.random().toString(36).slice(2, 9),
      timestamp: new Date().toISOString(),
      action,
      details,
      actor: "Console",
    };
    setAuditLog((prev) => [entry, ...prev].slice(0, 25));
  }, []);

  const loadAgents = React.useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.agents.list({
        role: filterRole || undefined,
        is_active: filterActive ?? undefined,
      });
      setAgents(response?.agents || []);
    } catch (error) {
      showToast({
        type: "error",
        title: "Failed to load agents",
        description: error instanceof APIError ? error.message : "An error occurred",
      });
    } finally {
      setLoading(false);
    }
  }, [filterRole, filterActive, showToast]);

  React.useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  const handleToggleActive = async (agent: Agent) => {
    const originalAgents = agents;
    const optimisticUpdate = agents.map((a) =>
      a.id === agent.id ? { ...a, is_active: !a.is_active } : a
    );
    setAgents(optimisticUpdate);

    try {
      if (agent.is_active) {
        await api.agents.deactivate(agent.id);
        showToast({
          type: "success",
          title: "Agent deactivated",
          description: `${agent.name} has been deactivated`,
        });
        addAuditEvent("Agent deactivated", `${agent.name} marked inactive`);
      } else {
        await api.agents.activate(agent.id);
        showToast({
          type: "success",
          title: "Agent activated",
          description: `${agent.name} has been activated`,
        });
        addAuditEvent("Agent activated", `${agent.name} marked active`);
      }
      await loadAgents();
    } catch (error) {
      setAgents(originalAgents);
      showToast({
        type: "error",
        title: "Failed to toggle agent",
        description: error instanceof APIError ? error.message : "An error occurred",
      });
    }
  };

  const handleEdit = (agent: Agent) => {
    setEditAgent(agent);
    setEditDialogOpen(true);
  };

  const handleDeleteClick = (agent: Agent) => {
    setAgentToDelete(agent);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!agentToDelete) return;

    try {
      await api.agents.delete(agentToDelete.id);
      showToast({
        type: "success",
        title: "Agent deleted",
        description: `${agentToDelete.name} has been deleted`,
      });
      addAuditEvent("Agent deleted", `${agentToDelete.name} removed from marketplace`);
      await loadAgents();
      setDeleteDialogOpen(false);
      setAgentToDelete(null);
    } catch (error) {
      showToast({
        type: "error",
        title: "Failed to delete agent",
        description: error instanceof APIError ? error.message : "An error occurred",
      });
    }
  };

  const handleReloadRegistry = async () => {
    try {
      setReloadLoading(true);
      await api.agents.reload();
      showToast({
        type: "success",
        title: "Registry reloaded",
        description: "Agent registry refreshed",
      });
      addAuditEvent("Registry reloaded", "Hot reload triggered for agent registry");
      await loadAgents();
    } catch (error) {
      showToast({
        type: "error",
        title: "Failed to reload registry",
        description: error instanceof APIError ? error.message : "An error occurred",
      });
    } finally {
      setReloadLoading(false);
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
          <h1 className="text-3xl font-heading font-semibold">Agent Marketplace</h1>
          <p className="mt-2 text-muted-foreground">
            Manage agent plugins, prompts, tool bindings, and lifecycle status
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleReloadRegistry} disabled={reloadLoading}>
            {reloadLoading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            Reload Registry
          </Button>
          <Button onClick={() => setCreateDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Agent
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <CardTitle>Agent Inventory</CardTitle>
              <CardDescription>
                {agents.length} agents registered · {agents.filter((a) => a.is_active).length} active
              </CardDescription>
            </div>
            <div className="flex flex-wrap gap-2">
              <Select
                value={filterRole || "all"}
                onValueChange={(value) => setFilterRole(value === "all" ? null : value)}
              >
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Filter by role" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All roles</SelectItem>
                  {AGENT_ROLES.map((role) => (
                    <SelectItem key={role} value={role}>
                      {role}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select
                value={
                  filterActive === null ? "all" : filterActive ? "active" : "inactive"
                }
                onValueChange={(value) =>
                  setFilterActive(value === "all" ? null : value === "active")
                }
              >
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Filter by status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>LLM</TableHead>
                <TableHead>Capabilities</TableHead>
                <TableHead>Tools</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Version</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {agents.map((agent) => (
                <TableRow key={agent.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{agent.name}</p>
                      {agent.description && (
                        <p className="text-xs text-muted-foreground">
                          {agent.description}
                        </p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{agent.role}</Badge>
                    {agent.is_reserved && (
                      <Badge variant="muted" className="ml-2 text-xs">
                        Reserved
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-xs">
                    <div>{agent.llm_provider}/{agent.llm_model}</div>
                    <div className="text-muted-foreground">
                      {agent.llm_type} · T={agent.temperature}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {agent.capabilities.slice(0, 3).map((cap) => (
                        <Badge key={cap} variant="muted" className="text-xs">
                          {cap}
                        </Badge>
                      ))}
                      {agent.capabilities.length > 3 && (
                        <Badge variant="muted" className="text-xs">
                          +{agent.capabilities.length - 3}
                        </Badge>
                      )}
                      {agent.capabilities.length === 0 && (
                        <span className="text-xs text-muted-foreground">None</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {agent.required_tools.slice(0, 2).map((tool) => (
                        <Badge key={tool} variant="muted" className="text-xs">
                          {tool}
                        </Badge>
                      ))}
                      {agent.required_tools.length > 2 && (
                        <Badge variant="muted" className="text-xs">
                          +{agent.required_tools.length - 2}
                        </Badge>
                      )}
                      {agent.required_tools.length === 0 && (
                        <span className="text-xs text-muted-foreground">None</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Switch
                      checked={agent.is_active}
                      onCheckedChange={() => handleToggleActive(agent)}
                    />
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {agent.version}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEdit(agent)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      {!agent.is_reserved && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteClick(agent)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {agents.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground">
                    No agents found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Audit Log</CardTitle>
          <CardDescription>Recent administration activity (session scoped)</CardDescription>
        </CardHeader>
        <CardContent>
          {auditLog.length === 0 ? (
            <p className="text-sm text-muted-foreground">No audit entries yet.</p>
          ) : (
            <div className="space-y-3">
              {auditLog.map((entry) => (
                <div
                  key={entry.id}
                  className="rounded-lg border border-border/60 bg-surface-muted/40 p-3"
                >
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{entry.actor}</span>
                    <span>{formatDate(entry.timestamp)}</span>
                  </div>
                  <p className="mt-1 text-sm font-medium text-foreground">{entry.action}</p>
                  <p className="text-sm text-muted-foreground">{entry.details}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <CreateAgentDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSuccess={loadAgents}
        onAudit={addAuditEvent}
      />

      {editAgent && (
        <EditAgentDialog
          agent={editAgent}
          open={editDialogOpen}
          onOpenChange={setEditDialogOpen}
          onSuccess={loadAgents}
          onAudit={addAuditEvent}
        />
      )}

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogHeader>
          <DialogTitle>Delete Agent</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete {agentToDelete?.name}? This action cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={handleDeleteConfirm}>
            Delete
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  );
}

interface CreateAgentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  onAudit: (action: string, details: string) => void;
}

function CreateAgentDialog({ open, onOpenChange, onSuccess, onAudit }: CreateAgentDialogProps) {
  const initialState: AgentFormData = {
    name: "",
    agent_type: "custom",
    role: "custom",
    description: "",
    llm_provider: "openai",
    llm_model: "gpt-4o-mini",
    llm_type: "quick",
    temperature: 0.7,
    max_tokens: null,
    prompt_template: "",
    capabilities: [],
    required_tools: [],
    requires_memory: false,
    memory_name: "",
    slot_name: "",
    is_active: true,
    version: "1.0.0",
  };

  const [formData, setFormData] = React.useState<AgentFormData>(initialState);
  const [saving, setSaving] = React.useState(false);
  const { showToast } = useToast();

  const handleSave = async () => {
    if (!formData.name.trim()) {
      showToast({
        type: "error",
        title: "Validation error",
        description: "Agent name is required",
      });
      return;
    }

    try {
      setSaving(true);
      await api.agents.create(formData);
      showToast({
        type: "success",
        title: "Agent created",
        description: `${formData.name} has been created successfully`,
      });
      onAudit("Agent created", `${formData.name} registered with role ${formData.role}`);
      onSuccess();
      onOpenChange(false);
      setFormData(initialState);
    } catch (error) {
      showToast({
        type: "error",
        title: "Failed to create agent",
        description: error instanceof APIError ? error.message : "An error occurred",
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogHeader>
        <DialogTitle>Create New Agent</DialogTitle>
        <DialogDescription>
          Configure a new agent plugin with LLM settings, prompts, and tool bindings
        </DialogDescription>
      </DialogHeader>
      <DialogContent className="max-h-[70vh] overflow-y-auto">
        <AgentForm formData={formData} setFormData={setFormData} />
      </DialogContent>
      <DialogFooter>
        <Button variant="outline" onClick={() => onOpenChange(false)}>
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Creating...
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              Create Agent
            </>
          )}
        </Button>
      </DialogFooter>
    </Dialog>
  );
}

interface EditAgentDialogProps {
  agent: Agent;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  onAudit: (action: string, details: string) => void;
}

function EditAgentDialog({ agent, open, onOpenChange, onSuccess, onAudit }: EditAgentDialogProps) {
  const [formData, setFormData] = React.useState<AgentFormData>({
    name: agent.name,
    agent_type: agent.agent_type,
    role: agent.role,
    description: agent.description || "",
    llm_provider: agent.llm_provider,
    llm_model: agent.llm_model,
    llm_type: agent.llm_type,
    temperature: agent.temperature,
    max_tokens: agent.max_tokens,
    prompt_template: agent.prompt_template || "",
    capabilities: agent.capabilities || [],
    required_tools: agent.required_tools || [],
    requires_memory: agent.requires_memory,
    memory_name: agent.memory_name || "",
    slot_name: agent.slot_name || "",
    is_active: agent.is_active,
    version: agent.version,
  });
  const [saving, setSaving] = React.useState(false);
  const { showToast } = useToast();

  React.useEffect(() => {
    if (open) {
      setFormData({
        name: agent.name,
        agent_type: agent.agent_type,
        role: agent.role,
        description: agent.description || "",
        llm_provider: agent.llm_provider,
        llm_model: agent.llm_model,
        llm_type: agent.llm_type,
        temperature: agent.temperature,
        max_tokens: agent.max_tokens,
        prompt_template: agent.prompt_template || "",
        capabilities: agent.capabilities || [],
        required_tools: agent.required_tools || [],
        requires_memory: agent.requires_memory,
        memory_name: agent.memory_name || "",
        slot_name: agent.slot_name || "",
        is_active: agent.is_active,
        version: agent.version,
      });
    }
  }, [open, agent]);

  const handleSave = async () => {
    try {
      setSaving(true);
      const { name: _name, ...payload } = formData;
      await api.agents.update(agent.id, payload);
      showToast({
        type: "success",
        title: "Agent updated",
        description: `${agent.name} configuration saved`,
      });
      onAudit("Agent updated", `${agent.name} prompt/tool configuration refreshed`);
      onSuccess();
      onOpenChange(false);
    } catch (error) {
      showToast({
        type: "error",
        title: "Failed to update agent",
        description: error instanceof APIError ? error.message : "An error occurred",
      });
    } finally {
      setSaving(false);
    }
  };

  const metadata = agent.metadata || {};
  const recentOutputs: string[] = React.useMemo(() => {
    const outputs = metadata.recent_outputs || metadata.recentOutputs;
    return Array.isArray(outputs) ? outputs : [];
  }, [metadata]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogHeader>
        <DialogTitle>Edit {agent.name}</DialogTitle>
        <DialogDescription>
          Update agent prompts, tool bindings, and runtime posture
        </DialogDescription>
      </DialogHeader>
      <DialogContent className="max-h-[75vh] space-y-6 overflow-y-auto">
        <AgentForm formData={formData} setFormData={setFormData} isEdit />

        <div className="space-y-3 rounded-lg border border-border/60 bg-surface-muted/40 p-4">
          <h3 className="text-sm font-semibold">Recent Outputs</h3>
          {recentOutputs.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No recent outputs captured for this agent.
            </p>
          ) : (
            <div className="space-y-3">
              {recentOutputs.slice(0, 5).map((output, idx) => (
                <div key={idx} className="rounded-md bg-background/60 p-3 text-sm text-muted-foreground">
                  {output}
                </div>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
      <DialogFooter>
        <Button variant="outline" onClick={() => onOpenChange(false)}>
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
    </Dialog>
  );
}

interface AgentFormProps {
  formData: AgentFormData;
  setFormData: React.Dispatch<React.SetStateAction<AgentFormData>>;
  isEdit?: boolean;
}

function AgentForm({ formData, setFormData, isEdit = false }: AgentFormProps) {
  const handleChange = (field: keyof AgentFormData, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="name">Name *</Label>
          <Input
            id="name"
            value={formData.name}
            onChange={(e) => handleChange("name", e.target.value)}
            disabled={isEdit}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="agent_type">Agent Type *</Label>
          <Input
            id="agent_type"
            value={formData.agent_type}
            onChange={(e) => handleChange("agent_type", e.target.value)}
            placeholder="analyst, researcher, trader..."
          />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="role">Role *</Label>
          <Select
            value={formData.role}
            onValueChange={(value) => handleChange("role", value)}
          >
            <SelectTrigger id="role">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {AGENT_ROLES.map((role) => (
                <SelectItem key={role} value={role}>
                  {role}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="slot_name">Slot Name</Label>
          <Input
            id="slot_name"
            value={formData.slot_name}
            onChange={(e) => handleChange("slot_name", e.target.value)}
            placeholder="risk_manager_primary"
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Input
          id="description"
          value={formData.description}
          onChange={(e) => handleChange("description", e.target.value)}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="space-y-2">
          <Label htmlFor="llm_provider">LLM Provider</Label>
          <Select
            value={formData.llm_provider}
            onValueChange={(value) => handleChange("llm_provider", value)}
          >
            <SelectTrigger id="llm_provider">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LLM_PROVIDERS.map((provider) => (
                <SelectItem key={provider} value={provider}>
                  {provider}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="llm_model">LLM Model</Label>
          <Input
            id="llm_model"
            value={formData.llm_model}
            onChange={(e) => handleChange("llm_model", e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="llm_type">LLM Type</Label>
          <Select
            value={formData.llm_type}
            onValueChange={(value) => handleChange("llm_type", value)}
          >
            <SelectTrigger id="llm_type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LLM_TYPES.map((type) => (
                <SelectItem key={type} value={type}>
                  {type}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="temperature">Temperature</Label>
          <Input
            id="temperature"
            type="number"
            min="0"
            max="2"
            step="0.1"
            value={formData.temperature}
            onChange={(e) =>
              handleChange(
                "temperature",
                e.target.value === "" ? 0 : parseFloat(e.target.value)
              )
            }
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="max_tokens">Max Tokens</Label>
          <Input
            id="max_tokens"
            type="number"
            value={formData.max_tokens ?? ""}
            onChange={(e) =>
              handleChange(
                "max_tokens",
                e.target.value === "" ? null : parseInt(e.target.value, 10)
              )
            }
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="prompt_template">Prompt Template</Label>
        <Textarea
          id="prompt_template"
          rows={6}
          value={formData.prompt_template}
          onChange={(e) => handleChange("prompt_template", e.target.value)}
          placeholder="Enter the agent's system prompt template..."
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="capabilities">Capabilities (comma-separated)</Label>
          <Input
            id="capabilities"
            value={formData.capabilities.join(", ")}
            onChange={(e) =>
              handleChange(
                "capabilities",
                e.target.value
                  .split(",")
                  .map((cap) => cap.trim())
                  .filter(Boolean)
              )
            }
            placeholder="technical_analysis, macro_scout"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="required_tools">Tool Bindings (comma-separated)</Label>
          <Input
            id="required_tools"
            value={formData.required_tools.join(", ")}
            onChange={(e) =>
              handleChange(
                "required_tools",
                e.target.value
                  .split(",")
                  .map((tool) => tool.trim())
                  .filter(Boolean)
              )
            }
            placeholder="get_stock_price, get_news, analyze_sentiment"
          />
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <Switch
          id="requires_memory"
          checked={formData.requires_memory}
          onCheckedChange={(checked) => handleChange("requires_memory", checked)}
        />
        <Label htmlFor="requires_memory">Requires Memory</Label>
      </div>

      {formData.requires_memory && (
        <div className="space-y-2">
          <Label htmlFor="memory_name">Memory Name</Label>
          <Input
            id="memory_name"
            value={formData.memory_name}
            onChange={(e) => handleChange("memory_name", e.target.value)}
          />
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="version">Version</Label>
          <Input
            id="version"
            value={formData.version}
            onChange={(e) => handleChange("version", e.target.value)}
          />
        </div>
        <div className="flex items-center space-x-2">
          <Switch
            id="is_active"
            checked={formData.is_active}
            onCheckedChange={(checked) => handleChange("is_active", checked)}
          />
          <Label htmlFor="is_active">Active on save</Label>
        </div>
      </div>
    </div>
  );
}
