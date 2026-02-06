/**
 * AI 配置面板组件
 *
 * 功能：
 * 1. 管理 AI 提供商（CRUD）
 * 2. 配置模型分配（哪个场景用哪个模型）
 * 3. 测试 API 连接
 * 4. 刷新配置
 */

import { useState } from 'react';
import { logger } from '../utils/logger';
import {
  X,
  Plus,
  Settings,
  CheckCircle,
  XCircle,
  RefreshCw,
  Trash2,
  Edit2,
  Zap,
  Brain,
  FileText,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import {
  useAIProviders,
  useAIModelConfigs,
  useAIConfigStatus,
  useCreateAIProvider,
  useUpdateAIProvider,
  useDeleteAIProvider,
  useTestAIProvider,
  useUpdateAIModelConfig,
  useRefreshAIConfig,
  getProviderTypeLabel,
  getConfigKeyLabel,
  getConfigKeyDescription,
  AIProvider,
  AIProviderType,
} from '../hooks/useAIConfig';

interface AIConfigPanelProps {
  onClose: () => void;
}

type EditMode = 'none' | 'create' | 'edit';

interface ProviderFormData {
  name: string;
  provider_type: AIProviderType;
  base_url: string;
  api_key: string;
  models: string;
  is_enabled: boolean;
  priority: number;
}

const PROVIDER_TYPES: AIProviderType[] = [
  'openai',
  'openai_compatible',
  'google',
  'anthropic',
  'deepseek',
];

const CONFIG_KEY_ICONS: Record<string, React.ReactNode> = {
  deep_think: <Brain className="w-4 h-4" />,
  quick_think: <Zap className="w-4 h-4" />,
  synthesis: <FileText className="w-4 h-4" />,
};

export function AIConfigPanel({ onClose }: AIConfigPanelProps) {
  const [activeTab, setActiveTab] = useState<'providers' | 'models'>('providers');
  const [editMode, setEditMode] = useState<EditMode>('none');
  const [editingProviderId, setEditingProviderId] = useState<number | null>(null);
  const [formData, setFormData] = useState<ProviderFormData>({
    name: '',
    provider_type: 'openai',
    base_url: '',
    api_key: '',
    models: '',
    is_enabled: true,
    priority: 99,
  });
  const [testResults, setTestResults] = useState<Record<number, { success: boolean; message: string } | null>>({});

  // Queries
  const { data: providers, isLoading: loadingProviders } = useAIProviders();
  const { data: modelConfigs, isLoading: loadingConfigs } = useAIModelConfigs();
  const { data: status } = useAIConfigStatus();

  // Mutations
  const createProvider = useCreateAIProvider();
  const updateProvider = useUpdateAIProvider();
  const deleteProvider = useDeleteAIProvider();
  const testProvider = useTestAIProvider();
  const updateModelConfig = useUpdateAIModelConfig();
  const refreshConfig = useRefreshAIConfig();

  // ============ Handlers ============

  const handleCreateNew = () => {
    setFormData({
      name: '',
      provider_type: 'openai',
      base_url: '',
      api_key: '',
      models: '',
      is_enabled: true,
      priority: 99,
    });
    setEditMode('create');
    setEditingProviderId(null);
  };

  const handleEdit = (provider: AIProvider) => {
    setFormData({
      name: provider.name,
      provider_type: provider.provider_type,
      base_url: provider.base_url || '',
      api_key: '', // 不回显密钥
      models: provider.models.join(', '),
      is_enabled: provider.is_enabled,
      priority: provider.priority,
    });
    setEditMode('edit');
    setEditingProviderId(provider.id);
  };

  const handleCancelEdit = () => {
    setEditMode('none');
    setEditingProviderId(null);
  };

  const handleSave = async () => {
    const modelsArray = formData.models
      .split(',')
      .map((m) => m.trim())
      .filter(Boolean);

    const data = {
      name: formData.name,
      provider_type: formData.provider_type,
      base_url: formData.base_url || null,
      api_key: formData.api_key || '',
      models: modelsArray,
      is_enabled: formData.is_enabled,
      priority: formData.priority,
    } as any;

    try {
      if (editMode === 'create') {
        await createProvider.mutateAsync(data);
      } else if (editMode === 'edit' && editingProviderId) {
        await updateProvider.mutateAsync({ providerId: editingProviderId, data });
      }
      handleCancelEdit();
    } catch (error) {
      logger.error('Failed to save provider:', error);
    }
  };

  const handleDelete = async (providerId: number) => {
    if (!confirm('Are you sure you want to delete this provider?')) return;
    try {
      await deleteProvider.mutateAsync(providerId);
    } catch (error) {
      logger.error('Failed to delete provider:', error);
    }
  };

  const handleTest = async (providerId: number) => {
    setTestResults((prev) => ({ ...prev, [providerId]: null }));
    try {
      const result = await testProvider.mutateAsync(providerId);
      setTestResults((prev) => ({
        ...prev,
        [providerId]: {
          success: result.success,
          message: result.success
            ? `Connected! Model: ${result.model}`
            : result.error || 'Unknown error',
        },
      }));
    } catch (error) {
      setTestResults((prev) => ({
        ...prev,
        [providerId]: { success: false, message: String(error) },
      }));
    }
  };

  const handleModelConfigChange = async (
    configKey: string,
    providerId: number,
    modelName: string
  ) => {
    try {
      await updateModelConfig.mutateAsync({ configKey, providerId, modelName });
    } catch (error) {
      logger.error('Failed to update model config:', error);
    }
  };

  const handleRefresh = async () => {
    try {
      await refreshConfig.mutateAsync();
    } catch (error) {
      logger.error('Failed to refresh config:', error);
    }
  };

  // ============ Render ============

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-surface-raised rounded-xl w-full max-w-4xl max-h-[90vh] overflow-hidden shadow-2xl border border-border-strong">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-strong">
          <div className="flex items-center gap-3">
            <Settings className="w-5 h-5 text-accent" />
            <h2 className="text-lg font-semibold text-white">AI Configuration</h2>
            {status && (
              <span className="text-xs text-stone-400">
                {status.providers_count} providers, {status.configs_count} configs
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleRefresh}
              disabled={refreshConfig.isPending}
              className="p-2 text-stone-400 hover:text-stone-50 hover:bg-surface-muted rounded-lg transition-colors"
              title="Refresh Config"
            >
              <RefreshCw className={`w-4 h-4 ${refreshConfig.isPending ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-2 text-stone-400 hover:text-stone-50 hover:bg-surface-muted rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border-strong">
          <button
            onClick={() => setActiveTab('providers')}
            className={`px-6 py-3 text-sm font-medium transition-colors ${
              activeTab === 'providers'
                ? 'text-accent border-b-2 border-accent'
                : 'text-stone-400 hover:text-stone-50'
            }`}
          >
            Providers
          </button>
          <button
            onClick={() => setActiveTab('models')}
            className={`px-6 py-3 text-sm font-medium transition-colors ${
              activeTab === 'models'
                ? 'text-accent border-b-2 border-accent'
                : 'text-stone-400 hover:text-stone-50'
            }`}
          >
            Model Assignment
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {activeTab === 'providers' && (
            <div className="space-y-4">
              {/* Add Button */}
              {editMode === 'none' && (
                <button
                  onClick={handleCreateNew}
                  className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  Add Provider
                </button>
              )}

              {/* Edit Form */}
              {editMode !== 'none' && (
                <div className="p-4 bg-surface-overlay rounded-lg border border-border-strong space-y-4">
                  <h3 className="text-sm font-medium text-white">
                    {editMode === 'create' ? 'New Provider' : 'Edit Provider'}
                  </h3>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs text-stone-400 mb-1">Name</label>
                      <input
                        type="text"
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        className="w-full px-3 py-2 bg-surface-muted border border-border-strong rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                        placeholder="My OpenAI"
                      />
                    </div>

                    <div>
                      <label className="block text-xs text-stone-400 mb-1">Type</label>
                      <select
                        value={formData.provider_type}
                        onChange={(e) =>
                          setFormData({ ...formData, provider_type: e.target.value as AIProviderType })
                        }
                        className="w-full px-3 py-2 bg-surface-muted border border-border-strong rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                      >
                        {PROVIDER_TYPES.map((type) => (
                          <option key={type} value={type}>
                            {getProviderTypeLabel(type)}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs text-stone-400 mb-1">
                        Base URL {formData.provider_type === 'openai_compatible' && '(Required)'}
                      </label>
                      <input
                        type="text"
                        value={formData.base_url}
                        onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                        className="w-full px-3 py-2 bg-surface-muted border border-border-strong rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                        placeholder="https://api.openai.com/v1"
                      />
                    </div>

                    <div>
                      <label className="block text-xs text-stone-400 mb-1">API Key</label>
                      <input
                        type="password"
                        value={formData.api_key}
                        onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                        className="w-full px-3 py-2 bg-surface-muted border border-border-strong rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                        placeholder={editMode === 'edit' ? '(unchanged)' : 'sk-...'}
                      />
                    </div>

                    <div className="col-span-2">
                      <label className="block text-xs text-stone-400 mb-1">
                        Models (comma-separated)
                      </label>
                      <input
                        type="text"
                        value={formData.models}
                        onChange={(e) => setFormData({ ...formData, models: e.target.value })}
                        className="w-full px-3 py-2 bg-surface-muted border border-border-strong rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                        placeholder="gpt-4o, gpt-4o-mini, o4-mini"
                      />
                    </div>

                    <div className="flex items-center gap-4">
                      <label className="flex items-center gap-2 text-sm text-stone-300">
                        <input
                          type="checkbox"
                          checked={formData.is_enabled}
                          onChange={(e) => setFormData({ ...formData, is_enabled: e.target.checked })}
                          className="w-4 h-4 rounded border-border-strong bg-surface-muted text-accent focus:ring-accent"
                        />
                        Enabled
                      </label>
                    </div>

                    <div>
                      <label className="block text-xs text-stone-400 mb-1">Priority</label>
                      <input
                        type="number"
                        value={formData.priority}
                        onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 99 })}
                        className="w-full px-3 py-2 bg-surface-muted border border-border-strong rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                        min="0"
                        max="99"
                      />
                    </div>
                  </div>

                  <div className="flex justify-end gap-2">
                    <button
                      onClick={handleCancelEdit}
                      className="px-4 py-2 text-stone-400 hover:text-stone-50 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSave}
                      disabled={createProvider.isPending || updateProvider.isPending}
                      className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors disabled:opacity-50"
                    >
                      {(createProvider.isPending || updateProvider.isPending) && (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      )}
                      Save
                    </button>
                  </div>
                </div>
              )}

              {/* Provider List */}
              {loadingProviders ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-stone-400" />
                </div>
              ) : (
                <div className="space-y-3">
                  {providers?.map((provider) => (
                    <div
                      key={provider.id}
                      className={`p-4 bg-surface-overlay rounded-lg border ${
                        provider.is_enabled ? 'border-border-strong' : 'border-border-strong/50 opacity-60'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-white">{provider.name}</span>
                            <span className="text-xs px-2 py-0.5 bg-surface-muted rounded-full text-stone-300">
                              {getProviderTypeLabel(provider.provider_type)}
                            </span>
                            {!provider.is_enabled && (
                              <span className="text-xs px-2 py-0.5 bg-yellow-900/30 text-yellow-400 rounded-full">
                                Disabled
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-stone-400">
                            {provider.base_url && <span className="mr-3">URL: {provider.base_url}</span>}
                            <span>Key: {provider.api_key_masked}</span>
                          </div>
                          <div className="flex flex-wrap gap-1 mt-2">
                            {provider.models.map((model) => (
                              <span
                                key={model}
                                className="text-xs px-2 py-0.5 bg-surface-muted/50 text-stone-400 rounded"
                              >
                                {model}
                              </span>
                            ))}
                          </div>
                        </div>

                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleTest(provider.id)}
                            disabled={testProvider.isPending}
                            className="p-2 text-stone-400 hover:text-green-400 hover:bg-surface-muted rounded-lg transition-colors"
                            title="Test Connection"
                          >
                            <Zap className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleEdit(provider)}
                            className="p-2 text-stone-400 hover:text-accent hover:bg-surface-muted rounded-lg transition-colors"
                            title="Edit"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(provider.id)}
                            disabled={deleteProvider.isPending}
                            className="p-2 text-stone-400 hover:text-red-400 hover:bg-surface-muted rounded-lg transition-colors"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>

                      {/* Test Result */}
                      {testResults[provider.id] && (
                        <div
                          className={`mt-3 p-2 rounded-lg text-xs flex items-center gap-2 ${
                            testResults[provider.id]?.success
                              ? 'bg-green-900/20 text-green-400'
                              : 'bg-red-900/20 text-red-400'
                          }`}
                        >
                          {testResults[provider.id]?.success ? (
                            <CheckCircle className="w-4 h-4" />
                          ) : (
                            <XCircle className="w-4 h-4" />
                          )}
                          {testResults[provider.id]?.message}
                        </div>
                      )}
                    </div>
                  ))}

                  {providers?.length === 0 && (
                    <div className="text-center py-8 text-stone-400">
                      No providers configured. Click "Add Provider" to get started.
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {activeTab === 'models' && (
            <div className="space-y-4">
              <p className="text-sm text-stone-400 mb-4">
                Assign which provider and model to use for each task type.
              </p>

              {loadingConfigs || loadingProviders ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-stone-400" />
                </div>
              ) : (
                <div className="space-y-4">
                  {modelConfigs?.map((config) => (
                    <div
                      key={config.config_key}
                      className="p-4 bg-surface-overlay rounded-lg border border-border-strong"
                    >
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-surface-muted rounded-lg text-accent">
                          {CONFIG_KEY_ICONS[config.config_key] || <Settings className="w-4 h-4" />}
                        </div>
                        <div className="flex-1">
                          <div className="font-medium text-white">
                            {getConfigKeyLabel(config.config_key)}
                          </div>
                          <div className="text-xs text-stone-400 mt-0.5">
                            {getConfigKeyDescription(config.config_key)}
                          </div>

                          <div className="grid grid-cols-2 gap-3 mt-3">
                            <div>
                              <label className="block text-xs text-stone-400 mb-1">Provider</label>
                              <select
                                value={config.provider_id || ''}
                                onChange={(e) => {
                                  const providerId = parseInt(e.target.value);
                                  if (providerId && config.model_name) {
                                    handleModelConfigChange(
                                      config.config_key,
                                      providerId,
                                      config.model_name
                                    );
                                  }
                                }}
                                className="w-full px-3 py-2 bg-surface-muted border border-border-strong rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                              >
                                <option value="">Select provider...</option>
                                {providers
                                  ?.filter((p) => p.is_enabled)
                                  .map((p) => (
                                    <option key={p.id} value={p.id}>
                                      {p.name}
                                    </option>
                                  ))}
                              </select>
                            </div>

                            <div>
                              <label className="block text-xs text-stone-400 mb-1">Model</label>
                              <select
                                value={config.model_name || ''}
                                onChange={(e) => {
                                  if (config.provider_id && e.target.value) {
                                    handleModelConfigChange(
                                      config.config_key,
                                      config.provider_id,
                                      e.target.value
                                    );
                                  }
                                }}
                                className="w-full px-3 py-2 bg-surface-muted border border-border-strong rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                              >
                                <option value="">Select model...</option>
                                {config.provider_id &&
                                  providers
                                    ?.find((p) => p.id === config.provider_id)
                                    ?.models.map((m) => (
                                      <option key={m} value={m}>
                                        {m}
                                      </option>
                                    ))}
                              </select>
                            </div>
                          </div>

                          {config.provider_name && config.model_name && (
                            <div className="mt-2 text-xs text-green-400 flex items-center gap-1">
                              <CheckCircle className="w-3 h-3" />
                              Using {config.provider_name} / {config.model_name}
                            </div>
                          )}
                          {!config.provider_id && (
                            <div className="mt-2 text-xs text-yellow-400 flex items-center gap-1">
                              <AlertTriangle className="w-3 h-3" />
                              No provider assigned - will use fallback
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AIConfigPanel;
