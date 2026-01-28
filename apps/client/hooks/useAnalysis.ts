import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, useCallback, useRef } from 'react';
import * as api from '../services/api';
import type { SSEConnectionState, SSEAnalysisController } from '../services/api';
import { AgentAnalysis } from '../types';

export const ANALYSIS_KEY = (symbol: string) => ['analysis', symbol];
export const LATEST_ANALYSIS_KEY = (symbol: string) => ['analysis', 'latest', symbol];

/**
 * 单个股票的分析状态
 */
export interface AnalysisState {
  /** 是否正在分析 */
  isAnalyzing: boolean;
  /** 当前阶段 */
  stage: string;
  /** SSE 连接状态 */
  connectionState: SSEConnectionState | null;
  /** 当前重试次数（重连时） */
  retryCount: number;
  /** 错误信息 */
  error: string | null;
}

const initialAnalysisState: AnalysisState = {
  isAnalyzing: false,
  stage: '',
  connectionState: null,
  retryCount: 0,
  error: null,
};

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
 * 管理分析状态、SSE 进度和重连机制
 */
export function useStockAnalysis() {
  const queryClient = useQueryClient();
  const [analysisStates, setAnalysisStates] = useState<Record<string, AnalysisState>>({});

  // 保存控制器引用，用于取消分析
  const controllersRef = useRef<Record<string, SSEAnalysisController>>({});

  // 更新单个股票的状态
  const updateState = useCallback((symbol: string, updates: Partial<AnalysisState>) => {
    setAnalysisStates((prev) => ({
      ...prev,
      [symbol]: {
        ...(prev[symbol] || initialAnalysisState),
        ...updates,
      },
    }));
  }, []);

  // 获取单个股票的状态
  const getState = useCallback(
    (symbol: string): AnalysisState => analysisStates[symbol] || initialAnalysisState,
    [analysisStates]
  );

  // 执行分析
  const runAnalysis = useCallback(
    async (symbol: string): Promise<void> => {
      // 如果已在分析中，不重复触发
      if (analysisStates[symbol]?.isAnalyzing) {
        console.warn(`Analysis already in progress for ${symbol}`);
        return;
      }

      updateState(symbol, {
        isAnalyzing: true,
        stage: 'starting',
        connectionState: 'connecting',
        retryCount: 0,
        error: null,
      });

      try {
        const controller = await api.analyzeStockWithAgent(
          symbol,
          {
            onEvent: (event, data) => {
              updateState(symbol, { stage: event });

              if (event === 'stage_final') {
                // 分析完成，更新缓存
                queryClient.setQueryData(ANALYSIS_KEY(symbol), data);
                // 同时使最近分析失效以便重新获取
                queryClient.invalidateQueries({ queryKey: LATEST_ANALYSIS_KEY(symbol) });
                updateState(symbol, {
                  isAnalyzing: false,
                  connectionState: 'closed',
                });
              } else if (event === 'error') {
                updateState(symbol, {
                  isAnalyzing: false,
                  connectionState: 'error',
                  error: data?.message || '分析失败',
                });
              }
            },
            onConnectionState: (state, retryCount) => {
              updateState(symbol, {
                connectionState: state,
                retryCount: retryCount || 0,
              });

              // 连接错误时标记分析结束
              if (state === 'error') {
                updateState(symbol, {
                  isAnalyzing: false,
                  error: retryCount ? `重连失败（${retryCount} 次尝试）` : '连接失败',
                });
              }
            },
          },
          {
            maxRetries: 3,
            initialDelay: 1000,
            maxDelay: 8000,
            backoffMultiplier: 2,
          }
        );

        // 保存控制器
        controllersRef.current[symbol] = controller;
      } catch (error) {
        console.error(`Analysis failed for ${symbol}`, error);
        updateState(symbol, {
          isAnalyzing: false,
          connectionState: 'error',
          error: error instanceof Error ? error.message : '未知错误',
        });
        throw error;
      }
    },
    [analysisStates, queryClient, updateState]
  );

  // 取消分析
  const cancelAnalysis = useCallback((symbol: string) => {
    const controller = controllersRef.current[symbol];
    if (controller) {
      controller.abort();
      delete controllersRef.current[symbol];
    }
    updateState(symbol, {
      isAnalyzing: false,
      connectionState: 'closed',
      stage: 'cancelled',
    });
  }, [updateState]);

  // 批量分析
  const runMultipleAnalyses = useCallback(
    async (symbols: string[], delayMs = 2000) => {
      for (let i = 0; i < symbols.length; i++) {
        if (i > 0) {
          await new Promise((resolve) => setTimeout(resolve, delayMs));
        }
        runAnalysis(symbols[i]).catch(() => {
          // 单个失败不影响其他
        });
      }
    },
    [runAnalysis]
  );

  // 兼容旧接口
  const analyzingStates = Object.fromEntries(
    Object.entries(analysisStates).map(([k, v]) => [k, v.isAnalyzing])
  );
  const analyzingStages = Object.fromEntries(
    Object.entries(analysisStates).map(([k, v]) => [k, v.stage])
  );

  return {
    // 新接口
    analysisStates,
    getState,
    runAnalysis,
    cancelAnalysis,
    runMultipleAnalyses,
    getAnalysis: (symbol: string) => queryClient.getQueryData<AgentAnalysis>(ANALYSIS_KEY(symbol)),

    // 兼容旧接口
    analyzingStates,
    analyzingStages,
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
