/**
 * 组合分析页面
 *
 * 展示投资组合相关性分析和分散化建议
 */
import React, { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import { useQuery, useQueries, useQueryClient } from '@tanstack/react-query';
import { logger } from '../utils/logger';
import {
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Info,
  PieChart,
  Link2,
  Play,
  X,
} from 'lucide-react';
import PageLayout, { LoadingState, EmptyState } from '../components/layout/PageLayout';
import {
  useWatchlist,
  usePortfolioAnalysis,
  useQuickPortfolioCheck,
  useRunBacktest,
  BACKTEST_KEY,
} from '../hooks';
import { getBacktestDetail, getBacktestHistory } from '../services/api';
import type {
  BacktestDetailResponse,
  BacktestHistoryItem,
  BacktestRunRequest,
  PortfolioPeriod,
  PortfolioRebalanceConstraints,
  PortfolioRiskProfile,
} from '../services/api';
import type * as T from '../src/types/schema';

const PERIOD_OPTIONS: Array<{ value: PortfolioPeriod; label: string }> = [
  { value: '5d', label: '5 日' },
  { value: '1mo', label: '1 月' },
  { value: '3mo', label: '3 月' },
  { value: '6mo', label: '6 月' },
  { value: '1y', label: '1 年' },
];

const CLUSTER_THRESHOLD_OPTIONS = [
  { value: 0.6, label: '0.60（敏感）' },
  { value: 0.7, label: '0.70（平衡）' },
  { value: 0.8, label: '0.80（严格）' },
];

type WeightMode = 'equal' | 'custom';
type WeightTemplate = 'aggressive' | 'balanced' | 'defensive';
type PresetImportMode = 'merge' | 'replace';
type PresetFeedbackType = 'success' | 'error' | 'info';

interface PresetFeedback {
  type: PresetFeedbackType;
  message: string;
}

interface PresetCompatibility {
  matchedSymbols: number;
  missingSymbols: string[];
  extraSymbols: string[];
  coverage: number;
}

type RebalanceAction = 'increase' | 'decrease' | 'hold';

interface RebalanceSuggestionItem {
  symbol: string;
  currentWeight: number;
  targetWeight: number;
  delta: number;
  action: RebalanceAction;
  volatility: number;
  totalReturn: number;
  confidence?: number;
  rationale?: string;
  source: 'server' | 'client';
}

interface ConstraintViolationItem {
  code: string;
  message: string;
  actual: number;
  limit: number;
  severity: 'warning' | 'critical';
}

interface BacktestPayloadHintItem {
  strategy_name: string;
  generated_at: string;
  requests: Array<{
    symbol: string;
    signals: Array<{
      date: string;
      signal: 'bullish' | 'bearish' | 'neutral';
      confidence: number;
      source: string;
    }>;
    initial_capital: number;
    holding_days: number;
    stop_loss_pct: number;
    take_profit_pct: number;
    use_historical_signals: boolean;
    days_back: number;
  }>;
}

interface BacktestExecutionSnapshot {
  status: 'running' | 'success' | 'error';
  finishedAt?: string;
  totalReturnPct?: number;
  winRate?: number;
  totalTrades?: number;
  message?: string;
}

interface BacktestExecutionSummary {
  success: number;
  failed: number;
}

type PortfolioAnalysisExtended = T.PortfolioAnalysis & {
  constraint_violations?: ConstraintViolationItem[];
  backtest_payload_hint?: BacktestPayloadHintItem | null;
};

const WEIGHT_TEMPLATE_OPTIONS: Array<{ value: WeightTemplate; label: string }> = [
  { value: 'aggressive', label: '进攻' },
  { value: 'balanced', label: '均衡' },
  { value: 'defensive', label: '防御' },
];

const RISK_PROFILE_OPTIONS: Array<{ value: PortfolioRiskProfile; label: string }> = [
  { value: 'conservative', label: '稳健' },
  { value: 'balanced', label: '均衡' },
  { value: 'aggressive', label: '进取' },
];

const DEFAULT_REBALANCE_CONSTRAINTS: Required<PortfolioRebalanceConstraints> = {
  maxSingleWeight: 0.45,
  maxTop2Weight: 0.65,
  maxTurnover: 0.35,
  riskProfile: 'balanced',
};

const PORTFOLIO_SETTINGS_STORAGE_KEY = 'portfolio.analysis.settings.v1';

interface PersistedPortfolioSettings {
  period: PortfolioPeriod;
  clusterThreshold: number;
  weightMode: WeightMode;
  customWeightInputs: Record<string, string>;
  rebalanceConstraints: Required<PortfolioRebalanceConstraints>;
  enableBacktestHint: boolean;
}

interface WeightPreset {
  id: string;
  name: string;
  weights: Record<string, number>;
  createdAt: number;
}

const WEIGHT_PRESETS_STORAGE_KEY = 'portfolio.weight.presets.v1';
const MAX_WEIGHT_PRESETS = 12;
const MAX_PRESET_NAME_LENGTH = 32;
const PRESET_FEEDBACK_DURATION_MS = 3200;
const BACKTEST_FEEDBACK_DURATION_MS = 4800;

const isPortfolioPeriod = (value: string): value is PortfolioPeriod =>
  PERIOD_OPTIONS.some((option) => option.value === value);

const clamp = (value: number, min: number, max: number): number =>
  Math.min(max, Math.max(min, value));

const normalizePresetName = (name: string): string => name.trim().toLowerCase();

const loadPersistedPortfolioSettings = (): PersistedPortfolioSettings => {
  const fallback: PersistedPortfolioSettings = {
    period: '1mo',
    clusterThreshold: 0.7,
    weightMode: 'equal',
    customWeightInputs: {},
    rebalanceConstraints: DEFAULT_REBALANCE_CONSTRAINTS,
    enableBacktestHint: true,
  };

  if (typeof window === 'undefined') {
    return fallback;
  }

  try {
    const raw = window.localStorage.getItem(PORTFOLIO_SETTINGS_STORAGE_KEY);
    if (!raw) {
      return fallback;
    }

    const parsed = JSON.parse(raw) as Partial<PersistedPortfolioSettings>;

    const period =
      typeof parsed.period === 'string' && isPortfolioPeriod(parsed.period)
        ? parsed.period
        : fallback.period;

    const clusterThreshold =
      typeof parsed.clusterThreshold === 'number' && Number.isFinite(parsed.clusterThreshold)
        ? clamp(parsed.clusterThreshold, 0.5, 0.95)
        : fallback.clusterThreshold;

    const weightMode = parsed.weightMode === 'custom' ? 'custom' : 'equal';

    const customWeightInputs =
      parsed.customWeightInputs && typeof parsed.customWeightInputs === 'object'
        ? Object.entries(parsed.customWeightInputs).reduce<Record<string, string>>(
            (accumulator, [symbol, value]) => {
              if (typeof value === 'string') {
                accumulator[symbol] = value;
              }
              return accumulator;
            },
            {}
          )
        : {};

    const rawConstraints = parsed.rebalanceConstraints;
    const rebalanceConstraints: Required<PortfolioRebalanceConstraints> = {
      maxSingleWeight:
        rawConstraints && typeof rawConstraints.maxSingleWeight === 'number'
          ? clamp(rawConstraints.maxSingleWeight, 0.1, 0.9)
          : DEFAULT_REBALANCE_CONSTRAINTS.maxSingleWeight,
      maxTop2Weight:
        rawConstraints && typeof rawConstraints.maxTop2Weight === 'number'
          ? clamp(rawConstraints.maxTop2Weight, 0.2, 1)
          : DEFAULT_REBALANCE_CONSTRAINTS.maxTop2Weight,
      maxTurnover:
        rawConstraints && typeof rawConstraints.maxTurnover === 'number'
          ? clamp(rawConstraints.maxTurnover, 0, 1)
          : DEFAULT_REBALANCE_CONSTRAINTS.maxTurnover,
      riskProfile:
        rawConstraints &&
        typeof rawConstraints.riskProfile === 'string' &&
        ['conservative', 'balanced', 'aggressive'].includes(rawConstraints.riskProfile)
          ? (rawConstraints.riskProfile as PortfolioRiskProfile)
          : DEFAULT_REBALANCE_CONSTRAINTS.riskProfile,
    };

    const enableBacktestHint =
      typeof parsed.enableBacktestHint === 'boolean' ? parsed.enableBacktestHint : true;

    return {
      period,
      clusterThreshold,
      weightMode,
      customWeightInputs,
      rebalanceConstraints,
      enableBacktestHint,
    };
  } catch {
    return fallback;
  }
};

const parseWeightPresets = (input: unknown): WeightPreset[] => {
  if (!Array.isArray(input)) {
    return [];
  }

  return input
    .map((item): WeightPreset | null => {
      if (!item || typeof item !== 'object') {
        return null;
      }

      const id = typeof item.id === 'string' ? item.id : '';
      const name =
        typeof item.name === 'string' ? item.name.trim().slice(0, MAX_PRESET_NAME_LENGTH) : '';
      const createdAt = typeof item.createdAt === 'number' ? item.createdAt : Date.now();

      if (!id || !name) {
        return null;
      }

      const sourceWeights = item.weights && typeof item.weights === 'object' ? item.weights : null;
      if (!sourceWeights) {
        return null;
      }

      const weights = Object.entries(sourceWeights).reduce<Record<string, number>>(
        (accumulator, [symbol, value]) => {
          if (typeof value === 'number' && Number.isFinite(value) && value >= 0) {
            accumulator[symbol] = value;
          }
          return accumulator;
        },
        {}
      );

      if (Object.keys(weights).length === 0) {
        return null;
      }

      return { id, name, createdAt, weights };
    })
    .filter((preset): preset is WeightPreset => Boolean(preset))
    .slice(0, MAX_WEIGHT_PRESETS);
};

const loadPersistedWeightPresets = (): WeightPreset[] => {
  if (typeof window === 'undefined') {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(WEIGHT_PRESETS_STORAGE_KEY);
    if (!raw) {
      return [];
    }

    const parsed = JSON.parse(raw);
    return parseWeightPresets(parsed);
  } catch {
    return [];
  }
};

const normalizeWeightScores = (scores: number[]): number[] => {
  if (scores.length === 0) {
    return [];
  }

  const safeScores = scores.map((score) => (Number.isFinite(score) && score > 0 ? score : 0));
  const total = safeScores.reduce((sum, score) => sum + score, 0);

  if (total <= 0) {
    const equalWeight = 1 / scores.length;
    return scores.map(() => equalWeight);
  }

  return safeScores.map((score) => score / total);
};

const getPresetCompatibility = (symbols: string[], preset: WeightPreset): PresetCompatibility => {
  const symbolSet = new Set(symbols);
  const presetSymbols = Object.keys(preset.weights);

  const matchedSymbols = symbols.filter((symbol) => Object.prototype.hasOwnProperty.call(preset.weights, symbol));
  const missingSymbols = symbols.filter((symbol) => !Object.prototype.hasOwnProperty.call(preset.weights, symbol));
  const extraSymbols = presetSymbols.filter((symbol) => !symbolSet.has(symbol));

  return {
    matchedSymbols: matchedSymbols.length,
    missingSymbols,
    extraSymbols,
    coverage: symbols.length > 0 ? matchedSymbols.length / symbols.length : 0,
  };
};

// 相关性颜色映射
const getCorrelationColor = (value: number): string => {
  if (value >= 0.7) return 'bg-red-600';
  if (value >= 0.4) return 'bg-orange-500';
  if (value >= 0.1) return 'bg-yellow-500';
  if (value >= -0.1) return 'bg-stone-600';
  if (value >= -0.4) return 'bg-cyan-500';
  if (value >= -0.7) return 'bg-blue-500';
  return 'bg-blue-700';
};

const getCorrelationTextColor = (value: number): string => {
  if (Math.abs(value) >= 0.4) return 'text-white';
  return 'text-stone-300';
};

const getDiversificationColor = (score: number): string => {
  if (score >= 70) return 'text-green-400';
  if (score >= 40) return 'text-yellow-400';
  return 'text-red-400';
};

const getDiversificationBarColor = (score: number): string => {
  if (score >= 70) return 'bg-green-500';
  if (score >= 40) return 'bg-yellow-500';
  return 'bg-red-500';
};

const stripRecommendationPrefix = (text?: string | null): string => {
  if (!text) return '暂无建议';
  return text.replace(/^[^a-zA-Z0-9\u4e00-\u9fa5]+/, '').trim() || text;
};

const normalizeBacktestDate = (value: string): string => {
  if (!value) {
    return '';
  }

  const normalized = value.trim();
  if (!normalized) {
    return '';
  }

  if (normalized.includes('T')) {
    return normalized.split('T', 1)[0];
  }

  return normalized.length > 10 ? normalized.slice(0, 10) : normalized;
};

const normalizeBacktestSignal = (value: 'bullish' | 'bearish' | 'neutral', confidence: number): string => {
  if (value === 'bullish') {
    return confidence >= 0.75 ? 'Strong Buy' : 'Buy';
  }

  if (value === 'bearish') {
    return confidence >= 0.75 ? 'Strong Sell' : 'Sell';
  }

  return 'Hold';
};

// 热力图单元格组件
const HeatmapCell: React.FC<{
  value: number;
  rowSymbol: string;
  colSymbol: string;
  isDiagonal: boolean;
}> = ({ value, rowSymbol, colSymbol, isDiagonal }) => {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div
      className={`relative w-12 h-12 flex items-center justify-center text-xs font-mono cursor-pointer transition-all hover:ring-2 hover:ring-white/50 ${
        isDiagonal ? 'bg-surface-muted' : getCorrelationColor(value)
      } ${getCorrelationTextColor(value)}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      {value.toFixed(2)}

      {showTooltip && !isDiagonal && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-surface-raised border border-border-strong rounded-lg shadow-xl z-50 whitespace-nowrap">
          <div className="text-xs text-stone-400">
            {rowSymbol} ↔ {colSymbol}
          </div>
          <div className={`text-sm font-bold ${value > 0 ? 'text-red-400' : 'text-blue-400'}`}>
            {value > 0 ? '正相关' : '负相关'}: {(value * 100).toFixed(1)}%
          </div>
        </div>
      )}
    </div>
  );
};

const PortfolioPage: React.FC = () => {
  const queryClient = useQueryClient();
  const persistedSettings = useMemo(loadPersistedPortfolioSettings, []);

  const { data: stocks = [] } = useWatchlist();
  const portfolioMutation = usePortfolioAnalysis();
  const backtestMutation = useRunBacktest();
  const [analysis, setAnalysis] = useState<T.PortfolioAnalysis | null>(null);
  const [period, setPeriod] = useState<PortfolioPeriod>(persistedSettings.period);
  const [clusterThreshold, setClusterThreshold] = useState<number>(persistedSettings.clusterThreshold);
  const [weightMode, setWeightMode] = useState<WeightMode>(persistedSettings.weightMode);
  const [customWeightInputs, setCustomWeightInputs] = useState<Record<string, string>>(
    persistedSettings.customWeightInputs
  );
  const [rebalanceConstraints, setRebalanceConstraints] = useState<Required<PortfolioRebalanceConstraints>>(
    persistedSettings.rebalanceConstraints
  );
  const [enableBacktestHint, setEnableBacktestHint] = useState<boolean>(
    persistedSettings.enableBacktestHint
  );
  const [savedWeightPresets, setSavedWeightPresets] = useState<WeightPreset[]>(() =>
    loadPersistedWeightPresets()
  );
  const [presetNameInput, setPresetNameInput] = useState<string>('');
  const [editingPresetId, setEditingPresetId] = useState<string | null>(null);
  const [editingPresetName, setEditingPresetName] = useState<string>('');
  const [presetImportMode, setPresetImportMode] = useState<PresetImportMode>('merge');
  const [presetFeedback, setPresetFeedback] = useState<PresetFeedback | null>(null);
  const [backtestFeedback, setBacktestFeedback] = useState<PresetFeedback | null>(null);
  const [backtestExecutionMap, setBacktestExecutionMap] = useState<Record<string, BacktestExecutionSnapshot>>({});
  const [isRunningAllBacktests, setIsRunningAllBacktests] = useState(false);
  const [selectedBacktestRecord, setSelectedBacktestRecord] = useState<{
    symbol: string;
    recordId: number;
  } | null>(null);
  const importPresetsInputRef = useRef<HTMLInputElement | null>(null);
  const [latestAnalysisRequestKey, setLatestAnalysisRequestKey] = useState<string>('');

  const symbols = useMemo(() => stocks.map((stock) => stock.symbol).filter(Boolean), [stocks]);
  const symbolFingerprint = useMemo(() => [...symbols].sort().join(','), [symbols]);

  const presetCompatibilityMap = useMemo(
    () =>
      new Map<string, PresetCompatibility>(
        savedWeightPresets.map((preset) => [preset.id, getPresetCompatibility(symbols, preset)])
      ),
    [savedWeightPresets, symbols]
  );

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const payload: PersistedPortfolioSettings = {
      period,
      clusterThreshold,
      weightMode,
      customWeightInputs,
      rebalanceConstraints,
      enableBacktestHint,
    };

    window.localStorage.setItem(PORTFOLIO_SETTINGS_STORAGE_KEY, JSON.stringify(payload));
  }, [period, clusterThreshold, weightMode, customWeightInputs, rebalanceConstraints, enableBacktestHint]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    window.localStorage.setItem(WEIGHT_PRESETS_STORAGE_KEY, JSON.stringify(savedWeightPresets));
  }, [savedWeightPresets]);

  useEffect(() => {
    if (!presetFeedback || typeof window === 'undefined') {
      return;
    }

    const timer = window.setTimeout(() => {
      setPresetFeedback(null);
    }, PRESET_FEEDBACK_DURATION_MS);

    return () => window.clearTimeout(timer);
  }, [presetFeedback]);

  useEffect(() => {
    if (!backtestFeedback || typeof window === 'undefined') {
      return;
    }

    const timer = window.setTimeout(() => {
      setBacktestFeedback(null);
    }, BACKTEST_FEEDBACK_DURATION_MS);

    return () => window.clearTimeout(timer);
  }, [backtestFeedback]);

  useEffect(() => {
    const equalWeight = symbols.length > 0 ? 100 / symbols.length : 0;

    setCustomWeightInputs((previous) => {
      const next: Record<string, string> = {};
      for (const symbol of symbols) {
        next[symbol] = previous[symbol] ?? equalWeight.toFixed(2);
      }
      return next;
    });
  }, [symbolFingerprint]);

  const returnsSummaryMap = useMemo(() => {
    const summary = analysis?.correlation.returns_summary;
    if (!summary) {
      return new Map<string, { total_return: number; volatility: number }>();
    }

    return new Map<string, { total_return: number; volatility: number }>(
      Object.entries(summary).map(([symbol, value]) => {
        const metrics = value as { total_return?: number; volatility?: number };
        return [
          symbol,
          {
            total_return: metrics.total_return ?? 0,
            volatility: metrics.volatility ?? 0,
          },
        ];
      })
    );
  }, [analysis]);

  const buildTemplateWeights = useCallback(
    (template: WeightTemplate): number[] => {
      if (symbols.length === 0) {
        return [];
      }

      const hasMetrics = symbols.some((symbol) => returnsSummaryMap.has(symbol));
      if (!hasMetrics) {
        const equalWeight = 1 / symbols.length;
        return symbols.map(() => equalWeight);
      }

      const aggressiveRaw = symbols.map((symbol) => {
        const metrics = returnsSummaryMap.get(symbol);
        return metrics ? metrics.total_return : 0;
      });
      const minAggressive = Math.min(...aggressiveRaw);
      const aggressiveScores = aggressiveRaw.map((value) => value - minAggressive + 1);

      const defensiveScores = symbols.map((symbol) => {
        const metrics = returnsSummaryMap.get(symbol);
        const volatility = metrics?.volatility ?? 2;
        return 1 / (volatility + 0.5);
      });

      if (template === 'aggressive') {
        return normalizeWeightScores(aggressiveScores);
      }

      if (template === 'defensive') {
        return normalizeWeightScores(defensiveScores);
      }

      const aggressiveWeights = normalizeWeightScores(aggressiveScores);
      const defensiveWeights = normalizeWeightScores(defensiveScores);
      const balancedScores = aggressiveWeights.map(
        (value, index) => value * 0.45 + defensiveWeights[index] * 0.55
      );
      return normalizeWeightScores(balancedScores);
    },
    [symbols, returnsSummaryMap]
  );

  const applyNormalizedWeights = useCallback(
    (weights: number[]) => {
      if (weights.length !== symbols.length || weights.length === 0) {
        return;
      }

      setWeightMode('custom');
      setCustomWeightInputs(
        symbols.reduce<Record<string, string>>((accumulator, symbol, index) => {
          accumulator[symbol] = (weights[index] * 100).toFixed(2);
          return accumulator;
        }, {})
      );
    },
    [symbols]
  );

  const handleApplyTemplate = useCallback(
    (template: WeightTemplate) => {
      const weights = buildTemplateWeights(template);
      if (weights.length !== symbols.length || weights.length === 0) {
        return;
      }

      applyNormalizedWeights(weights);
    },
    [buildTemplateWeights, symbols, applyNormalizedWeights]
  );

  const handleApplySavedPreset = useCallback(
    (preset: WeightPreset) => {
      if (symbols.length === 0) {
        return;
      }

      const compatibility = getPresetCompatibility(symbols, preset);
      if (compatibility.matchedSymbols === 0) {
        setPresetFeedback({
          type: 'error',
          message: `预设「${preset.name}」与当前股票池无重叠标的，无法应用。`,
        });
        return;
      }

      const presetWeights = symbols.map((symbol) => preset.weights[symbol] ?? 0);
      const normalized = normalizeWeightScores(presetWeights);
      applyNormalizedWeights(normalized);

      if (compatibility.coverage < 1) {
        setPresetFeedback({
          type: 'info',
          message: `已应用「${preset.name}」：覆盖 ${compatibility.matchedSymbols}/${symbols.length} 个标的，其余权重自动归一化。`,
        });
        return;
      }

      setPresetFeedback({
        type: 'success',
        message: `已应用预设「${preset.name}」。`,
      });
    },
    [symbols, applyNormalizedWeights]
  );

  const handleDeleteSavedPreset = useCallback(
    (presetId: string) => {
      const preset = savedWeightPresets.find((item) => item.id === presetId);
      setSavedWeightPresets((previous) => previous.filter((item) => item.id !== presetId));
      if (editingPresetId === presetId) {
        setEditingPresetId(null);
        setEditingPresetName('');
      }
      if (preset) {
        setPresetFeedback({ type: 'info', message: `已删除预设「${preset.name}」。` });
      }
    },
    [editingPresetId, savedWeightPresets]
  );

  const handleMoveSavedPreset = useCallback((presetId: string, direction: 'up' | 'down') => {
    setSavedWeightPresets((previous) => {
      const index = previous.findIndex((preset) => preset.id === presetId);
      if (index < 0) {
        return previous;
      }

      const targetIndex = direction === 'up' ? index - 1 : index + 1;
      if (targetIndex < 0 || targetIndex >= previous.length) {
        return previous;
      }

      const next = [...previous];
      const [moved] = next.splice(index, 1);
      next.splice(targetIndex, 0, moved);
      return next;
    });
  }, []);

  const handleStartRenamePreset = useCallback((preset: WeightPreset) => {
    setEditingPresetId(preset.id);
    setEditingPresetName(preset.name);
  }, []);

  const handleCancelRenamePreset = useCallback(() => {
    setEditingPresetId(null);
    setEditingPresetName('');
  }, []);

  const handleConfirmRenamePreset = useCallback(
    (presetId: string) => {
      const nextName = editingPresetName.trim().slice(0, MAX_PRESET_NAME_LENGTH);
      if (!nextName) {
        setPresetFeedback({ type: 'error', message: '预设名称不能为空。' });
        return;
      }

      const hasDuplicateName = savedWeightPresets.some(
        (preset) =>
          preset.id !== presetId && normalizePresetName(preset.name) === normalizePresetName(nextName)
      );
      if (hasDuplicateName) {
        setPresetFeedback({ type: 'error', message: `已存在同名预设「${nextName}」，请使用其他名称。` });
        return;
      }

      setSavedWeightPresets((previous) =>
        previous.map((preset) =>
          preset.id === presetId
            ? {
                ...preset,
                name: nextName,
              }
            : preset
        )
      );
      setEditingPresetId(null);
      setEditingPresetName('');
      setPresetFeedback({ type: 'success', message: `预设已重命名为「${nextName}」。` });
    },
    [editingPresetName, savedWeightPresets]
  );

  const handleExportPresets = useCallback(() => {
    if (typeof window === 'undefined' || savedWeightPresets.length === 0) {
      return;
    }

    const payload = JSON.stringify(savedWeightPresets, null, 2);
    const blob = new Blob([payload], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');

    anchor.href = url;
    anchor.download = `portfolio-weight-presets-${timestamp}.json`;
    anchor.click();

    window.URL.revokeObjectURL(url);
    setPresetFeedback({ type: 'success', message: `已导出 ${savedWeightPresets.length} 个预设。` });
  }, [savedWeightPresets]);

  const handleTriggerImportPresets = useCallback(() => {
    setPresetFeedback(null);
    importPresetsInputRef.current?.click();
  }, []);

  const handleImportPresetFile = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      event.target.value = '';

      if (!file) {
        return;
      }

      try {
        const content = await file.text();
        const parsed = JSON.parse(content);
        const imported = parseWeightPresets(parsed);

        if (imported.length === 0) {
          setPresetFeedback({ type: 'error', message: '导入失败：文件中没有可用的预设数据。' });
          return;
        }

        if (presetImportMode === 'replace') {
          const nextPresets = imported.slice(0, MAX_WEIGHT_PRESETS);
          setSavedWeightPresets(nextPresets);
          setPresetFeedback({
            type: 'success',
            message: `导入完成：已覆盖为 ${nextPresets.length} 个预设。`,
          });
          return;
        }

        const mergedByName = new Map<string, WeightPreset>();
        for (const preset of savedWeightPresets) {
          mergedByName.set(normalizePresetName(preset.name), preset);
        }

        let overwrittenCount = 0;
        for (const preset of imported) {
          const key = normalizePresetName(preset.name);
          if (mergedByName.has(key)) {
            overwrittenCount += 1;
          }
          mergedByName.set(key, preset);
        }

        const droppedCount = Math.max(0, mergedByName.size - MAX_WEIGHT_PRESETS);
        const nextPresets = Array.from(mergedByName.values())
          .sort((left, right) => right.createdAt - left.createdAt)
          .slice(0, MAX_WEIGHT_PRESETS);

        setSavedWeightPresets(nextPresets);

        let message = `导入完成：新增/更新 ${imported.length} 个预设。`;
        if (overwrittenCount > 0) {
          message += ` 覆盖同名 ${overwrittenCount} 个。`;
        }
        if (droppedCount > 0) {
          message += ` 超出上限已截断 ${droppedCount} 个。`;
        }

        setPresetFeedback({ type: 'success', message });
      } catch {
        setPresetFeedback({ type: 'error', message: '导入失败：请确认 JSON 格式正确。' });
      }
    },
    [presetImportMode, savedWeightPresets]
  );

  const weightConfig = useMemo(() => {
    if (symbols.length === 0) {
      return {
        isValid: true,
        errorMessage: '',
        helperMessage: '',
        totalInputPercent: 0,
        weightsForRequest: [] as number[],
      };
    }

    if (weightMode === 'equal') {
      const equalWeight = 1 / symbols.length;
      return {
        isValid: true,
        errorMessage: '',
        helperMessage: `当前等权配置：每只股票 ${(equalWeight * 100).toFixed(2)}%`,
        totalInputPercent: 100,
        weightsForRequest: symbols.map(() => equalWeight),
      };
    }

    const parsedWeights = symbols.map((symbol) => {
      const rawValue = customWeightInputs[symbol];
      if (rawValue === undefined || rawValue.trim() === '') {
        return Number.NaN;
      }
      return Number(rawValue);
    });

    if (parsedWeights.some((weight) => !Number.isFinite(weight))) {
      return {
        isValid: false,
        errorMessage: '存在空值或非法数字，请输入有效权重。',
        helperMessage: '',
        totalInputPercent: 0,
        weightsForRequest: [] as number[],
      };
    }

    if (parsedWeights.some((weight) => weight < 0)) {
      return {
        isValid: false,
        errorMessage: '权重不能为负数。',
        helperMessage: '',
        totalInputPercent: 0,
        weightsForRequest: [] as number[],
      };
    }

    const totalInputPercent = parsedWeights.reduce((sum, weight) => sum + weight, 0);
    if (totalInputPercent <= 0) {
      return {
        isValid: false,
        errorMessage: '权重总和必须大于 0。',
        helperMessage: '',
        totalInputPercent,
        weightsForRequest: [] as number[],
      };
    }

    const weightsForRequest = parsedWeights.map((weight) => weight / totalInputPercent);
    const helperMessage =
      Math.abs(totalInputPercent - 100) > 0.01
        ? `当前输入合计 ${totalInputPercent.toFixed(2)}%，请求时将自动归一化为 100%。`
        : '权重合计 100%，将按该配比分析。';

    return {
      isValid: true,
      errorMessage: '',
      helperMessage,
      totalInputPercent,
      weightsForRequest,
    };
  }, [weightMode, symbols, customWeightInputs]);

  const constraintConfig = useMemo(() => {
    const maxSingleWeight = clamp(rebalanceConstraints.maxSingleWeight, 0.1, 0.9);
    const maxTop2Weight = clamp(rebalanceConstraints.maxTop2Weight, 0.2, 1);
    const maxTurnover = clamp(rebalanceConstraints.maxTurnover, 0, 1);

    if (maxTop2Weight + 1e-6 < maxSingleWeight) {
      return {
        isValid: false,
        errorMessage: '前两大持仓上限不能低于单票上限。',
        constraintsForRequest: undefined,
      };
    }

    if (symbols.length > 0 && maxSingleWeight * symbols.length < 1 - 1e-6) {
      return {
        isValid: false,
        errorMessage: `当前股票数为 ${symbols.length}，单票上限至少需 ${(100 / symbols.length).toFixed(2)}%。`,
        constraintsForRequest: undefined,
      };
    }

    return {
      isValid: true,
      errorMessage: '',
      constraintsForRequest: {
        maxSingleWeight,
        maxTop2Weight,
        maxTurnover,
        riskProfile: rebalanceConstraints.riskProfile,
      } satisfies PortfolioRebalanceConstraints,
    };
  }, [rebalanceConstraints, symbols.length]);

  const handleConstraintNumberChange = useCallback(
    (field: 'maxSingleWeight' | 'maxTop2Weight' | 'maxTurnover', rawValue: string) => {
      const parsed = Number(rawValue);
      if (!Number.isFinite(parsed)) {
        return;
      }

      setRebalanceConstraints((previous) => ({
        ...previous,
        [field]:
          field === 'maxTurnover'
            ? clamp(parsed, 0, 1)
            : field === 'maxTop2Weight'
              ? clamp(parsed, 0.2, 1)
              : clamp(parsed, 0.1, 0.9),
      }));
    },
    []
  );

  const handleSaveWeightPreset = useCallback(() => {
    if (!weightConfig.isValid || weightConfig.weightsForRequest.length !== symbols.length || symbols.length === 0) {
      return;
    }

    const presetWeights = symbols.reduce<Record<string, number>>((accumulator, symbol, index) => {
      accumulator[symbol] = weightConfig.weightsForRequest[index];
      return accumulator;
    }, {});

    let finalName = presetNameInput.trim().slice(0, MAX_PRESET_NAME_LENGTH);
    if (!finalName) {
      let index = savedWeightPresets.length + 1;
      finalName = `方案 ${index}`;
      while (
        savedWeightPresets.some(
          (preset) => normalizePresetName(preset.name) === normalizePresetName(finalName)
        )
      ) {
        index += 1;
        finalName = `方案 ${index}`;
      }
    }

    const existingPreset = savedWeightPresets.find(
      (preset) => normalizePresetName(preset.name) === normalizePresetName(finalName)
    );

    if (existingPreset) {
      const updatedPreset: WeightPreset = {
        ...existingPreset,
        name: finalName,
        createdAt: Date.now(),
        weights: presetWeights,
      };
      const nextPresets = [
        updatedPreset,
        ...savedWeightPresets.filter((preset) => preset.id !== existingPreset.id),
      ].slice(0, MAX_WEIGHT_PRESETS);
      setSavedWeightPresets(nextPresets);
      setPresetFeedback({ type: 'info', message: `名称已存在，已覆盖预设「${finalName}」。` });
    } else {
      const preset: WeightPreset = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        name: finalName,
        createdAt: Date.now(),
        weights: presetWeights,
      };

      setSavedWeightPresets([preset, ...savedWeightPresets].slice(0, MAX_WEIGHT_PRESETS));
      setPresetFeedback({ type: 'success', message: `已保存预设「${finalName}」。` });
    }

    setPresetNameInput('');
  }, [weightConfig.isValid, weightConfig.weightsForRequest, symbols, presetNameInput, savedWeightPresets]);

  const effectiveWeights = useMemo(() => {
    if (!weightConfig.isValid || weightConfig.weightsForRequest.length !== symbols.length) {
      return [] as Array<{ symbol: string; weight: number }>;
    }

    return symbols
      .map((symbol, index) => ({
        symbol,
        weight: weightConfig.weightsForRequest[index] ?? 0,
      }))
      .sort((left, right) => right.weight - left.weight);
  }, [weightConfig.isValid, weightConfig.weightsForRequest, symbols]);

  const effectiveWeightStats = useMemo(() => {
    const topOne = effectiveWeights[0]?.weight ?? 0;
    const topTwo = topOne + (effectiveWeights[1]?.weight ?? 0);
    const hhi = effectiveWeights.reduce((sum, item) => sum + item.weight * item.weight, 0);

    return { topOne, topTwo, hhi };
  }, [effectiveWeights]);

  const weightsForRequest = weightConfig.isValid ? weightConfig.weightsForRequest : undefined;
  const constraintsForRequest = constraintConfig.constraintsForRequest;
  const isAnalysisReady =
    symbols.length >= 2 && weightConfig.isValid && constraintConfig.isValid && Boolean(constraintsForRequest);
  const weightSignature =
    weightMode === 'equal'
      ? 'equal'
      : weightConfig.isValid
        ? weightConfig.weightsForRequest.map((weight) => weight.toFixed(4)).join(',')
        : 'invalid';
  const constraintsSignature = constraintsForRequest
    ? `${constraintsForRequest.maxSingleWeight.toFixed(3)}|${constraintsForRequest.maxTop2Weight.toFixed(3)}|${constraintsForRequest.maxTurnover.toFixed(3)}|${constraintsForRequest.riskProfile}`
    : 'invalid';

  const analysisRequestKey = useMemo(
    () =>
      `${symbolFingerprint}|${period}|${clusterThreshold.toFixed(2)}|${weightSignature}|${constraintsSignature}|${enableBacktestHint}`,
    [
      symbolFingerprint,
      period,
      clusterThreshold,
      weightSignature,
      constraintsSignature,
      enableBacktestHint,
    ]
  );

  const periodLabel = useMemo(
    () => PERIOD_OPTIONS.find((option) => option.value === period)?.label ?? period,
    [period]
  );

  const quickCheckQuery = useQuickPortfolioCheck({
    symbols: isAnalysisReady ? symbols : [],
    period,
    clusterThreshold,
    weights: isAnalysisReady ? weightsForRequest : undefined,
    constraints: constraintsForRequest,
    enableBacktestHint,
  });

  const handleAnalyze = useCallback(async () => {
    if (!isAnalysisReady || !weightsForRequest || !constraintsForRequest) {
      return;
    }

    try {
      const result = await portfolioMutation.mutateAsync({
        symbols,
        period,
        clusterThreshold,
        weights: weightsForRequest,
        constraints: constraintsForRequest,
        enableBacktestHint,
      });
      setAnalysis(result);
      setLatestAnalysisRequestKey(analysisRequestKey);
    } catch (error) {
      logger.error('Portfolio analysis failed', error);
    }
  }, [
    symbols,
    period,
    clusterThreshold,
    weightsForRequest,
    constraintsForRequest,
    enableBacktestHint,
    isAnalysisReady,
    analysisRequestKey,
    portfolioMutation,
  ]);

  const handleRefreshQuickCheck = useCallback(() => {
    if (!isAnalysisReady) {
      return;
    }
    void quickCheckQuery.refetch();
  }, [isAnalysisReady, quickCheckQuery]);

  const handleRefreshAll = useCallback(() => {
    if (!isAnalysisReady) {
      return;
    }
    void quickCheckQuery.refetch();
    void handleAnalyze();
  }, [isAnalysisReady, quickCheckQuery, handleAnalyze]);

  const handleFillEqualWeights = useCallback(() => {
    if (symbols.length === 0) {
      return;
    }

    const equalPercent = 100 / symbols.length;
    setCustomWeightInputs(
      symbols.reduce<Record<string, string>>((accumulator, symbol) => {
        accumulator[symbol] = equalPercent.toFixed(2);
        return accumulator;
      }, {})
    );
  }, [symbols]);

  const handleWeightInputChange = useCallback((symbol: string, rawValue: string) => {
    setCustomWeightInputs((previous) => ({
      ...previous,
      [symbol]: rawValue,
    }));
  }, []);

  useEffect(() => {
    if (symbols.length < 2) {
      setAnalysis(null);
      setLatestAnalysisRequestKey('');
      return;
    }

    if (!isAnalysisReady || portfolioMutation.isPending) {
      return;
    }

    if (latestAnalysisRequestKey !== analysisRequestKey) {
      void handleAnalyze();
    }
  }, [
    symbols.length,
    isAnalysisReady,
    analysisRequestKey,
    latestAnalysisRequestKey,
    portfolioMutation.isPending,
    handleAnalyze,
  ]);

  const sortedReturns = useMemo(() => {
    if (!analysis?.correlation.returns_summary) return [];

    return Object.entries(analysis.correlation.returns_summary)
      .map(([symbol, data]) => {
        const metrics = data as { total_return?: number; volatility?: number };
        return {
          symbol,
          total_return: metrics.total_return ?? 0,
          volatility: metrics.volatility ?? 0,
        };
      })
      .sort((a, b) => b.total_return - a.total_return);
  }, [analysis]);

  const rebalanceSuggestions = useMemo(() => {
    if (!analysis || effectiveWeights.length === 0) {
      return [] as RebalanceSuggestionItem[];
    }

    const serverSuggestions = analysis.rebalance_suggestions ?? [];
    if (serverSuggestions.length > 0) {
      return serverSuggestions
        .map<RebalanceSuggestionItem>((item) => ({
          symbol: item.symbol,
          currentWeight: item.current_weight,
          targetWeight: item.target_weight,
          delta: item.delta_weight,
          action: item.action,
          volatility: item.volatility ?? 0,
          totalReturn: item.total_return ?? 0,
          confidence: item.confidence,
          rationale: item.rationale,
          source: 'server',
        }))
        .sort((left, right) => Math.abs(right.delta) - Math.abs(left.delta));
    }

    const symbolsInAnalysis = analysis.correlation.symbols;
    if (symbolsInAnalysis.length === 0) {
      return [] as RebalanceSuggestionItem[];
    }

    const currentWeightMap = new Map<string, number>(
      effectiveWeights.map((item) => [item.symbol, item.weight])
    );

    const rawScores = symbolsInAnalysis.map((symbol, index) => {
      const metrics = returnsSummaryMap.get(symbol);
      const volatility = Math.max(metrics?.volatility ?? 2, 0.1);
      const row = analysis.correlation.matrix[index] ?? [];
      const avgAbsCorr =
        row.length > 1
          ? row.reduce((sum, value, columnIndex) => {
              if (columnIndex === index) {
                return sum;
              }
              return sum + Math.abs(value);
            }, 0) /
            (row.length - 1)
          : 0;

      const momentumScore = metrics ? clamp((metrics.total_return + 20) / 40, 0.3, 1.4) : 1;
      const stabilityScore = 1 / (volatility + 0.6);
      const decorrelationScore = 1 - clamp(avgAbsCorr, 0, 0.95);

      return Math.max(0.01, stabilityScore * Math.pow(decorrelationScore, 0.8) * momentumScore);
    });

    const targetWeights = normalizeWeightScores(rawScores);

    return symbolsInAnalysis
      .map<RebalanceSuggestionItem>((symbol, index) => {
        const currentWeight = currentWeightMap.get(symbol) ?? 0;
        const targetWeight = targetWeights[index] ?? 0;
        const delta = targetWeight - currentWeight;
        const action: RebalanceAction =
          delta > 0.03 ? 'increase' : delta < -0.03 ? 'decrease' : 'hold';

        const metrics = returnsSummaryMap.get(symbol);

        return {
          symbol,
          currentWeight,
          targetWeight,
          delta,
          action,
          volatility: metrics?.volatility ?? 0,
          totalReturn: metrics?.total_return ?? 0,
          confidence: undefined,
          rationale: undefined,
          source: 'client',
        };
      })
      .sort((left, right) => Math.abs(right.delta) - Math.abs(left.delta));
  }, [analysis, effectiveWeights, returnsSummaryMap]);

  const rebalanceSummary = useMemo(() => {
    if (rebalanceSuggestions.length === 0) {
      return null;
    }

    const serverTurnover = analysis?.recommended_turnover;
    const turnover =
      typeof serverTurnover === 'number' && Number.isFinite(serverTurnover)
        ? serverTurnover
        : rebalanceSuggestions.reduce((sum, item) => sum + Math.abs(item.delta), 0) / 2;
    const increaseCount = rebalanceSuggestions.filter((item) => item.action === 'increase').length;
    const decreaseCount = rebalanceSuggestions.filter((item) => item.action === 'decrease').length;

    return {
      turnover,
      increaseCount,
      decreaseCount,
      source: rebalanceSuggestions[0]?.source ?? 'client',
    };
  }, [analysis, rebalanceSuggestions]);

  const analysisExtended = analysis as PortfolioAnalysisExtended | null;
  const constraintViolations = analysisExtended?.constraint_violations ?? [];
  const backtestPayloadHint = analysisExtended?.backtest_payload_hint ?? null;

  const hintedBacktestSymbols = useMemo(() => {
    if (!backtestPayloadHint?.requests?.length) {
      return [] as string[];
    }

    return Array.from(
      new Set(backtestPayloadHint.requests.map((requestItem) => requestItem.symbol).filter(Boolean))
    );
  }, [backtestPayloadHint]);

  const backtestHistoryQueries = useQueries({
    queries: hintedBacktestSymbols.map((symbol) => ({
      queryKey: [...BACKTEST_KEY, 'history', symbol, 1],
      queryFn: () => getBacktestHistory(symbol, 1),
      enabled: symbol.length > 0,
      staleTime: 30_000,
    })),
  });

  const isBacktestHistoryLoading = backtestHistoryQueries.some((query) => query.isFetching);

  const backtestDetailQuery = useQuery({
    queryKey: [
      ...BACKTEST_KEY,
      'detail',
      selectedBacktestRecord?.symbol ?? '',
      selectedBacktestRecord?.recordId ?? 0,
    ],
    queryFn: async () => {
      if (!selectedBacktestRecord) {
        return null as BacktestDetailResponse | null;
      }
      return getBacktestDetail(selectedBacktestRecord.symbol, selectedBacktestRecord.recordId);
    },
    enabled: Boolean(selectedBacktestRecord),
    staleTime: 30_000,
  });

  const selectedBacktestDetail = (backtestDetailQuery.data ?? null) as BacktestDetailResponse | null;

  const latestBacktestHistoryMap = useMemo(
    () =>
      hintedBacktestSymbols.reduce<Record<string, BacktestHistoryItem>>((accumulator, symbol, index) => {
        const response = backtestHistoryQueries[index]?.data as
          | { history?: BacktestHistoryItem[] }
          | undefined;
        const latestRecord = response?.history?.[0];
        if (latestRecord) {
          accumulator[symbol] = latestRecord;
        }
        return accumulator;
      }, {}),
    [hintedBacktestSymbols, backtestHistoryQueries]
  );

  const refreshBacktestHistory = useCallback(() => {
    for (const symbol of hintedBacktestSymbols) {
      void queryClient.invalidateQueries({ queryKey: [...BACKTEST_KEY, 'history', symbol] });
    }
  }, [hintedBacktestSymbols, queryClient]);

  useEffect(() => {
    setBacktestExecutionMap({});
    setBacktestFeedback(null);
    setIsRunningAllBacktests(false);
    setSelectedBacktestRecord(null);
  }, [backtestPayloadHint?.generated_at, backtestPayloadHint?.strategy_name]);

  const buildBacktestPayload = useCallback(
    (requestItem: BacktestPayloadHintItem['requests'][number]): BacktestRunRequest => {
      const signals = requestItem.signals
        .map((item) => {
          const confidence = clamp(item.confidence, 0, 1);
          return {
            date: normalizeBacktestDate(item.date),
            signal: normalizeBacktestSignal(item.signal, confidence),
            confidence: Math.round(confidence * 100),
            source: item.source,
          };
        })
        .filter((item) => item.date.length > 0);

      const useHistoricalSignals = requestItem.use_historical_signals || signals.length === 0;

      return {
        symbol: requestItem.symbol,
        signals: signals.length > 0 ? signals : undefined,
        initial_capital: requestItem.initial_capital,
        holding_days: requestItem.holding_days,
        stop_loss_pct: requestItem.stop_loss_pct,
        take_profit_pct: requestItem.take_profit_pct,
        use_historical_signals: useHistoricalSignals,
        days_back: requestItem.days_back,
      };
    },
    []
  );

  const executeBacktestFromHint = useCallback(
    async (
      requestItem: BacktestPayloadHintItem['requests'][number],
      options: { silent?: boolean } = {}
    ): Promise<boolean> => {
      setBacktestExecutionMap((previous) => ({
        ...previous,
        [requestItem.symbol]: {
          status: 'running',
          message: '回测执行中...',
        },
      }));

      try {
        const payload = buildBacktestPayload(requestItem);
        const response = await backtestMutation.mutateAsync(payload);
        const result = response.result;
        const finishedAt = new Date().toISOString();

        setBacktestExecutionMap((previous) => ({
          ...previous,
          [requestItem.symbol]: {
            status: 'success',
            finishedAt,
            totalReturnPct: result.total_return_pct,
            winRate: result.win_rate,
            totalTrades: result.total_trades,
            message: `收益 ${result.total_return_pct.toFixed(2)}%，胜率 ${(result.win_rate * 100).toFixed(1)}%`,
          },
        }));

        if (!options.silent) {
          setBacktestFeedback({
            type: 'success',
            message: `${requestItem.symbol} 回测完成：收益 ${result.total_return_pct.toFixed(2)}%，交易 ${result.total_trades} 笔。`,
          });
        }

        void queryClient.invalidateQueries({
          queryKey: [...BACKTEST_KEY, 'history', requestItem.symbol],
        });

        return true;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : '回测执行失败，请稍后重试。';

        setBacktestExecutionMap((previous) => ({
          ...previous,
          [requestItem.symbol]: {
            status: 'error',
            finishedAt: new Date().toISOString(),
            message: errorMessage,
          },
        }));

        if (!options.silent) {
          setBacktestFeedback({
            type: 'error',
            message: `${requestItem.symbol} 回测失败：${errorMessage}`,
          });
        }

        return false;
      }
    },
    [backtestMutation, buildBacktestPayload, queryClient]
  );

  const handleRunAllHintBacktests = useCallback(async () => {
    if (!backtestPayloadHint?.requests?.length || isRunningAllBacktests) {
      return;
    }

    setIsRunningAllBacktests(true);
    const summary: BacktestExecutionSummary = { success: 0, failed: 0 };

    for (const requestItem of backtestPayloadHint.requests) {
      const success = await executeBacktestFromHint(requestItem, { silent: true });
      if (success) {
        summary.success += 1;
      } else {
        summary.failed += 1;
      }
    }

    setIsRunningAllBacktests(false);
    refreshBacktestHistory();
    setBacktestFeedback({
      type: summary.failed === 0 ? 'success' : summary.success === 0 ? 'error' : 'info',
      message: `批量回测完成：成功 ${summary.success}，失败 ${summary.failed}。`,
    });
  }, [
    backtestPayloadHint,
    executeBacktestFromHint,
    isRunningAllBacktests,
    refreshBacktestHistory,
  ]);

  const handleApplyRebalanceSuggestion = useCallback(() => {
    if (rebalanceSuggestions.length === 0 || symbols.length === 0) {
      return;
    }

    const targetWeightMap = new Map<string, number>(
      rebalanceSuggestions.map((item) => [item.symbol, item.targetWeight])
    );
    const weights = symbols.map((symbol) => targetWeightMap.get(symbol) ?? 0);
    const normalized = normalizeWeightScores(weights);

    applyNormalizedWeights(normalized);
    setPresetFeedback({
      type: 'info',
      message: '已应用智能再平衡建议，请刷新分析查看新权重下结果。',
    });
  }, [rebalanceSuggestions, symbols, applyNormalizedWeights]);

  const showInitialAnalysisLoading = portfolioMutation.isPending && !analysis;
  const showInitialAnalysisError = !analysis && Boolean(portfolioMutation.error);
  const hasPendingRefresh =
    portfolioMutation.isPending &&
    Boolean(analysis) &&
    latestAnalysisRequestKey !== analysisRequestKey;

  return (
    <PageLayout
      title="Portfolio Analysis"
      subtitle={`${stocks.length} stocks · ${periodLabel} · 阈值 ≥ ${clusterThreshold.toFixed(2)} · ${weightMode === 'equal' ? '等权' : '自定义权重'} · ${rebalanceConstraints.riskProfile} 风格`}
      icon={PieChart}
      iconColor="text-cyan-400"
      iconBgColor="bg-cyan-500/10"
      variant="wide"
      actions={[
        {
          label: quickCheckQuery.isFetching ? '体检中...' : '刷新体检',
          icon: RefreshCw,
          onClick: handleRefreshQuickCheck,
          loading: quickCheckQuery.isFetching,
          disabled: !isAnalysisReady,
          variant: 'secondary',
        },
        {
          label: portfolioMutation.isPending ? '分析中...' : '刷新分析',
          icon: RefreshCw,
          onClick: handleRefreshAll,
          loading: portfolioMutation.isPending,
          disabled: !isAnalysisReady,
          variant: 'primary',
        },
      ]}
    >
      {stocks.length < 2 ? (
        <EmptyState
          icon={AlertTriangle}
          title="需要至少 2 只股票来进行组合分析"
          description="请在 Dashboard 添加更多股票到关注列表"
        />
      ) : (
        <div className="space-y-6">
          {/* 参数设置 */}
          <div className="bg-surface-overlay/30 rounded-xl p-4 border border-border-strong">
            <h3 className="text-base font-bold text-white mb-3">Analysis Settings</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label className="block">
                <span className="block text-xs text-stone-400 mb-2">历史周期</span>
                <select
                  value={period}
                  onChange={(event) => setPeriod(event.target.value as PortfolioPeriod)}
                  className="w-full h-11 px-3 rounded-lg bg-surface-raised border border-border-strong text-stone-200 focus:outline-none focus:ring-2 focus:ring-cyan-500/60"
                >
                  {PERIOD_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="block text-xs text-stone-400 mb-2">风险聚类阈值</span>
                <select
                  value={clusterThreshold}
                  onChange={(event) => setClusterThreshold(Number(event.target.value))}
                  className="w-full h-11 px-3 rounded-lg bg-surface-raised border border-border-strong text-stone-200 focus:outline-none focus:ring-2 focus:ring-cyan-500/60"
                >
                  {CLUSTER_THRESHOLD_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              <label className="block">
                <span className="block text-xs text-stone-400 mb-2">单票上限（%）</span>
                <input
                  type="number"
                  min="10"
                  max="90"
                  step="1"
                  value={(rebalanceConstraints.maxSingleWeight * 100).toFixed(0)}
                  onChange={(event) =>
                    handleConstraintNumberChange('maxSingleWeight', String(Number(event.target.value) / 100))
                  }
                  className="w-full h-11 px-3 rounded-lg bg-surface-raised border border-border-strong text-stone-200 focus:outline-none focus:ring-2 focus:ring-cyan-500/60"
                />
              </label>

              <label className="block">
                <span className="block text-xs text-stone-400 mb-2">前两大上限（%）</span>
                <input
                  type="number"
                  min="20"
                  max="100"
                  step="1"
                  value={(rebalanceConstraints.maxTop2Weight * 100).toFixed(0)}
                  onChange={(event) =>
                    handleConstraintNumberChange('maxTop2Weight', String(Number(event.target.value) / 100))
                  }
                  className="w-full h-11 px-3 rounded-lg bg-surface-raised border border-border-strong text-stone-200 focus:outline-none focus:ring-2 focus:ring-cyan-500/60"
                />
              </label>

              <label className="block">
                <span className="block text-xs text-stone-400 mb-2">最大换手（%）</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  value={(rebalanceConstraints.maxTurnover * 100).toFixed(0)}
                  onChange={(event) =>
                    handleConstraintNumberChange('maxTurnover', String(Number(event.target.value) / 100))
                  }
                  className="w-full h-11 px-3 rounded-lg bg-surface-raised border border-border-strong text-stone-200 focus:outline-none focus:ring-2 focus:ring-cyan-500/60"
                />
              </label>

              <label className="block">
                <span className="block text-xs text-stone-400 mb-2">风险风格</span>
                <select
                  value={rebalanceConstraints.riskProfile}
                  onChange={(event) =>
                    setRebalanceConstraints((previous) => ({
                      ...previous,
                      riskProfile: event.target.value as PortfolioRiskProfile,
                    }))
                  }
                  className="w-full h-11 px-3 rounded-lg bg-surface-raised border border-border-strong text-stone-200 focus:outline-none focus:ring-2 focus:ring-cyan-500/60"
                >
                  {RISK_PROFILE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="mt-2 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border-strong bg-surface-raised/40 px-3 py-2">
              <div>
                <p className="text-xs text-stone-300">生成回测参数提示</p>
                <p className="text-[11px] text-stone-500">分析结果中会附带 backtest 请求参数建议。</p>
              </div>
              <button
                type="button"
                onClick={() => setEnableBacktestHint((previous) => !previous)}
                className={`px-3 py-1.5 rounded-md text-xs ${
                  enableBacktestHint
                    ? 'bg-cyan-700 text-white'
                    : 'bg-surface-overlay text-stone-300 hover:bg-surface-muted'
                }`}
              >
                {enableBacktestHint ? '已启用' : '未启用'}
              </button>
            </div>

            {constraintConfig.errorMessage && (
              <p className="text-xs text-red-400">{constraintConfig.errorMessage}</p>
            )}

            <div className="mt-4 border-t border-border-strong/60 pt-4 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className="text-xs text-stone-400">仓位模式</span>
                <div className="inline-flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setWeightMode('equal')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      weightMode === 'equal'
                        ? 'bg-cyan-600 text-white'
                        : 'bg-surface-overlay text-stone-300 hover:bg-surface-muted'
                    }`}
                  >
                    等权
                  </button>
                  <button
                    type="button"
                    onClick={() => setWeightMode('custom')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      weightMode === 'custom'
                        ? 'bg-cyan-600 text-white'
                        : 'bg-surface-overlay text-stone-300 hover:bg-surface-muted'
                    }`}
                  >
                    自定义权重
                  </button>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs text-stone-400">场景模板</span>
                  {WEIGHT_TEMPLATE_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => handleApplyTemplate(option.value)}
                      className="px-2.5 py-1.5 text-xs rounded-lg bg-surface-overlay text-stone-300 hover:bg-surface-muted"
                    >
                      {option.label}
                    </button>
                  ))}
                  {!analysis && (
                    <span className="text-xs text-stone-500">（当前无收益数据，模板将按等权近似）</span>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs text-stone-400">保存预设</span>
                  <input
                    type="text"
                    value={presetNameInput}
                    onChange={(event) => setPresetNameInput(event.target.value)}
                    placeholder="输入预设名称"
                    className="h-8 px-2.5 rounded-lg border border-border-strong bg-surface-raised text-xs text-stone-100 outline-none focus:ring-2 focus:ring-cyan-500/50"
                  />
                  <button
                    type="button"
                    onClick={handleSaveWeightPreset}
                    disabled={!weightConfig.isValid || symbols.length < 2}
                    className="px-2.5 py-1.5 text-xs rounded-lg bg-cyan-700 text-white hover:bg-cyan-600 disabled:opacity-50"
                  >
                    保存当前权重
                  </button>
                  <button
                    type="button"
                    onClick={handleTriggerImportPresets}
                    className="px-2.5 py-1.5 text-xs rounded-lg bg-surface-overlay text-stone-300 hover:bg-surface-muted"
                  >
                    导入预设
                  </button>
                  <button
                    type="button"
                    onClick={handleExportPresets}
                    disabled={savedWeightPresets.length === 0}
                    className="px-2.5 py-1.5 text-xs rounded-lg bg-surface-overlay text-stone-300 hover:bg-surface-muted disabled:opacity-50"
                  >
                    导出预设
                  </button>
                  <input
                    ref={importPresetsInputRef}
                    type="file"
                    accept="application/json"
                    className="hidden"
                    onChange={handleImportPresetFile}
                  />
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs text-stone-400">导入策略</span>
                  <button
                    type="button"
                    onClick={() => setPresetImportMode('merge')}
                    className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                      presetImportMode === 'merge'
                        ? 'bg-cyan-700 text-white'
                        : 'bg-surface-overlay text-stone-300 hover:bg-surface-muted'
                    }`}
                  >
                    合并（同名覆盖）
                  </button>
                  <button
                    type="button"
                    onClick={() => setPresetImportMode('replace')}
                    className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                      presetImportMode === 'replace'
                        ? 'bg-cyan-700 text-white'
                        : 'bg-surface-overlay text-stone-300 hover:bg-surface-muted'
                    }`}
                  >
                    覆盖全部
                  </button>
                  <span className="text-[11px] text-stone-500">最多保留 {MAX_WEIGHT_PRESETS} 个预设</span>
                </div>

                {presetFeedback && (
                  <p
                    className={`text-xs ${
                      presetFeedback.type === 'error'
                        ? 'text-red-400'
                        : presetFeedback.type === 'success'
                          ? 'text-emerald-400'
                          : 'text-cyan-300'
                    }`}
                  >
                    {presetFeedback.message}
                  </p>
                )}

                {savedWeightPresets.length > 0 ? (
                  <div className="space-y-2">
                    <span className="text-xs text-stone-400">已保存预设</span>
                    <div className="flex flex-col gap-2">
                      {savedWeightPresets.map((preset, index) => {
                        const compatibility = presetCompatibilityMap.get(preset.id);
                        const matchedSymbols = compatibility?.matchedSymbols ?? 0;
                        const coverage = compatibility?.coverage ?? 0;
                        const isApplicable = matchedSymbols > 0;

                        return (
                          <div
                            key={preset.id}
                            className="flex flex-wrap items-center justify-between gap-2 p-2 rounded-lg border border-border-strong bg-surface-raised/60"
                          >
                            {editingPresetId === preset.id ? (
                              <div className="flex items-center gap-2">
                                <input
                                  type="text"
                                  value={editingPresetName}
                                  onChange={(event) => setEditingPresetName(event.target.value)}
                                  className="h-8 px-2.5 rounded-lg border border-border-strong bg-surface-raised text-xs text-stone-100 outline-none focus:ring-2 focus:ring-cyan-500/50"
                                />
                                <button
                                  type="button"
                                  onClick={() => handleConfirmRenamePreset(preset.id)}
                                  className="px-2 py-1 text-xs rounded-md bg-cyan-700 text-white hover:bg-cyan-600"
                                >
                                  保存
                                </button>
                                <button
                                  type="button"
                                  onClick={handleCancelRenamePreset}
                                  className="px-2 py-1 text-xs rounded-md bg-surface-overlay text-stone-300 hover:bg-surface-muted"
                                >
                                  取消
                                </button>
                              </div>
                            ) : (
                              <div className="space-y-0.5">
                                <p className="text-xs text-stone-200 font-medium">{preset.name}</p>
                                <p className="text-[11px] text-stone-500">
                                  {new Date(preset.createdAt).toLocaleString('zh-CN', { hour12: false })}
                                </p>
                                <p
                                  className={`text-[11px] ${
                                    coverage === 1
                                      ? 'text-emerald-400'
                                      : isApplicable
                                        ? 'text-cyan-300'
                                        : 'text-yellow-400'
                                  }`}
                                >
                                  {coverage === 1
                                    ? `匹配当前股票池 ${matchedSymbols}/${symbols.length}`
                                    : isApplicable
                                      ? `部分匹配 ${matchedSymbols}/${symbols.length}，应用时将自动归一化`
                                      : '与当前股票池无重叠标的'}
                                </p>
                                {Boolean(compatibility?.extraSymbols.length) && (
                                  <p className="text-[11px] text-stone-500">
                                    预设含历史标的 {compatibility?.extraSymbols.length ?? 0} 个（当前未在股票池中）。
                                  </p>
                                )}
                              </div>
                            )}
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={() => handleApplySavedPreset(preset)}
                                disabled={!isApplicable}
                                className="px-2 py-1 text-xs rounded-md bg-surface-overlay text-stone-200 hover:bg-surface-muted disabled:opacity-40 disabled:cursor-not-allowed"
                              >
                                应用
                              </button>
                              <button
                                type="button"
                                onClick={() => handleStartRenamePreset(preset)}
                                className="px-2 py-1 text-xs rounded-md bg-surface-overlay text-stone-200 hover:bg-surface-muted"
                              >
                                重命名
                              </button>
                              <button
                                type="button"
                                onClick={() => handleMoveSavedPreset(preset.id, 'up')}
                                disabled={index === 0}
                                className="px-2 py-1 text-xs rounded-md bg-surface-overlay text-stone-200 hover:bg-surface-muted disabled:opacity-50"
                              >
                                上移
                              </button>
                              <button
                                type="button"
                                onClick={() => handleMoveSavedPreset(preset.id, 'down')}
                                disabled={index === savedWeightPresets.length - 1}
                                className="px-2 py-1 text-xs rounded-md bg-surface-overlay text-stone-200 hover:bg-surface-muted disabled:opacity-50"
                              >
                                下移
                              </button>
                              <button
                                type="button"
                                onClick={() => handleDeleteSavedPreset(preset.id)}
                                className="px-2 py-1 text-xs rounded-md bg-red-950/40 text-red-300 hover:bg-red-900/40"
                              >
                                删除
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-stone-500">暂无保存的预设，可将当前配置保存后复用。</p>
                )}
              </div>

              {weightMode === 'custom' && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs text-stone-500">
                      输入权重百分比，系统会自动归一化（无需严格等于 100%）。
                    </p>
                    <button
                      type="button"
                      onClick={handleFillEqualWeights}
                      className="px-2.5 py-1.5 text-xs rounded-lg bg-surface-overlay text-stone-300 hover:bg-surface-muted"
                    >
                      一键等权填充
                    </button>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {symbols.map((symbol) => (
                      <label key={symbol} className="block">
                        <span className="block text-xs text-stone-400 mb-1">{symbol}</span>
                        <div className="h-11 rounded-lg border border-border-strong bg-surface-raised px-3 flex items-center gap-2">
                          <input
                            type="number"
                            min="0"
                            step="0.1"
                            inputMode="decimal"
                            value={customWeightInputs[symbol] ?? ''}
                            onChange={(event) => handleWeightInputChange(symbol, event.target.value)}
                            className="w-full bg-transparent text-sm text-stone-100 outline-none"
                            placeholder="0"
                          />
                          <span className="text-xs text-stone-500">%</span>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {weightConfig.isValid && effectiveWeights.length > 0 && (
                <div className="space-y-2 rounded-lg border border-border-strong bg-surface-raised/40 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-xs text-stone-300">有效权重预览（请求实际生效）</p>
                    <span className="text-[11px] text-stone-500">
                      Top1 {(effectiveWeightStats.topOne * 100).toFixed(1)}% · Top2 {(effectiveWeightStats.topTwo * 100).toFixed(1)}% · HHI {effectiveWeightStats.hhi.toFixed(3)}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {effectiveWeights.map((item) => (
                      <div key={`effective-weight-${item.symbol}`} className="rounded-md border border-border-strong bg-surface-overlay/50 px-2.5 py-2">
                        <div className="mb-1 flex items-center justify-between gap-2">
                          <span className="text-xs text-stone-200 font-mono">{item.symbol}</span>
                          <span className="text-xs text-stone-400">{(item.weight * 100).toFixed(2)}%</span>
                        </div>
                        <div className="h-1.5 rounded-full bg-surface-muted overflow-hidden">
                          <div
                            className="h-full bg-cyan-500"
                            style={{ width: `${Math.max(2, item.weight * 100).toFixed(2)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>

                  <p
                    className={`text-[11px] ${
                      effectiveWeightStats.topOne >= 0.45 || effectiveWeightStats.topTwo >= 0.65
                        ? 'text-yellow-300'
                        : 'text-emerald-300'
                    }`}
                  >
                    {effectiveWeightStats.topOne >= 0.45
                      ? '单一标的权重偏高，建议将最大权重控制在 45% 以下。'
                      : effectiveWeightStats.topTwo >= 0.65
                        ? '前两大持仓占比较高，建议增加低相关标的分散风险。'
                        : '当前权重分布较均衡，可继续结合相关性与波动率复核。'}
                  </p>
                </div>
              )}

              {weightConfig.errorMessage ? (
                <p className="text-xs text-red-400">{weightConfig.errorMessage}</p>
              ) : (
                <p className="text-xs text-stone-500">{weightConfig.helperMessage}</p>
              )}
            </div>

            <p className="text-xs text-stone-500 mt-3">
              阈值越低，越容易识别到“高相关”股票群；阈值越高，只提示更强的相关风险。
            </p>
          </div>

          {/* 快速体检 */}
          <div className="bg-surface-overlay/30 rounded-xl p-4 border border-border-strong">
            <div className="flex items-center justify-between mb-4 gap-4">
              <div>
                <h3 className="text-lg font-bold text-white">Quick Check</h3>
                <p className="text-xs text-stone-500 mt-1">
                  周期 {periodLabel} · 聚类阈值 ≥ {clusterThreshold.toFixed(2)} ·{' '}
                  {weightMode === 'equal' ? '等权' : `输入合计 ${weightConfig.totalInputPercent.toFixed(2)}%`}
                </p>
              </div>
              <button
                type="button"
                onClick={handleRefreshQuickCheck}
                className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium bg-surface-overlay hover:bg-surface-muted text-stone-200 disabled:opacity-50"
                disabled={quickCheckQuery.isFetching || !isAnalysisReady}
                aria-label="刷新组合快速体检"
              >
                <RefreshCw className={`w-4 h-4 ${quickCheckQuery.isFetching ? 'animate-spin' : ''}`} />
                刷新
              </button>
            </div>

            {!isAnalysisReady ? (
              <div className="text-sm text-stone-400">请先修正参数后再运行快速体检。</div>
            ) : quickCheckQuery.isLoading && !quickCheckQuery.data ? (
              <div className="text-sm text-stone-400">正在生成快速体检...</div>
            ) : quickCheckQuery.error && !quickCheckQuery.data ? (
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                <p className="text-sm text-red-400">
                  快速体检失败: {(quickCheckQuery.error as Error).message}
                </p>
                <button
                  type="button"
                  onClick={handleRefreshQuickCheck}
                  className="px-3 py-2 bg-surface-overlay rounded-lg hover:bg-surface-muted text-white text-sm"
                >
                  重试体检
                </button>
              </div>
            ) : quickCheckQuery.data ? (
              <div className="space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-surface-overlay/50 rounded-xl p-4 border border-border-strong">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-stone-400">Diversification Score</span>
                      <Info className="w-4 h-4 text-stone-600" />
                    </div>
                    <div className={`text-3xl font-bold ${getDiversificationColor(quickCheckQuery.data.diversification_score)}`}>
                      {quickCheckQuery.data.diversification_score}
                      <span className="text-base text-stone-500">/100</span>
                    </div>
                    <div className="mt-2 h-2 bg-surface-muted rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-500 ${getDiversificationBarColor(quickCheckQuery.data.diversification_score)}`}
                        style={{ width: `${quickCheckQuery.data.diversification_score}%` }}
                      />
                    </div>
                  </div>

                  <div className="bg-surface-overlay/50 rounded-xl p-4 border border-border-strong">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-stone-400">Risk Clusters</span>
                      <Link2 className="w-4 h-4 text-stone-600" />
                    </div>
                    <div className="text-3xl font-bold text-white">
                      {quickCheckQuery.data.risk_clusters_count}
                      <span className="text-base text-stone-500"> groups</span>
                    </div>
                    <p className="text-xs text-stone-500 mt-2">
                      {quickCheckQuery.data.risk_clusters_count > 0
                        ? '存在高相关股票群，建议降低集中度'
                        : '未发现明显高相关股票群'}
                    </p>
                  </div>

                  <div className="bg-surface-overlay/50 rounded-xl p-4 border border-border-strong">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-stone-400">Top Recommendation</span>
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    </div>
                    <p className="text-sm text-stone-200 leading-relaxed">
                      {stripRecommendationPrefix(
                        quickCheckQuery.data.top_recommendation ?? quickCheckQuery.data.message
                      )}
                    </p>
                  </div>
                </div>

                {quickCheckQuery.error && (
                  <p className="text-xs text-yellow-400">
                    快速体检刷新失败，当前展示的是最近一次成功结果。
                  </p>
                )}
              </div>
            ) : (
              <div className="text-sm text-stone-400">暂无快速体检结果</div>
            )}
          </div>

          {showInitialAnalysisLoading ? (
            <LoadingState message="正在分析组合..." />
          ) : showInitialAnalysisError ? (
            <EmptyState
              icon={AlertTriangle}
              title={`分析失败: ${(portfolioMutation.error as Error).message}`}
              action={
                <button
                  onClick={handleAnalyze}
                  className="px-4 py-2 bg-surface-overlay rounded-lg hover:bg-surface-muted text-white"
                >
                  重试
                </button>
              }
            />
          ) : analysis ? (
            <div className="space-y-6">
              {hasPendingRefresh && (
                <div className="flex items-start gap-3 rounded-lg border border-cyan-700/40 bg-cyan-950/20 px-4 py-3">
                  <RefreshCw className="w-4 h-4 text-cyan-300 mt-0.5 shrink-0 animate-spin" />
                  <p className="text-sm text-cyan-100">参数已更新，正在基于新配置刷新分析结果...</p>
                </div>
              )}

              {portfolioMutation.error && (
                <div className="flex items-start gap-3 rounded-lg border border-yellow-700/40 bg-yellow-950/20 px-4 py-3">
                  <AlertTriangle className="w-4 h-4 text-yellow-400 mt-0.5 shrink-0" />
                  <p className="text-sm text-yellow-200">
                    最近一次刷新失败: {(portfolioMutation.error as Error).message}。当前展示的是上次成功分析结果。
                  </p>
                </div>
              )}

              {/* 顶部摘要卡片 */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-surface-overlay/50 rounded-xl p-4 border border-border-strong">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-stone-400">Diversification Score</span>
                    <Info className="w-4 h-4 text-stone-600" />
                  </div>
                  <div className={`text-4xl font-bold ${getDiversificationColor(analysis.diversification_score)}`}>
                    {analysis.diversification_score}
                    <span className="text-lg text-stone-500">/100</span>
                  </div>
                  <div className="mt-2 h-2 bg-surface-muted rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-1000 ${getDiversificationBarColor(analysis.diversification_score)}`}
                      style={{ width: `${analysis.diversification_score}%` }}
                    />
                  </div>
                </div>

                <div className="bg-surface-overlay/50 rounded-xl p-4 border border-border-strong">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-stone-400">Risk Clusters</span>
                    <Link2 className="w-4 h-4 text-stone-600" />
                  </div>
                  <div className="text-4xl font-bold text-white">
                    {analysis.risk_clusters.length}
                    <span className="text-lg text-stone-500"> groups</span>
                  </div>
                  <p className="text-xs text-stone-500 mt-2">
                    {analysis.risk_clusters.length === 0
                      ? '无高度相关股票群'
                      : `${analysis.risk_clusters.reduce((sum: number, c) => sum + c.stocks.length, 0)} stocks in correlated groups`}
                  </p>
                </div>

                <div className="bg-surface-overlay/50 rounded-xl p-4 border border-border-strong">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-stone-400">Analyzed Stocks</span>
                    <CheckCircle className="w-4 h-4 text-green-500" />
                  </div>
                  <div className="text-4xl font-bold text-white">
                    {analysis.correlation.symbols.length}
                    <span className="text-lg text-stone-500">/{stocks.length}</span>
                  </div>
                  <p className="text-xs text-stone-500 mt-2">
                    {analysis.correlation.symbols.length === stocks.length
                      ? '所有股票数据完整'
                      : `${stocks.length - analysis.correlation.symbols.length} 只股票数据不足`}
                  </p>
                </div>
              </div>

              <div className="bg-surface-overlay/30 rounded-xl p-4 border border-border-strong">
                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-gradient-to-r from-blue-500 to-red-500" />
                  Correlation Heatmap
                </h3>

                <div className="overflow-x-auto">
                  <div className="inline-block min-w-max">
                    <div className="flex">
                      <div className="w-20" />
                      {analysis.correlation.symbols.map((symbol) => (
                        <div key={symbol} className="w-12 text-center">
                          <span
                            className="text-xs text-stone-400 font-mono truncate block"
                            style={{ writingMode: 'vertical-lr' }}
                          >
                            {symbol.split('.')[0]}
                          </span>
                        </div>
                      ))}
                    </div>

                    {analysis.correlation.matrix.map((row, i) => (
                      <div key={i} className="flex items-center">
                        <div className="w-20 pr-2 text-right">
                          <span className="text-xs text-stone-400 font-mono truncate">
                            {analysis.correlation.symbols[i].split('.')[0]}
                          </span>
                        </div>

                        {row.map((value, j) => (
                          <HeatmapCell
                            key={j}
                            value={value}
                            rowSymbol={analysis.correlation.symbols[i]}
                            colSymbol={analysis.correlation.symbols[j]}
                            isDiagonal={i === j}
                          />
                        ))}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-center gap-4 text-xs text-stone-400">
                  <span className="flex items-center gap-1">
                    <span className="w-4 h-4 rounded bg-blue-700" /> -1.0 负相关
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-4 h-4 rounded bg-stone-600" /> 0 无相关
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-4 h-4 rounded bg-red-600" /> +1.0 正相关
                  </span>
                </div>
              </div>

              {sortedReturns.length > 0 && (
                <div className="bg-surface-overlay/30 rounded-xl p-4 border border-border-strong">
                  <h3 className="text-lg font-bold text-white mb-4">Returns Summary (1M)</h3>

                  <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                    {sortedReturns.map((item) => (
                      <div
                        key={item.symbol}
                        className={`p-3 rounded-lg border ${
                          item.total_return >= 0
                            ? 'bg-green-950/30 border-green-900/50'
                            : 'bg-red-950/30 border-red-900/50'
                        }`}
                      >
                        <div className="text-xs text-stone-400 font-mono truncate">
                          {item.symbol.split('.')[0]}
                        </div>
                        <div className={`text-lg font-bold ${item.total_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {item.total_return >= 0 ? '+' : ''}
                          {item.total_return.toFixed(1)}%
                        </div>
                        <div className="text-xs text-stone-500">Vol: {item.volatility.toFixed(1)}%</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {rebalanceSuggestions.length > 0 && (
                <div className="bg-surface-overlay/30 rounded-xl p-4 border border-border-strong">
                  <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                    <h3 className="text-lg font-bold text-white">Rebalance Suggestions</h3>
                    <button
                      type="button"
                      onClick={handleApplyRebalanceSuggestion}
                      className="px-3 py-1.5 text-xs rounded-lg bg-cyan-700 text-white hover:bg-cyan-600"
                    >
                      一键应用建议权重
                    </button>
                  </div>

                  <p className="text-xs text-stone-500 mb-3">
                    基于波动率、相关性和近期收益给出建议权重，用于辅助再平衡，不构成投资建议。
                  </p>

                  {rebalanceSummary && (
                    <div className="mb-3 text-xs text-stone-400">
                      预计换手约 {(rebalanceSummary.turnover * 100).toFixed(1)}% · 建议增持 {rebalanceSummary.increaseCount} 只 · 建议减持 {rebalanceSummary.decreaseCount} 只 · 来源 {rebalanceSummary.source === 'server' ? '后端模型' : '前端兜底'}
                    </div>
                  )}

                  <div className="space-y-2">
                    {rebalanceSuggestions.map((item) => (
                      <div
                        key={`rebalance-${item.symbol}`}
                        className="rounded-lg border border-border-strong bg-surface-raised/50 px-3 py-2"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-mono text-stone-200">{item.symbol}</span>
                            <span
                              className={`text-[11px] px-1.5 py-0.5 rounded ${
                                item.action === 'increase'
                                  ? 'bg-emerald-950/60 text-emerald-300'
                                  : item.action === 'decrease'
                                    ? 'bg-amber-950/60 text-amber-300'
                                    : 'bg-surface-overlay text-stone-300'
                              }`}
                            >
                              {item.action === 'increase'
                                ? '建议增持'
                                : item.action === 'decrease'
                                  ? '建议减持'
                                  : '保持'}
                            </span>
                          </div>
                          <div className="text-xs text-stone-300">
                            当前 {(item.currentWeight * 100).toFixed(2)}% → 建议 {(item.targetWeight * 100).toFixed(2)}% （
                            {item.delta >= 0 ? '+' : ''}
                            {(item.delta * 100).toFixed(2)}%）
                          </div>
                        </div>
                        <div className="mt-1 text-[11px] text-stone-500">
                          近一期收益 {item.totalReturn.toFixed(1)}% · 波动率 {item.volatility.toFixed(1)}%
                          {typeof item.confidence === 'number' && (
                            <span> · 置信度 {(item.confidence * 100).toFixed(0)}%</span>
                          )}
                        </div>
                        {item.rationale && <div className="mt-1 text-[11px] text-stone-400">{item.rationale}</div>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {constraintViolations.length > 0 && (
                <div className="bg-surface-overlay/30 rounded-xl p-4 border border-border-strong">
                  <h3 className="text-lg font-bold text-white mb-3">Constraint Violations</h3>
                  <div className="space-y-2">
                    {constraintViolations.map((violation, index) => (
                      <div
                        key={`${violation.code}-${index}`}
                        className="rounded-lg border border-border-strong bg-surface-raised/50 px-3 py-2"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs text-stone-200">{violation.message}</span>
                          <span
                            className={`text-[11px] px-1.5 py-0.5 rounded ${
                              violation.severity === 'critical'
                                ? 'bg-red-950/70 text-red-300'
                                : 'bg-amber-950/70 text-amber-300'
                            }`}
                          >
                            {violation.severity === 'critical' ? 'critical' : 'warning'}
                          </span>
                        </div>
                        <div className="mt-1 text-[11px] text-stone-500">
                          实际值 {violation.actual.toFixed(4)} · 限制 {violation.limit.toFixed(4)} · 代码 {violation.code}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {backtestPayloadHint && (
                <div className="bg-surface-overlay/30 rounded-xl p-4 border border-border-strong">
                  <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
                    <div>
                      <h3 className="text-lg font-bold text-white">Backtest Payload Hint</h3>
                      <p className="text-xs text-stone-500 mt-1">
                        策略 {backtestPayloadHint.strategy_name} · 生成时间{' '}
                        {new Date(backtestPayloadHint.generated_at).toLocaleString('zh-CN', {
                          hour12: false,
                        })}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => refreshBacktestHistory()}
                        disabled={isBacktestHistoryLoading}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-surface-overlay text-stone-200 hover:bg-surface-muted disabled:opacity-50"
                      >
                        <RefreshCw className={`h-3.5 w-3.5 ${isBacktestHistoryLoading ? 'animate-spin' : ''}`} />
                        {isBacktestHistoryLoading ? '刷新中...' : '刷新历史'}
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleRunAllHintBacktests()}
                        disabled={isRunningAllBacktests || backtestPayloadHint.requests.length === 0}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-cyan-700 text-white hover:bg-cyan-600 disabled:opacity-50"
                      >
                        <Play className="h-3.5 w-3.5" />
                        {isRunningAllBacktests ? '批量执行中...' : '一键执行全部回测'}
                      </button>
                    </div>
                  </div>

                  {backtestFeedback && (
                    <p
                      className={`mb-3 text-xs ${
                        backtestFeedback.type === 'error'
                          ? 'text-red-400'
                          : backtestFeedback.type === 'success'
                            ? 'text-emerald-400'
                            : 'text-cyan-300'
                      }`}
                    >
                      {backtestFeedback.message}
                    </p>
                  )}

                  {isBacktestHistoryLoading && (
                    <p className="mb-3 text-[11px] text-stone-500">正在同步最近回测记录...</p>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {backtestPayloadHint.requests.map((request) => {
                      const execution = backtestExecutionMap[request.symbol];
                      const latestHistory = latestBacktestHistoryMap[request.symbol];
                      const isRunning = execution?.status === 'running';

                      return (
                        <div
                          key={`backtest-hint-${request.symbol}`}
                          className="rounded-lg border border-border-strong bg-surface-raised/50 px-3 py-2"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-sm font-mono text-stone-200">{request.symbol}</span>
                            <span className="text-[11px] text-stone-400">{request.signals[0]?.signal ?? 'neutral'}</span>
                          </div>
                          <div className="mt-1 text-[11px] text-stone-500">
                            持有 {request.holding_days} 天 · 止损 {request.stop_loss_pct}% · 止盈 {request.take_profit_pct}%
                          </div>
                          <div className="mt-2 flex items-center justify-between gap-2">
                            <span className="text-[11px] text-stone-500">
                              信号数 {request.signals.length} · 资金 {request.initial_capital.toLocaleString('zh-CN')}
                            </span>
                            <button
                              type="button"
                              onClick={() => void executeBacktestFromHint(request)}
                              disabled={isRunningAllBacktests || isRunning}
                              className="inline-flex items-center gap-1 px-2 py-1 text-[11px] rounded-md bg-surface-overlay text-stone-200 hover:bg-surface-muted disabled:opacity-50"
                            >
                              <Play className="h-3 w-3" />
                              {isRunning ? '执行中...' : '执行回测'}
                            </button>
                          </div>

                          {execution && (
                            <div
                              className={`mt-2 text-[11px] ${
                                execution.status === 'error'
                                  ? 'text-red-400'
                                  : execution.status === 'success'
                                    ? 'text-emerald-400'
                                    : 'text-cyan-300'
                              }`}
                            >
                              {execution.message}
                              {execution.finishedAt && (
                                <span className="text-stone-500">
                                  {' '}
                                  · {new Date(execution.finishedAt).toLocaleTimeString('zh-CN', { hour12: false })}
                                </span>
                              )}
                            </div>
                          )}

                          {latestHistory && (
                            <div className="mt-1 flex items-center justify-between gap-2 text-[11px] text-stone-500">
                              <span>
                                最近记录 · 收益 {latestHistory.total_return_pct.toFixed(2)}% · 胜率 {latestHistory.win_rate} ·{' '}
                                {new Date(latestHistory.created_at).toLocaleString('zh-CN', { hour12: false })}
                              </span>
                              <button
                                type="button"
                                onClick={() =>
                                  setSelectedBacktestRecord({
                                    symbol: request.symbol,
                                    recordId: latestHistory.id,
                                  })
                                }
                                className="px-2 py-0.5 rounded-md bg-surface-overlay text-stone-200 hover:bg-surface-muted"
                              >
                                查看详情
                              </button>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="bg-surface-overlay/30 rounded-xl p-4 border border-border-strong">
                <h3 className="text-lg font-bold text-white mb-4">Recommendations</h3>

                <div className="space-y-3">
                  {analysis.recommendations.map((rec, i) => {
                    const normalized = stripRecommendationPrefix(rec);
                    const hasLeadingPrefix = normalized !== rec;

                    return (
                      <div
                        key={i}
                        className="flex items-start gap-3 p-3 bg-surface-raised/50 rounded-lg border border-border-strong"
                      >
                        <span className="text-xl">{hasLeadingPrefix ? rec.charAt(0) : '•'}</span>
                        <p className="text-sm text-stone-300">{normalized}</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <LoadingState message="正在准备分析任务..." />
          )}
        </div>
      )}
    </PageLayout>
  );
};

export default PortfolioPage;
