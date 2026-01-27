/**
 * 宏观经济分析 Hooks
 *
 * 提供宏观经济数据和影响分析
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getMacroOverview,
  getMacroImpactAnalysis,
  refreshMacro,
} from '../services/api';

export const MACRO_KEY = ['macro'];

export interface MacroIndicator {
  name: string;
  value: number;
  previous_value?: number;
  change?: number;
  change_percent?: number;
  unit: string;
  date: string;
  source: string;
  trend: 'up' | 'down' | 'stable';
}

export interface MacroOverview {
  fed_rate?: MacroIndicator;
  gdp_growth?: MacroIndicator;
  cpi?: MacroIndicator;
  unemployment?: MacroIndicator;
  pmi?: MacroIndicator;
  treasury_10y?: MacroIndicator;
  vix?: MacroIndicator;
  dxy?: MacroIndicator;
  sentiment: string;
  summary: string;
  last_updated: string;
}

export interface MacroImpact {
  indicator: string;
  impact_level: string;
  direction: string;
  reasoning: string;
}

export interface MacroAnalysisResult {
  overview: MacroOverview;
  impacts: MacroImpact[];
  market_outlook: string;
  risk_factors: string[];
  opportunities: string[];
}

/**
 * 获取宏观经济概览
 */
export function useMacroOverview() {
  return useQuery({
    queryKey: [...MACRO_KEY, 'overview'],
    queryFn: getMacroOverview,
    staleTime: 30 * 60 * 1000, // 30分钟
    refetchInterval: 60 * 60 * 1000, // 1小时自动刷新
  });
}

/**
 * 获取宏观影响分析
 */
export function useMacroImpactAnalysis(market: string = 'US') {
  return useQuery({
    queryKey: [...MACRO_KEY, 'impact', market],
    queryFn: () => getMacroImpactAnalysis(market),
    staleTime: 30 * 60 * 1000,
  });
}

/**
 * 刷新宏观数据
 */
export function useRefreshMacro() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: refreshMacro,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MACRO_KEY });
    },
  });
}
