/**
 * 风控建模 Hooks
 *
 * 提供 VaR/CVaR 计算、压力测试和综合风险指标
 */
import { useMutation } from '@tanstack/react-query';
import { request } from '../services/api';

// 类型定义
export interface VaRResult {
  symbols: string[];
  weights: number[];
  confidence: number;
  holding_days: number;
  simulations: number;
  var: number;
  cvar: number;
  var_interpretation: string;
  cvar_interpretation: string;
  histogram: { bin_start: number; bin_end: number; count: number; bin_center: number }[];
  stats: { mean_return: number; std_return: number; min_return: number; max_return: number };
}

export interface StressTestScenario {
  scenario_id: string;
  name: string;
  description: string;
  asset_impacts: { symbol: string; shock: number }[];
  portfolio_loss: number;
  portfolio_loss_interpretation: string;
}

export interface StressTestResult {
  symbols: string[];
  weights: number[];
  scenarios: StressTestScenario[];
}

export interface RiskMetrics {
  symbols: string[];
  weights: number[];
  lookback_days: number;
  metrics: {
    annual_return: number;
    volatility: number;
    sharpe_ratio: number;
    sortino_ratio: number;
    max_drawdown: number;
    beta: number;
    avg_correlation: number;
  };
  interpretation: {
    volatility: string;
    sharpe: string;
    drawdown: string;
    diversification: string;
  };
}

/**
 * VaR/CVaR 计算
 */
export function useCalculateVaR() {
  return useMutation({
    mutationFn: (params: {
      symbols: string[];
      weights?: number[];
      confidence?: number;
      days?: number;
      simulations?: number;
    }) =>
      request<VaRResult>('/risk/var', {
        method: 'POST',
        body: JSON.stringify(params),
      }),
  });
}

/**
 * 压力测试
 */
export function useStressTest() {
  return useMutation({
    mutationFn: (params: { symbols: string[]; weights?: number[]; scenario?: string }) =>
      request<StressTestResult>('/risk/stress-test', {
        method: 'POST',
        body: JSON.stringify(params),
      }),
  });
}

/**
 * 综合风险指标
 */
export function useRiskMetrics() {
  return useMutation({
    mutationFn: (params: { symbols: string[]; weights?: number[]; lookback_days?: number }) =>
      request<RiskMetrics>('/risk/metrics', {
        method: 'POST',
        body: JSON.stringify(params),
      }),
  });
}
