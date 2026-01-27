import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useCallback } from 'react';
import * as api from '../services/api';
import { AgentAnalysis } from '../types';

export const ANALYSIS_KEY = (symbol: string) => ['analysis', symbol];
export const LATEST_ANALYSIS_KEY = (symbol: string) => ['analysis', 'latest', symbol];

/**
 * 获取最近的分析结果（从数据库）
 */
export function useLatestAnalysis(symbol: string) {
  return useQuery({
    queryKey: LATEST_ANALYSIS_KEY(symbol),
    queryFn: async () => {
      try {
        const response = await fetch(`/api/v1/analyze/latest/${symbol}`);
        if (!response.ok) return null;
        const data = await response.json();
        return data.analysis as AgentAnalysis;
      } catch {
        return null;
      }
    },
    staleTime: 10 * 60 * 1000, // 10分钟
    enabled: !!symbol,
  });
}

/**
 * 执行股票分析的 Hook
 * 管理分析状态和 SSE 进度
 */
export function useStockAnalysis() {
  const queryClient = useQueryClient();
  const [analyzingStates, setAnalyzingStates] = useState<Record<string, boolean>>({});
  const [analyzingStages, setAnalyzingStages] = useState<Record<string, string>>({});

  const runAnalysis = useCallback(async (symbol: string) => {
    setAnalyzingStates(prev => ({ ...prev, [symbol]: true }));

    try {
      await api.analyzeStockWithAgent(symbol, (event, data) => {
        setAnalyzingStages(prev => ({ ...prev, [symbol]: event }));
        if (event === 'stage_final') {
          // 分析完成，更新缓存
          queryClient.setQueryData(ANALYSIS_KEY(symbol), data);
          // 同时使最近分析失效以便重新获取
          queryClient.invalidateQueries({ queryKey: LATEST_ANALYSIS_KEY(symbol) });
        }
      });
    } catch (error) {
      console.error(`Analysis failed for ${symbol}`, error);
      throw error;
    } finally {
      setAnalyzingStates(prev => ({ ...prev, [symbol]: false }));
    }
  }, [queryClient]);

  const runMultipleAnalyses = useCallback(async (symbols: string[], delayMs = 2000) => {
    for (let i = 0; i < symbols.length; i++) {
      if (i > 0) {
        await new Promise(resolve => setTimeout(resolve, delayMs));
      }
      runAnalysis(symbols[i]);
    }
  }, [runAnalysis]);

  return {
    analyzingStates,
    analyzingStages,
    runAnalysis,
    runMultipleAnalyses,
    getAnalysis: (symbol: string) => queryClient.getQueryData<AgentAnalysis>(ANALYSIS_KEY(symbol)),
  };
}

/**
 * 获取所有已缓存的分析结果
 */
export function useCachedAnalyses() {
  const queryClient = useQueryClient();

  const getAll = useCallback((): Record<string, AgentAnalysis> => {
    const cache = queryClient.getQueryCache().getAll();
    const analyses: Record<string, AgentAnalysis> = {};

    cache.forEach(query => {
      if (query.queryKey[0] === 'analysis' && query.queryKey[1] !== 'latest' && query.state.data) {
        const symbol = query.queryKey[1] as string;
        analyses[symbol] = query.state.data as AgentAnalysis;
      }
    });

    return analyses;
  }, [queryClient]);

  return { getAll };
}
