"use client";

import * as React from "react";
import {
  RefreshCw,
  Settings,
  Eye,
  EyeOff,
  Save,
  Loader2,
  Plus,
  ArrowUp,
  ArrowDown,
  X as Close,
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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

interface VendorPlugin {
  name: string;
  provider: string;
  description: string;
  version: string;
  priority: number;
  capabilities: string[];
  rate_limits: Record<string, number | null>;
  is_active: boolean;
}

interface RoutingConfig {
  [method: string]: string[];
}

interface ConfigReloadResponse {
  success: boolean;
  message: string;
  last_reload: string | null;
}

interface AuditLogEntry {
  id: string;
  action: string;
  details: string;
  actor: string;
  timestamp: string;
}

type FieldType = "string" | "number" | "boolean" | "object" | "array" | "null";

type FieldMeta = Record<string, FieldType>;
type FieldValues = Record<string, string>;

const SENSITIVE_KEYS = ["key", "secret", "token", "password"];

function inferFieldType(value: any): FieldType {
  if (value === null || value === undefined) return "null";
  if (Array.isArray(value)) return "array";
  switch (typeof value) {
    case "number":
      return "number";
    case "boolean":
      return "boolean";
    case "object":
      return "object";
    default:
      return "string";
  }
}

function stringifyValue(value: any): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") {
    try {
      return JSON.stringify(value, null, 2);
    } catch (error) {
      return String(value);
    }
  }
  return String(value);
}

function parseValue(value: string, type: FieldType): any {
  switch (type) {
    case "number": {
      const parsed = Number(value);
      return Number.isNaN(parsed) ? 0 : parsed;
    }
    case "boolean":
      return value === "true";
    case "array":
    case "object": {
      try {
        return JSON.parse(value);
      } catch (error) {
        return value;
      }
    }
    case "null":
      return value.trim() === "" ? null : value;
    default:
      return value;
  }
}

export default function VendorManagementPage() {
  const [vendors, setVendors] = React.useState<VendorPlugin[]>([]);
  const [routingConfig, setRoutingConfig] = React.useState<RoutingConfig>({});
  const [loading, setLoading] = React.useState(true);
  const [reloadLoading, setReloadLoading] = React.useState(false);
  const [lastReload, setLastReload] = React.useState<string | null>(null);
  const [selectedVendor, setSelectedVendor] = React.useState<VendorPlugin | null>(null);
  const [editDialogOpen, setEditDialogOpen] = React.useState(false);
  const [routingDialogOpen, setRoutingDialogOpen] = React.useState(false);
  const [selectedMethod, setSelectedMethod] = React.useState<string | null>(null);
  const [auditLog, setAuditLog] = React.useState<AuditLogEntry[]>([]);
  const { showToast } = useToast();

  const addAuditEvent = React.useCallback((action: string, details: string) => {
    const entry: AuditLogEntry = {
      id: Math.random().toString(36).slice(2, 9),
      actor: "Console",
      action,
      details,
      timestamp: new Date().toISOString(),
    };
    setAuditLog((prev) => [entry, ...prev].slice(0, 25));
  }, []);

  const loadData = React.useCallback(async () => {
    try {
      setLoading(true);
      const [vendorsResp, routingResp] = await Promise.all([
        api.vendors.list(),
        api.vendors.getRoutingConfig(),
      ]);
      setVendors(vendorsResp.plugins || []);
      setRoutingConfig(routingResp.routing || {});
    } catch (error) {
      showToast({
        type: "error",
        title: "Failed to load vendors",
        description: error instanceof APIError ? error.message : "An error occurred",
      });
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  React.useEffect(() => {
    loadData();
  }, [loadData]);

  const handleReloadConfig = async () => {
    try {
      setReloadLoading(true);
      const response: ConfigReloadResponse = await api.vendors.reloadConfig();
      setLastReload(response.last_reload);
      showToast({
        type: "success",
        title: "Config reloaded",
        description: response.message,
      });
      addAuditEvent("Vendor config reloaded", response.message);
      await loadData();
    } catch (error) {
      showToast({
        type: "error",
        title: "Failed to reload config",
        description: error instanceof APIError ? error.message : "An error occurred",
      });
    } finally {
      setReloadLoading(false);
    }
  };

  const handleEditVendor = (vendor: VendorPlugin) => {
    setSelectedVendor(vendor);
    setEditDialogOpen(true);
  };

  const handleEditRouting = (method: string) => {
    setSelectedMethod(method);
    setRoutingDialogOpen(true);
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
          <h1 className="text-3xl font-heading font-semibold">Vendor Management</h1>
          <p className="mt-2 text-muted-foreground">
            Configure data providers, fallback chains, and secure credentials
          </p>
        </div>
        <Button onClick={handleReloadConfig} disabled={reloadLoading}>
          {reloadLoading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          Reload Config
        </Button>
      </div>

      {lastReload && (
        <Card className="border-success/60 bg-success/10">
          <CardContent className="py-3 text-sm text-success">
            Last config reload: {formatDate(lastReload)}
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="vendors" className="space-y-6">
        <TabsList>
          <TabsTrigger value="vendors">Vendors</TabsTrigger>
          <TabsTrigger value="routing">Routing & Fallbacks</TabsTrigger>
        </TabsList>

        <TabsContent value="vendors" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Registered Vendors</CardTitle>
              <CardDescription>
                Manage plugin metadata, credentials, and execution priorities
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Provider</TableHead>
                    <TableHead>Priority</TableHead>
                    <TableHead>Capabilities</TableHead>
                    <TableHead>Version</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {vendors.map((vendor) => (
                    <TableRow key={vendor.name}>
                      <TableCell className="font-medium">{vendor.name}</TableCell>
                      <TableCell>{vendor.provider}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{vendor.priority}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {vendor.capabilities.slice(0, 3).map((cap) => (
                            <Badge key={cap} variant="muted" className="text-xs">
                              {cap}
                            </Badge>
                          ))}
                          {vendor.capabilities.length > 3 && (
                            <Badge variant="muted" className="text-xs">
                              +{vendor.capabilities.length - 3}
                            </Badge>
                          )}
                          {vendor.capabilities.length === 0 && (
                            <span className="text-xs text-muted-foreground">None</span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {vendor.version}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEditVendor(vendor)}
                        >
                          <Settings className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="routing" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Fallback Chains</CardTitle>
              <CardDescription>
                Order vendors by priority for each capability method. Highest priority executes first.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {Object.entries(routingConfig).length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No routing configuration discovered. Configure fallback chains per method to ensure continuity.
                </p>
              ) : (
                Object.entries(routingConfig).map(([method, vendorList]) => (
                  <div
                    key={method}
                    className="flex items-center justify-between rounded-lg border border-border/60 bg-surface-muted/40 p-4"
                  >
                    <div className="flex-1">
                      <h3 className="font-medium">{method}</h3>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {vendorList.length === 0 ? (
                          <span className="text-sm text-muted-foreground">No vendors configured</span>
                        ) : (
                          vendorList.map((vendor, index) => (
                            <Badge key={vendor} variant={index === 0 ? "default" : "outline"}>
                              {index + 1}. {vendor}
                            </Badge>
                          ))
                        )}
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEditRouting(method)}
                    >
                      <Settings className="h-4 w-4" />
                    </Button>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Card>
        <CardHeader>
          <CardTitle>Audit Log</CardTitle>
          <CardDescription>Recent configuration changes (session scoped)</CardDescription>
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

      {selectedVendor && (
        <VendorEditDialog
          vendor={selectedVendor}
          open={editDialogOpen}
          onOpenChange={setEditDialogOpen}
          onSuccess={() => {
            loadData();
            addAuditEvent(
              "Vendor config updated",
              `${selectedVendor.name} credentials/settings saved`
            );
          }}
        />
      )}

      {selectedMethod && (
        <RoutingEditDialog
          method={selectedMethod}
          vendors={routingConfig[selectedMethod] || []}
          allVendors={vendors.map((v) => v.name)}
          open={routingDialogOpen}
          onOpenChange={setRoutingDialogOpen}
          onSuccess={(detail) => {
            loadData();
            addAuditEvent("Routing updated", detail);
          }}
        />
      )}
    </div>
  );
}

interface VendorEditDialogProps {
  vendor: VendorPlugin;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

function VendorEditDialog({ vendor, open, onOpenChange, onSuccess }: VendorEditDialogProps) {
  const [fieldValues, setFieldValues] = React.useState<FieldValues>({});
  const [fieldMeta, setFieldMeta] = React.useState<FieldMeta>({});
  const [showSecrets, setShowSecrets] = React.useState<Record<string, boolean>>({});
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [newKey, setNewKey] = React.useState("");
  const [newValue, setNewValue] = React.useState("");
  const [newType, setNewType] = React.useState<FieldType>("string");
  const { showToast } = useToast();

  React.useEffect(() => {
    if (open) {
      loadConfig();
    }
  }, [open]);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const response = await api.vendors.getConfig(vendor.name);
      const configObj = response.config || {};
      const meta: FieldMeta = {};
      const values: FieldValues = {};
      Object.entries(configObj).forEach(([key, value]) => {
        meta[key] = inferFieldType(value);
        values[key] = stringifyValue(value);
      });
      setFieldMeta(meta);
      setFieldValues(values);
    } catch (error) {
      showToast({
        type: "error",
        title: "Failed to load config",
        description: error instanceof APIError ? error.message : "An error occurred",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      const payload: Record<string, any> = {};
      Object.entries(fieldValues).forEach(([key, value]) => {
        payload[key] = parseValue(value, fieldMeta[key] ?? "string");
      });
      await api.vendors.updateConfig(vendor.name, payload);
      showToast({
        type: "success",
        title: "Config updated",
        description: `${vendor.name} configuration saved successfully`,
      });
      onSuccess();
      onOpenChange(false);
    } catch (error) {
      showToast({
        type: "error",
        title: "Failed to save config",
        description: error instanceof APIError ? error.message : "An error occurred",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleFieldChange = (key: string, value: string) => {
    setFieldValues((prev) => ({ ...prev, [key]: value }));
  };

  const handleBooleanToggle = (key: string) => {
    const current = fieldValues[key] === "true";
    setFieldValues((prev) => ({ ...prev, [key]: current ? "false" : "true" }));
  };

  const handleRemoveField = (key: string) => {
    setFieldValues((prev) => {
      const updated = { ...prev };
      delete updated[key];
      return updated;
    });
    setFieldMeta((prev) => {
      const updated = { ...prev };
      delete updated[key];
      return updated;
    });
  };

  const handleAddField = () => {
    if (!newKey.trim()) {
      showToast({
        type: "error",
        title: "Validation error",
        description: "Config key is required",
      });
      return;
    }
    if (fieldValues[newKey]) {
      showToast({
        type: "error",
        title: "Duplicate key",
        description: `${newKey} already exists in this configuration`,
      });
      return;
    }

    setFieldValues((prev) => ({ ...prev, [newKey]: newValue }));
    setFieldMeta((prev) => ({ ...prev, [newKey]: newType }));
    setShowSecrets((prev) => ({ ...prev, [newKey]: false }));
    setNewKey("");
    setNewValue("");
    setNewType("string");
  };

  const isSecretField = (key: string) => SENSITIVE_KEYS.some((token) => key.toLowerCase().includes(token));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogHeader>
        <DialogTitle>Edit {vendor.name} Configuration</DialogTitle>
        <DialogDescription>
          Update vendor credentials and operational tuning. Sensitive values are masked by default.
        </DialogDescription>
      </DialogHeader>
      <DialogContent className="max-h-[75vh] space-y-6 overflow-y-auto">
        {loading ? (
          <div className="flex h-32 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : (
          <div className="space-y-5">
            {Object.keys(fieldValues).length === 0 ? (
              <p className="text-sm text-muted-foreground">
                This vendor has no configuration entries yet. Add credentials or settings below.
              </p>
            ) : (
              Object.keys(fieldValues).map((key) => {
                const type = fieldMeta[key] ?? "string";
                const isSecret = isSecretField(key);
                const showValue = showSecrets[key] ?? false;
                const value = fieldValues[key];

                return (
                  <div key={key} className="space-y-2 rounded-lg border border-border/60 bg-surface-muted/40 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1">
                        <Label htmlFor={key} className="flex items-center gap-2">
                          {key}
                          <Badge variant="outline" className="text-xs uppercase">{type}</Badge>
                        </Label>
                        <p className="text-xs text-muted-foreground">
                          {isSecret ? "Credential stored securely" : "Editable configuration value"}
                        </p>
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveField(key)}
                      >
                        <Close className="h-4 w-4" />
                      </Button>
                    </div>

                    {type === "boolean" ? (
                      <div className="flex items-center gap-2">
                        <Switch
                          id={key}
                          checked={value === "true"}
                          onCheckedChange={() => handleBooleanToggle(key)}
                        />
                        <span className="text-sm text-muted-foreground">
                          {value === "true" ? "Enabled" : "Disabled"}
                        </span>
                      </div>
                    ) : type === "object" || type === "array" ? (
                      <Textarea
                        id={key}
                        rows={6}
                        value={value}
                        onChange={(e) => handleFieldChange(key, e.target.value)}
                      />
                    ) : (
                      <div className="flex items-center gap-2">
                        <Input
                          id={key}
                          type={isSecret && !showValue ? "password" : type === "number" ? "number" : "text"}
                          value={value}
                          onChange={(e) => handleFieldChange(key, e.target.value)}
                          className="flex-1"
                        />
                        {isSecret && (
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() =>
                              setShowSecrets((prev) => ({ ...prev, [key]: !showValue }))
                            }
                          >
                            {showValue ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                          </Button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })
            )}

            <div className="space-y-3 rounded-lg border border-dashed border-border/70 bg-surface/80 p-4">
              <p className="text-sm font-medium">Add new configuration field</p>
              <div className="grid gap-3 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="newKey">Key</Label>
                  <Input
                    id="newKey"
                    value={newKey}
                    onChange={(e) => setNewKey(e.target.value)}
                    placeholder="api_key"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="newType">Type</Label>
                  <Select value={newType} onValueChange={(value: FieldType) => setNewType(value)}>
                    <SelectTrigger id="newType">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="string">String</SelectItem>
                      <SelectItem value="number">Number</SelectItem>
                      <SelectItem value="boolean">Boolean</SelectItem>
                      <SelectItem value="object">JSON Object</SelectItem>
                      <SelectItem value="array">JSON Array</SelectItem>
                      <SelectItem value="null">Nullable</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="newValue">Value</Label>
                {newType === "object" || newType === "array" ? (
                  <Textarea
                    id="newValue"
                    rows={4}
                    value={newValue}
                    onChange={(e) => setNewValue(e.target.value)}
                    placeholder={newType === "array" ? "[\n  \"primary\",\n  \"fallback\"\n]" : "{\n  \"region\": \"us\"\n}"}
                  />
                ) : newType === "boolean" ? (
                  <Select
                    value={newValue || "false"}
                    onValueChange={(value) => setNewValue(value)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="true">True</SelectItem>
                      <SelectItem value="false">False</SelectItem>
                    </SelectContent>
                  </Select>
                ) : (
                  <Input
                    id="newValue"
                    value={newValue}
                    onChange={(e) => setNewValue(e.target.value)}
                    placeholder="Enter value"
                  />
                )}
              </div>
              <Button type="button" variant="outline" size="sm" className="mt-1" onClick={handleAddField}>
                <Plus className="mr-2 h-4 w-4" />
                Add field
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
      <DialogFooter>
        <Button variant="outline" onClick={() => onOpenChange(false)}>
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={saving || loading}>
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

interface RoutingEditDialogProps {
  method: string;
  vendors: string[];
  allVendors: string[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: (detail: string) => void;
}

function RoutingEditDialog({
  method,
  vendors,
  allVendors,
  open,
  onOpenChange,
  onSuccess,
}: RoutingEditDialogProps) {
  const [orderedVendors, setOrderedVendors] = React.useState<string[]>([]);
  const [saving, setSaving] = React.useState(false);
  const [manualEntry, setManualEntry] = React.useState("");
  const { showToast } = useToast();

  React.useEffect(() => {
    if (open) {
      setOrderedVendors([...vendors]);
      setManualEntry("");
    }
  }, [open, vendors]);

  const handleSave = async () => {
    try {
      setSaving(true);
      await api.vendors.updateRoutingConfig(method, orderedVendors);
      showToast({
        type: "success",
        title: "Routing updated",
        description: `Fallback chain for ${method} updated`,
      });
      onSuccess(`${method} fallback chain -> ${orderedVendors.join(" → ") || "empty"}`);
      onOpenChange(false);
    } catch (error) {
      showToast({
        type: "error",
        title: "Failed to update routing",
        description: error instanceof APIError ? error.message : "An error occurred",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleMoveUp = (index: number) => {
    if (index === 0) return;
    const updated = [...orderedVendors];
    [updated[index - 1], updated[index]] = [updated[index], updated[index - 1]];
    setOrderedVendors(updated);
  };

  const handleMoveDown = (index: number) => {
    if (index === orderedVendors.length - 1) return;
    const updated = [...orderedVendors];
    [updated[index + 1], updated[index]] = [updated[index], updated[index + 1]];
    setOrderedVendors(updated);
  };

  const handleRemove = (index: number) => {
    setOrderedVendors((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleAddVendor = (vendor: string) => {
    if (!vendor) return;
    setOrderedVendors((prev) => (prev.includes(vendor) ? prev : [...prev, vendor]));
  };

  const availableVendors = allVendors.filter((name) => !orderedVendors.includes(name));

  const handleManualAdd = () => {
    if (!manualEntry.trim()) return;
    handleAddVendor(manualEntry.trim());
    setManualEntry("");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogHeader>
        <DialogTitle>Edit routing for {method}</DialogTitle>
        <DialogDescription>
          Order vendors by priority. The first entry is attempted before falling back to subsequent providers.
        </DialogDescription>
      </DialogHeader>
      <DialogContent className="space-y-5">
        <div className="space-y-3">
          <Label>Current priority order</Label>
          {orderedVendors.length === 0 ? (
            <p className="text-sm text-muted-foreground">No vendors in this chain yet.</p>
          ) : (
            <div className="space-y-2">
              {orderedVendors.map((vendor, index) => (
                <div
                  key={vendor}
                  className="flex items-center gap-2 rounded-lg border border-border/60 bg-surface-muted/40 p-2"
                >
                  <span className="rounded bg-background/70 px-2 py-1 text-xs font-semibold">
                    {index + 1}
                  </span>
                  <span className="flex-1 text-sm font-medium">{vendor}</span>
                  <div className="flex gap-1">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => handleMoveUp(index)}
                      disabled={index === 0}
                    >
                      <ArrowUp className="h-4 w-4" />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => handleMoveDown(index)}
                      disabled={index === orderedVendors.length - 1}
                    >
                      <ArrowDown className="h-4 w-4" />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemove(index)}
                    >
                      <Close className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {availableVendors.length > 0 && (
          <div className="space-y-2">
            <Label>Add from registered vendors</Label>
            <div className="flex flex-wrap gap-2">
              {availableVendors.map((vendor) => (
                <Button
                  key={vendor}
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => handleAddVendor(vendor)}
                >
                  + {vendor}
                </Button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="manualVendor">Add vendor by name</Label>
          <div className="flex gap-2">
            <Input
              id="manualVendor"
              value={manualEntry}
              onChange={(e) => setManualEntry(e.target.value)}
              placeholder="custom-provider"
            />
            <Button type="button" variant="outline" onClick={handleManualAdd}>
              Add
            </Button>
          </div>
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
              Save Priority
            </>
          )}
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
