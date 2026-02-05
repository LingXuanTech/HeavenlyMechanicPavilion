/**
 * AI 配置页面 - 增强版
 *
 * 功能：
 * 1. 管理 AI 提供商（CRUD）
 * 2. 配置模型分配（哪个场景用哪个模型）
 * 3. 测试 API 连接
 * 4. 提供模型推荐和配置指南
 *
 * 使用 standard 布局变体
 */
import React, { useState, useMemo } from 'react';
import {
  Plus,
  CheckCircle,
  XCircle,
  RefreshCw,
  Trash2,
  Edit2,
  Zap,
  Brain,
  FileText,
  Cpu,
  Loader2,
  AlertTriangle,
  HelpCircle,
  ExternalLink,
  Sparkles,
  Shield,
  Activity,
  Info,
} from 'lucide-react';
import PageLayout from '../components/layout/PageLayout';
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
  AIProvider,
  AIProviderType,
} from '../hooks/useAIConfig';
import { useToast } from '../components/Toast';

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

// === 提供商配置信息 ===

interface ProviderInfo {
  label: string;
  description: string;
  docUrl: string;
  defaultBaseUrl: string;
  suggestedModels: string[];
  features: string[];
  apiKeyFormat: string;
}

const PROVIDER_INFO: Record<AIProviderType, ProviderInfo> = {
  openai: {
    label: 'OpenAI',
    description: 'GPT-4o, o4-mini 等模型，支持函数调用和结构化输出',
    docUrl: 'https://platform.openai.com/docs/api-reference',
    defaultBaseUrl: 'https://api.openai.com/v1',
    suggestedModels: ['gpt-4o', 'gpt-4o-mini', 'o4-mini', 'o3', 'gpt-4-turbo'],
    features: ['Function Calling', 'Structured Output', 'Vision', 'Long Context'],
    apiKeyFormat: 'sk-...',
  },
  openai_compatible: {
    label: 'OpenAI Compatible',
    description: '兼容 OpenAI API 的第三方服务（如 Groq、Together、vLLM 等）',
    docUrl: '',
    defaultBaseUrl: '',
    suggestedModels: ['llama-3.1-70b', 'mixtral-8x7b', 'qwen2-72b'],
    features: ['OpenAI API 兼容', '自定义端点'],
    apiKeyFormat: '取决于提供商',
  },
  google: {
    label: 'Google Gemini',
    description: 'Gemini Pro/Flash 系列，支持多模态和长上下文',
    docUrl: 'https://ai.google.dev/gemini-api/docs',
    defaultBaseUrl: '',
    suggestedModels: ['gemini-2.0-flash-exp', 'gemini-1.5-pro', 'gemini-1.5-flash'],
    features: ['Multimodal', '2M Context', 'Grounding', 'Code Execution'],
    apiKeyFormat: 'AIza...',
  },
  anthropic: {
    label: 'Anthropic Claude',
    description: 'Claude 3.5 Sonnet/Opus 系列，擅长分析和推理',
    docUrl: 'https://docs.anthropic.com/claude/reference/getting-started-with-the-api',
    defaultBaseUrl: 'https://api.anthropic.com',
    suggestedModels: ['claude-opus-4-20250514', 'claude-sonnet-4-20250514', 'claude-3-5-sonnet-20241022'],
    features: ['Extended Thinking', 'Tool Use', '200K Context', 'Computer Use'],
    apiKeyFormat: 'sk-ant-...',
  },
  deepseek: {
    label: 'DeepSeek',
    description: 'DeepSeek-V3/R1 系列，高性价比深度推理模型',
    docUrl: 'https://platform.deepseek.com/api-docs',
    defaultBaseUrl: 'https://api.deepseek.com',
    suggestedModels: ['deepseek-chat', 'deepseek-reasoner'],
    features: ['Deep Reasoning', 'Long Context', 'Cost Effective', 'Code Generation'],
    apiKeyFormat: 'sk-...',
  },
};

// === 配置键信息 ===

interface ConfigKeyInfo {
  label: string;
  description: string;
  icon: React.ReactNode;
  recommendedModels: string[];
  importance: 'critical' | 'high' | 'medium';
}

const CONFIG_KEY_INFO: Record<string, ConfigKeyInfo> = {
  deep_think: {
    label: '深度推理 (Deep Think)',
    description: '用于复杂分析任务，如风险评估、Bull/Bear 辩论、最终决策。需要强大的推理能力。',
    icon: <Brain className="w-5 h-5" />,
    recommendedModels: ['claude-opus-4-20250514', 'o4-mini', 'gemini-1.5-pro', 'deepseek-reasoner'],
    importance: 'critical',
  },
  quick_think: {
    label: '快速响应 (Quick Think)',
    description: '用于快速任务，如新闻分析、发现机会、数据摘要。追求速度和成本效率。',
    icon: <Zap className="w-5 h-5" />,
    recommendedModels: ['gpt-4o-mini', 'claude-sonnet-4-20250514', 'gemini-2.0-flash-exp', 'deepseek-chat'],
    importance: 'high',
  },
  synthesis: {
    label: '报告合成 (Synthesis)',
    description: '用于合成多个 Agent 的报告，生成结构化 JSON 输出。需要稳定的格式遵循能力。',
    icon: <FileText className="w-5 h-5" />,
    recommendedModels: ['gpt-4o', 'claude-sonnet-4-20250514', 'gemini-1.5-flash'],
    importance: 'high',
  },
};

const IMPORTANCE_STYLES = {
  critical: 'border-red-500/30 bg-red-500/5',
  high: 'border-amber-500/30 bg-amber-500/5',
  medium: 'border-gray-500/30 bg-gray-500/5',
};

// === 主组件 ===

const AIConfigPage: React.FC = () => {
  const toast = useToast();
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
  const { data: status, refetch: refetchStatus } = useAIConfigStatus();

  // Mutations
  const createProvider = useCreateAIProvider();
  const updateProvider = useUpdateAIProvider();
  const deleteProvider = useDeleteAIProvider();
  const testProvider = useTestAIProvider();
  const updateModelConfig = useUpdateAIModelConfig();
  const refreshConfig = useRefreshAIConfig();

  // 当前选中提供商的信息
  const selectedProviderInfo = useMemo(
    () => PROVIDER_INFO[formData.provider_type],
    [formData.provider_type]
  );

  // ============ Handlers ============

  const handleCreateNew = () => {
    const info = PROVIDER_INFO.openai;
    setFormData({
      name: '',
      provider_type: 'openai',
      base_url: info.defaultBaseUrl,
      api_key: '',
      models: info.suggestedModels.slice(0, 3).join(', '),
      is_enabled: true,
      priority: (providers?.length || 0) + 1,
    });
    setEditMode('create');
    setEditingProviderId(null);
  };

  const handleProviderTypeChange = (type: AIProviderType) => {
    const info = PROVIDER_INFO[type];
    setFormData({
      ...formData,
      provider_type: type,
      base_url: info.defaultBaseUrl,
      models: info.suggestedModels.slice(0, 3).join(', '),
    });
  };

  const handleEdit = (provider: AIProvider) => {
    setFormData({
      name: provider.name,
      provider_type: provider.provider_type,
      base_url: provider.base_url || '',
      api_key: '',
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

    if (!formData.name.trim()) {
      toast.error('请输入提供商名称');
      return;
    }

    if (modelsArray.length === 0) {
      toast.error('请至少添加一个模型');
      return;
    }

    const data = {
      name: formData.name,
      provider_type: formData.provider_type,
      base_url: formData.base_url || undefined,
      api_key: formData.api_key || undefined,
      models: modelsArray,
      is_enabled: formData.is_enabled,
      priority: formData.priority,
    };

    try {
      if (editMode === 'create') {
        await createProvider.mutateAsync(data as any);
        toast.success(`已添加提供商: ${formData.name}`);
      } else if (editMode === 'edit' && editingProviderId) {
        await updateProvider.mutateAsync({ providerId: editingProviderId, data });
        toast.success(`已更新提供商: ${formData.name}`);
      }
      handleCancelEdit();
    } catch (error) {
      toast.error('保存失败: ' + String(error));
    }
  };

  const handleDelete = async (provider: AIProvider) => {
    if (!confirm(`确定要删除提供商 "${provider.name}" 吗？\n\n注意：这可能会影响已配置的模型分配。`)) return;
    try {
      await deleteProvider.mutateAsync(provider.id);
      toast.success(`已删除提供商: ${provider.name}`);
    } catch (error) {
      toast.error('删除失败: ' + String(error));
    }
  };

  const handleTest = async (provider: AIProvider) => {
    setTestResults((prev) => ({ ...prev, [provider.id]: null }));
    try {
      const result = await testProvider.mutateAsync(provider.id);
      setTestResults((prev) => ({
        ...prev,
        [provider.id]: {
          success: result.success,
          message: result.success
            ? `✓ 连接成功! 模型: ${result.model}${result.response_preview ? `\n预览: "${result.response_preview.slice(0, 50)}..."` : ''}`
            : result.error || '未知错误',
        },
      }));
      if (result.success) {
        toast.success(`${provider.name} 连接测试成功`);
      } else {
        toast.error(`${provider.name} 连接测试失败`);
      }
    } catch (error) {
      setTestResults((prev) => ({
        ...prev,
        [provider.id]: { success: false, message: String(error) },
      }));
      toast.error('测试失败: ' + String(error));
    }
  };

  const handleModelConfigChange = async (configKey: string, providerId: number, modelName: string) => {
    try {
      await updateModelConfig.mutateAsync({ configKey, providerId, modelName });
      toast.success('模型配置已更新');
    } catch (error) {
      toast.error('更新失败: ' + String(error));
    }
  };

  const handleRefresh = async () => {
    try {
      await refreshConfig.mutateAsync();
      await refetchStatus();
      toast.success('配置已刷新');
    } catch (error) {
      toast.error('刷新失败: ' + String(error));
    }
  };

  return (
    <PageLayout
      title="AI Configuration"
      subtitle={
        status ? (
          <span className="flex items-center gap-2">
            <span className="flex items-center gap-1">
              <Activity className="w-3 h-3" />
              {status.providers_count} 提供商
            </span>
            <span className="text-gray-600">•</span>
            <span>{status.configs_count} 配置项</span>
            {status.cached_llms.length > 0 && (
              <>
                <span className="text-gray-600">•</span>
                <span className="text-green-400">{status.cached_llms.length} 已缓存</span>
              </>
            )}
          </span>
        ) : '管理 AI 提供商和模型分配'
      }
      icon={Cpu}
      iconColor="text-blue-400"
      iconBgColor="bg-blue-500/10"
      variant="standard"
      actions={[
        {
          label: '刷新',
          icon: RefreshCw,
          onClick: handleRefresh,
          loading: refreshConfig.isPending,
          variant: 'ghost',
        },
      ]}
      noPadding
    >
      {/* Tabs */}
      <div className="flex border-b border-gray-800 bg-gray-900/30">
        <button
          onClick={() => setActiveTab('providers')}
          className={`px-6 py-3 text-sm font-medium transition-colors flex items-center gap-2 ${
            activeTab === 'providers'
              ? 'text-blue-400 border-b-2 border-blue-400 bg-blue-500/5'
              : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
          }`}
        >
          <Shield className="w-4 h-4" />
          提供商管理
        </button>
        <button
          onClick={() => setActiveTab('models')}
          className={`px-6 py-3 text-sm font-medium transition-colors flex items-center gap-2 ${
            activeTab === 'models'
              ? 'text-blue-400 border-b-2 border-blue-400 bg-blue-500/5'
              : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
          }`}
        >
          <Sparkles className="w-4 h-4" />
          模型分配
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto">
          {activeTab === 'providers' && (
            <div className="space-y-4">
              {/* Add Button */}
              {editMode === 'none' && (
                <button
                  onClick={handleCreateNew}
                  className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors font-medium"
                >
                  <Plus className="w-4 h-4" />
                  添加 AI 提供商
                </button>
              )}

              {/* Edit Form */}
              {editMode !== 'none' && (
                <div className="p-5 bg-gray-800/50 rounded-xl border border-gray-700 space-y-5">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-medium text-white">
                      {editMode === 'create' ? '添加新提供商' : '编辑提供商'}
                    </h3>
                    {selectedProviderInfo.docUrl && (
                      <a
                        href={selectedProviderInfo.docUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
                      >
                        <ExternalLink className="w-3 h-3" />
                        API 文档
                      </a>
                    )}
                  </div>

                  {/* Provider Type Selection */}
                  <div>
                    <label className="block text-sm text-gray-300 mb-2">提供商类型</label>
                    <div className="grid grid-cols-5 gap-2">
                      {(Object.keys(PROVIDER_INFO) as AIProviderType[]).map((type) => {
                        const info = PROVIDER_INFO[type];
                        const isSelected = formData.provider_type === type;
                        return (
                          <button
                            key={type}
                            type="button"
                            onClick={() => handleProviderTypeChange(type)}
                            className={`p-3 rounded-lg border text-center transition-all ${
                              isSelected
                                ? 'border-blue-500 bg-blue-500/10 text-white'
                                : 'border-gray-700 bg-gray-800/50 text-gray-400 hover:border-gray-600 hover:text-white'
                            }`}
                          >
                            <div className="text-sm font-medium">{info.label}</div>
                          </button>
                        );
                      })}
                    </div>
                    <p className="mt-2 text-xs text-gray-500">{selectedProviderInfo.description}</p>
                  </div>

                  {/* Features */}
                  <div className="flex flex-wrap gap-2">
                    {selectedProviderInfo.features.map((feature) => (
                      <span
                        key={feature}
                        className="px-2 py-1 bg-gray-700/50 text-gray-400 text-xs rounded"
                      >
                        {feature}
                      </span>
                    ))}
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs text-gray-400 mb-1.5">名称 *</label>
                      <input
                        type="text"
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        className="w-full px-3 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder={`My ${selectedProviderInfo.label}`}
                      />
                    </div>

                    <div>
                      <label className="block text-xs text-gray-400 mb-1.5">
                        Base URL
                        {formData.provider_type === 'openai_compatible' && (
                          <span className="text-red-400 ml-1">*</span>
                        )}
                      </label>
                      <input
                        type="text"
                        value={formData.base_url}
                        onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                        className="w-full px-3 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder={selectedProviderInfo.defaultBaseUrl || 'https://api.example.com/v1'}
                      />
                    </div>

                    <div className="col-span-2">
                      <label className="block text-xs text-gray-400 mb-1.5 flex items-center gap-2">
                        API Key *
                        <span className="text-gray-600">格式: {selectedProviderInfo.apiKeyFormat}</span>
                      </label>
                      <input
                        type="password"
                        value={formData.api_key}
                        onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                        className="w-full px-3 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
                        placeholder={editMode === 'edit' ? '(保持原有密钥不变)' : selectedProviderInfo.apiKeyFormat}
                      />
                    </div>

                    <div className="col-span-2">
                      <label className="block text-xs text-gray-400 mb-1.5 flex items-center justify-between">
                        <span>模型列表 * (逗号分隔)</span>
                        <button
                          type="button"
                          onClick={() =>
                            setFormData({
                              ...formData,
                              models: selectedProviderInfo.suggestedModels.join(', '),
                            })
                          }
                          className="text-blue-400 hover:text-blue-300 text-xs"
                        >
                          使用推荐模型
                        </button>
                      </label>
                      <input
                        type="text"
                        value={formData.models}
                        onChange={(e) => setFormData({ ...formData, models: e.target.value })}
                        className="w-full px-3 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
                        placeholder={selectedProviderInfo.suggestedModels.slice(0, 3).join(', ')}
                      />
                      <p className="mt-1 text-xs text-gray-500">
                        推荐: {selectedProviderInfo.suggestedModels.join(', ')}
                      </p>
                    </div>

                    <div className="flex items-center gap-6">
                      <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={formData.is_enabled}
                          onChange={(e) => setFormData({ ...formData, is_enabled: e.target.checked })}
                          className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-blue-500 focus:ring-offset-gray-800"
                        />
                        启用
                      </label>
                    </div>

                    <div>
                      <label className="block text-xs text-gray-400 mb-1.5 flex items-center gap-1">
                        优先级
                        <HelpCircle className="w-3 h-3 text-gray-600" />
                      </label>
                      <input
                        type="number"
                        value={formData.priority}
                        onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 99 })}
                        className="w-full px-3 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        min="1"
                        max="99"
                      />
                    </div>
                  </div>

                  <div className="flex justify-end gap-3 pt-2">
                    <button
                      onClick={handleCancelEdit}
                      className="px-4 py-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
                    >
                      取消
                    </button>
                    <button
                      onClick={handleSave}
                      disabled={createProvider.isPending || updateProvider.isPending}
                      className="flex items-center gap-2 px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors disabled:opacity-50 font-medium"
                    >
                      {(createProvider.isPending || updateProvider.isPending) && (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      )}
                      保存
                    </button>
                  </div>
                </div>
              )}

              {/* Provider List */}
              {loadingProviders ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                </div>
              ) : providers?.length === 0 ? (
                <div className="text-center py-12 text-gray-400 bg-gray-800/30 rounded-xl border border-dashed border-gray-700">
                  <Cpu className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>尚未配置任何 AI 提供商</p>
                  <p className="text-sm mt-1 text-gray-500">点击上方按钮添加第一个提供商</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {providers?.map((provider) => {
                    const info = PROVIDER_INFO[provider.provider_type];
                    return (
                      <div
                        key={provider.id}
                        className={`p-4 bg-gray-800/50 rounded-xl border transition-all ${
                          provider.is_enabled
                            ? 'border-gray-700 hover:border-gray-600'
                            : 'border-gray-700/50 opacity-60'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="space-y-2 flex-1">
                            <div className="flex items-center gap-3">
                              <span className="font-medium text-white text-lg">{provider.name}</span>
                              <span className="text-xs px-2.5 py-1 bg-gray-700 rounded-full text-gray-300">
                                {info?.label || provider.provider_type}
                              </span>
                              {!provider.is_enabled && (
                                <span className="text-xs px-2.5 py-1 bg-yellow-900/30 text-yellow-400 rounded-full">
                                  已禁用
                                </span>
                              )}
                              <span className="text-xs text-gray-500">优先级: {provider.priority}</span>
                            </div>
                            <div className="text-xs text-gray-400 flex items-center gap-3">
                              {provider.base_url && (
                                <span className="flex items-center gap-1">
                                  <span className="text-gray-600">URL:</span>
                                  {provider.base_url}
                                </span>
                              )}
                              <span className="flex items-center gap-1">
                                <span className="text-gray-600">Key:</span>
                                {provider.api_key_masked}
                              </span>
                            </div>
                            <div className="flex flex-wrap gap-1.5 mt-1">
                              {provider.models.map((model) => (
                                <span
                                  key={model}
                                  className="text-xs px-2 py-1 bg-blue-500/10 text-blue-400 rounded border border-blue-500/20"
                                >
                                  {model}
                                </span>
                              ))}
                            </div>
                          </div>

                          <div className="flex items-center gap-1 ml-4">
                            <button
                              onClick={() => handleTest(provider)}
                              disabled={testProvider.isPending}
                              className="p-2 text-gray-400 hover:text-green-400 hover:bg-green-500/10 rounded-lg transition-colors"
                              title="测试连接"
                            >
                              <Zap className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleEdit(provider)}
                              className="p-2 text-gray-400 hover:text-blue-400 hover:bg-blue-500/10 rounded-lg transition-colors"
                              title="编辑"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleDelete(provider)}
                              disabled={deleteProvider.isPending}
                              className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                              title="删除"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>

                        {/* Test Result */}
                        {testResults[provider.id] && (
                          <div
                            className={`mt-3 p-3 rounded-lg text-sm flex items-start gap-2 ${
                              testResults[provider.id]?.success
                                ? 'bg-green-900/20 text-green-400 border border-green-500/20'
                                : 'bg-red-900/20 text-red-400 border border-red-500/20'
                            }`}
                          >
                            {testResults[provider.id]?.success ? (
                              <CheckCircle className="w-4 h-4 mt-0.5 shrink-0" />
                            ) : (
                              <XCircle className="w-4 h-4 mt-0.5 shrink-0" />
                            )}
                            <pre className="whitespace-pre-wrap text-xs">
                              {testResults[provider.id]?.message}
                            </pre>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {activeTab === 'models' && (
            <div className="space-y-4">
              {/* Info Banner */}
              <div className="p-4 bg-blue-900/20 border border-blue-500/30 rounded-xl flex items-start gap-3">
                <Info className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm text-blue-300">
                    为不同任务类型分配合适的 AI 模型。深度推理任务建议使用更强的模型，快速响应任务可使用轻量模型以节省成本。
                  </p>
                </div>
              </div>

              {loadingConfigs || loadingProviders ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                </div>
              ) : (
                <div className="space-y-4">
                  {modelConfigs?.map((config) => {
                    const info = CONFIG_KEY_INFO[config.config_key];
                    if (!info) return null;

                    return (
                      <div
                        key={config.config_key}
                        className={`p-5 bg-gray-800/50 rounded-xl border ${IMPORTANCE_STYLES[info.importance]}`}
                      >
                        <div className="flex items-start gap-4">
                          <div className={`p-3 rounded-lg ${
                            info.importance === 'critical' ? 'bg-red-500/10 text-red-400' :
                            info.importance === 'high' ? 'bg-amber-500/10 text-amber-400' :
                            'bg-gray-700 text-gray-400'
                          }`}>
                            {info.icon}
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <h4 className="font-medium text-white">{info.label}</h4>
                              {info.importance === 'critical' && (
                                <span className="text-xs px-2 py-0.5 bg-red-500/20 text-red-400 rounded">核心</span>
                              )}
                            </div>
                            <p className="text-xs text-gray-400 mt-1">{info.description}</p>

                            <div className="grid grid-cols-2 gap-4 mt-4">
                              <div>
                                <label className="block text-xs text-gray-400 mb-1.5">提供商</label>
                                <select
                                  value={config.provider_id || ''}
                                  onChange={(e) => {
                                    const providerId = parseInt(e.target.value);
                                    const provider = providers?.find((p) => p.id === providerId);
                                    if (providerId && provider && provider.models.length > 0) {
                                      handleModelConfigChange(config.config_key, providerId, provider.models[0]);
                                    }
                                  }}
                                  className="w-full px-3 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                  <option value="">选择提供商...</option>
                                  {providers
                                    ?.filter((p) => p.is_enabled)
                                    .map((p) => (
                                      <option key={p.id} value={p.id}>
                                        {p.name} ({PROVIDER_INFO[p.provider_type]?.label || p.provider_type})
                                      </option>
                                    ))}
                                </select>
                              </div>

                              <div>
                                <label className="block text-xs text-gray-400 mb-1.5">模型</label>
                                <select
                                  value={config.model_name || ''}
                                  onChange={(e) => {
                                    if (config.provider_id && e.target.value) {
                                      handleModelConfigChange(config.config_key, config.provider_id, e.target.value);
                                    }
                                  }}
                                  disabled={!config.provider_id}
                                  className="w-full px-3 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                                >
                                  <option value="">选择模型...</option>
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

                            {/* Status */}
                            <div className="mt-3">
                              {config.provider_name && config.model_name ? (
                                <div className="text-xs text-green-400 flex items-center gap-1">
                                  <CheckCircle className="w-3.5 h-3.5" />
                                  当前: {config.provider_name} / {config.model_name}
                                </div>
                              ) : (
                                <div className="text-xs text-amber-400 flex items-center gap-1">
                                  <AlertTriangle className="w-3.5 h-3.5" />
                                  未配置 - 将使用系统默认模型
                                </div>
                              )}
                            </div>

                            {/* Recommended */}
                            <div className="mt-3 pt-3 border-t border-gray-700/50">
                              <p className="text-xs text-gray-500">
                                推荐模型: {info.recommendedModels.join(' • ')}
                              </p>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </PageLayout>
  );
};

export default AIConfigPage;
