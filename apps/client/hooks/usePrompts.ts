/**
 * Prompt 管理 Hooks
 *
 * 提供 Agent Prompt 配置的读取和更新
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getPrompts,
  getPromptByRole,
  updatePromptByRole,
  updateAllPrompts,
  reloadPrompts,
  PromptConfig,
} from '../services/api';

export const PROMPTS_KEY = ['prompts'];

// 重新导出类型
export type { PromptConfig };

export interface PromptsData {
  prompts: Record<string, PromptConfig>;
  path: string;
}

/**
 * 获取所有 Prompt 配置
 */
export function usePrompts() {
  return useQuery({
    queryKey: PROMPTS_KEY,
    queryFn: getPrompts,
    staleTime: 5 * 60 * 1000, // 5分钟
  });
}

/**
 * 获取单个角色的 Prompt 配置
 */
export function usePromptByRole(role: string) {
  return useQuery({
    queryKey: [...PROMPTS_KEY, role],
    queryFn: () => getPromptByRole(role),
    enabled: !!role,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * 更新单个角色的 Prompt
 */
export function useUpdatePrompt() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ role, config, apiKey }: { role: string; config: PromptConfig; apiKey?: string }) =>
      updatePromptByRole(role, config, apiKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PROMPTS_KEY });
    },
  });
}

/**
 * 批量更新所有 Prompts
 */
export function useUpdateAllPrompts() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ prompts, apiKey }: { prompts: Record<string, PromptConfig>; apiKey?: string }) =>
      updateAllPrompts(prompts, apiKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PROMPTS_KEY });
    },
  });
}

/**
 * 重新加载 Prompts
 */
export function useReloadPrompts() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: reloadPrompts,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PROMPTS_KEY });
    },
  });
}
