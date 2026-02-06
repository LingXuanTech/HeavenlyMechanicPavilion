/**
 * Vision 分析 Hooks
 */

import { useMutation, useQuery } from '@tanstack/react-query';
import { API_BASE } from '../services/api';
import type * as T from '../src/types/schema';

// ============ Query Keys ============

export const visionKeys = {
  all: ['vision'] as const,
  history: (symbol?: string) => [...visionKeys.all, 'history', symbol] as const,
};

// ============ Re-export Types ============
export type {
  VisionAnalysisResult,
  VisionAnalysisResponse,
  VisionKeyDataPoint,
} from '../src/types/schema';

// ============ Hooks ============

/**
 * Vision 图片分析 Mutation
 */
export function useVisionAnalysis() {
  return useMutation({
    mutationFn: async ({
      file,
      description = '',
      symbol = '',
    }: {
      file: File;
      description?: string;
      symbol?: string;
    }): Promise<T.VisionAnalysisResponse> => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('description', description);
      formData.append('symbol', symbol);

      const response = await fetch(`${API_BASE}/vision/analyze`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => response.statusText);
        throw new Error(`Vision analysis failed: ${errorText}`);
      }

      return response.json();
    },
  });
}

/**
 * Vision 分析历史
 */
export function useVisionHistory(symbol?: string, limit: number = 10) {
  return useQuery({
    queryKey: visionKeys.history(symbol),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (symbol) params.append('symbol', symbol);
      params.append('limit', String(limit));
      const query = params.toString() ? `?${params.toString()}` : '';

      const response = await fetch(`${API_BASE}/vision/history${query}`);
      if (!response.ok) throw new Error('Failed to fetch vision history');
      return response.json();
    },
    staleTime: 5 * 60 * 1000,
  });
}
