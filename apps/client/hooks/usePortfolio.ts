/**
 * Portfolio 分析 Hooks
 *
 * 提供组合相关性分析和风险评估
 */
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  getPortfolioCorrelation,
  getPortfolioAnalysis,
  getQuickPortfolioCheck,
  type PortfolioPeriod,
  type PortfolioRebalanceConstraints,
} from '../services/api';

export const PORTFOLIO_KEY = ['portfolio'];

const DEFAULT_PORTFOLIO_PERIOD: PortfolioPeriod = '1mo';
const DEFAULT_CLUSTER_THRESHOLD = 0.7;

export interface PortfolioAnalysisParams {
  symbols: string[];
  period?: PortfolioPeriod;
  clusterThreshold?: number;
  weights?: number[];
  constraints?: PortfolioRebalanceConstraints;
  enableBacktestHint?: boolean;
}

type PortfolioAnalysisInput = string[] | PortfolioAnalysisParams;

interface NormalizedPortfolioParams {
  symbols: string[];
  period: PortfolioPeriod;
  clusterThreshold: number;
  weights?: number[];
  constraints?: PortfolioRebalanceConstraints;
  enableBacktestHint: boolean;
}

const normalizePortfolioParams = (input: PortfolioAnalysisInput): NormalizedPortfolioParams => {
  const params = Array.isArray(input) ? { symbols: input } : input;
  const symbols = (params.symbols ?? []).map((symbol) => symbol.trim()).filter(Boolean);
  const weights = params.weights?.filter((weight) => Number.isFinite(weight));

  return {
    symbols,
    period: params.period ?? DEFAULT_PORTFOLIO_PERIOD,
    clusterThreshold: params.clusterThreshold ?? DEFAULT_CLUSTER_THRESHOLD,
    weights: weights && weights.length === symbols.length ? weights : undefined,
    constraints: params.constraints,
    enableBacktestHint: params.enableBacktestHint ?? true,
  };
};

/**
 * 计算组合相关性
 */
export function usePortfolioCorrelation() {
  return useMutation({
    mutationFn: (input: PortfolioAnalysisInput) => {
      const { symbols, period, weights } = normalizePortfolioParams(input);
      return getPortfolioCorrelation(symbols, { period, weights });
    },
  });
}

/**
 * 完整组合分析
 */
export function usePortfolioAnalysis() {
  return useMutation({
    mutationFn: (input: PortfolioAnalysisInput) => {
      const { symbols, period, clusterThreshold, weights, constraints, enableBacktestHint } =
        normalizePortfolioParams(input);
      return getPortfolioAnalysis(symbols, {
        period,
        clusterThreshold,
        weights,
        constraints,
        enableBacktestHint,
      });
    },
  });
}

/**
 * 快速组合检查
 */
export function useQuickPortfolioCheck(input: PortfolioAnalysisInput) {
  const { symbols, period, clusterThreshold, weights, constraints, enableBacktestHint } =
    normalizePortfolioParams(input);
  const symbolKey = [...symbols].sort().join(',');
  const weightKey = weights ? weights.map((weight) => weight.toFixed(4)).join(',') : 'equal';
  const constraintsKey = constraints
    ? [
        constraints.maxSingleWeight ?? '',
        constraints.maxTop2Weight ?? '',
        constraints.maxTurnover ?? '',
        constraints.riskProfile ?? '',
      ].join(',')
    : 'none';

  return useQuery({
    queryKey: [
      ...PORTFOLIO_KEY,
      'quick',
      symbolKey,
      period,
      clusterThreshold,
      weightKey,
      constraintsKey,
      enableBacktestHint,
    ],
    queryFn: () => getQuickPortfolioCheck(symbols, { period, clusterThreshold, weights }),
    enabled: symbols.length >= 2,
    staleTime: 5 * 60 * 1000, // 5分钟
  });
}
