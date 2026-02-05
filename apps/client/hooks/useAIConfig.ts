/**
 * AI 配置管理 Hooks
 *
 * 提供 AI 提供商和模型配置的 React Query hooks
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as T from '../src/types/schema';
import {
  listAIProviders,
  getAIProvider,
  createAIProvider,
  updateAIProvider,
  deleteAIProvider,
  testAIProvider,
  getAIModelConfigs,
  updateAIModelConfig,
  refreshAIConfig,
  getAIConfigStatus,
} from '../services/api';

// ============ Query Keys ============

const AI_CONFIG_KEY = ['ai-config'];
const AI_PROVIDERS_KEY = [...AI_CONFIG_KEY, 'providers'];
const AI_MODELS_KEY = [...AI_CONFIG_KEY, 'models'];
const AI_STATUS_KEY = [...AI_CONFIG_KEY, 'status'];

// ============ Provider Hooks ============

/**
 * 获取所有 AI 提供商
 */
export function useAIProviders() {
  return useQuery({
    queryKey: AI_PROVIDERS_KEY,
    queryFn: async () => {
      const { providers } = await listAIProviders();
      return providers;
    },
    staleTime: 30 * 1000, // 30秒缓存
  });
}

/**
 * 获取单个 AI 提供商
 */
export function useAIProvider(providerId: number | null) {
  return useQuery({
    queryKey: [...AI_PROVIDERS_KEY, providerId],
    queryFn: () => (providerId ? getAIProvider(providerId) : null),
    enabled: providerId !== null,
  });
}

/**
 * 创建 AI 提供商
 */
export function useCreateAIProvider() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: T.ApiRequestBody<'/api/ai/providers', 'post'>) => createAIProvider(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: AI_PROVIDERS_KEY });
      queryClient.invalidateQueries({ queryKey: AI_STATUS_KEY });
    },
  });
}

/**
 * 更新 AI 提供商
 */
export function useUpdateAIProvider() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      providerId,
      data,
    }: {
      providerId: number;
      data: T.ApiRequestBody<'/api/ai/providers/{provider_id}', 'put'>;
    }) => updateAIProvider(providerId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: AI_PROVIDERS_KEY });
      queryClient.invalidateQueries({ queryKey: [...AI_PROVIDERS_KEY, variables.providerId] });
      queryClient.invalidateQueries({ queryKey: AI_STATUS_KEY });
    },
  });
}

/**
 * 删除 AI 提供商
 */
export function useDeleteAIProvider() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (providerId: number) => deleteAIProvider(providerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: AI_PROVIDERS_KEY });
      queryClient.invalidateQueries({ queryKey: AI_STATUS_KEY });
    },
  });
}

/**
 * 测试 AI 提供商连接
 */
export function useTestAIProvider() {
  return useMutation({
    mutationFn: (providerId: number) => testAIProvider(providerId),
  });
}

// ============ Model Config Hooks ============

/**
 * 获取所有模型配置
 */
export function useAIModelConfigs() {
  return useQuery({
    queryKey: AI_MODELS_KEY,
    queryFn: async () => {
      const { configs } = await getAIModelConfigs();
      return configs;
    },
    staleTime: 30 * 1000,
  });
}

/**
 * 更新模型配置
 */
export function useUpdateAIModelConfig() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      configKey,
      providerId,
      modelName,
    }: {
      configKey: string;
      providerId: number;
      modelName: string;
    }) => updateAIModelConfig(configKey, { provider_id: providerId, model_name: modelName }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: AI_MODELS_KEY });
      queryClient.invalidateQueries({ queryKey: AI_STATUS_KEY });
    },
  });
}

// ============ Management Hooks ============

/**
 * 刷新 AI 配置
 */
export function useRefreshAIConfig() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => refreshAIConfig(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: AI_CONFIG_KEY });
    },
  });
}

/**
 * 获取 AI 配置状态
 */
export function useAIConfigStatus() {
  return useQuery({
    queryKey: AI_STATUS_KEY,
    queryFn: () => getAIConfigStatus(),
    staleTime: 10 * 1000, // 10秒缓存
    refetchInterval: 30 * 1000, // 30秒自动刷新
  });
}

// ============ Utilities ============

/**
 * 获取提供商类型的显示名称
 */
export function getProviderTypeLabel(type: T.AIProviderType): string {
  const labels: Record<T.AIProviderType, string> = {
    openai: 'OpenAI',
    openai_compatible: 'OpenAI Compatible',
    google: 'Google Gemini',
    anthropic: 'Anthropic Claude',
    deepseek: 'DeepSeek',
  };
  return labels[type] || type;
}

/**
 * 获取配置键的显示名称
 */
export function getConfigKeyLabel(key: string): string {
  const labels: Record<string, string> = {
    deep_think: 'Deep Think (Complex reasoning)',
    quick_think: 'Quick Think (Fast responses)',
    synthesis: 'Synthesis (Report generation)',
  };
  return labels[key] || key;
}

/**
 * 获取配置键的描述
 */
export function getConfigKeyDescription(key: string): string {
  const descriptions: Record<string, string> = {
    deep_think: 'Used for complex analysis like risk assessment and debate',
    quick_think: 'Used for quick tasks like discovery and news analysis',
    synthesis: 'Used for synthesizing multiple agent reports',
  };
  return descriptions[key] || '';
}

// Re-export types
export type { AIProvider, AIProviderType, AIModelConfig, AIConfigStatus, TestProviderResult } from '../src/types/schema';
