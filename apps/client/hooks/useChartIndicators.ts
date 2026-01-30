import { useState, useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import type { TimePeriod, IndicatorType } from '@/components/ChartToolbar';
import type { KlineDataPoint } from '@/components/TradingViewChart';
import { getMarketKline } from '@/services/api';

/**
 * 图表指标 Hook
 *
 * 管理图表的时间周期、技术指标选择、全屏状态，并加载 K 线数据。
 */

interface UseChartIndicatorsOptions {
  symbol?: string;
  market?: string;
  initialPeriod?: TimePeriod;
  initialIndicators?: IndicatorType[];
  initialShowVolume?: boolean;
}

interface UseChartIndicatorsReturn {
  // 状态
  period: TimePeriod;
  indicators: IndicatorType[];
  showVolume: boolean;
  isFullscreen: boolean;

  // 操作
  setPeriod: (period: TimePeriod) => void;
  setIndicators: (indicators: IndicatorType[]) => void;
  toggleVolume: () => void;
  toggleFullscreen: () => void;

  // 数据
  klineData: KlineDataPoint[];
  isLoading: boolean;
  error: Error | null;
}

/**
 * 时间周期到天数的映射
 */
const PERIOD_TO_DAYS: Record<TimePeriod, number> = {
  '1D': 1,
  '1W': 7,
  '1M': 30,
  '3M': 90,
  '6M': 180,
  '1Y': 365,
  '3Y': 1095,
  'ALL': 3650,
};

/**
 * 获取 K 线历史数据
 */
async function fetchKlineData(symbol: string, days: number): Promise<KlineDataPoint[]> {
  const data = await getMarketKline(symbol, days);
  return data.kline || [];
}

export function useChartIndicators(options: UseChartIndicatorsOptions = {}): UseChartIndicatorsReturn {
  const {
    symbol,
    initialPeriod = '3M',
    initialIndicators = ['ma5', 'ma20'],
    initialShowVolume = true,
  } = options;

  // 状态
  const [period, setPeriod] = useState<TimePeriod>(initialPeriod);
  const [indicators, setIndicators] = useState<IndicatorType[]>(initialIndicators);
  const [showVolume, setShowVolume] = useState(initialShowVolume);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // 操作
  const toggleVolume = useCallback(() => setShowVolume((v) => !v), []);
  const toggleFullscreen = useCallback(() => setIsFullscreen((v) => !v), []);

  // 计算数据请求天数
  const days = useMemo(() => PERIOD_TO_DAYS[period], [period]);

  // 获取 K 线数据
  const {
    data: klineData = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ['kline', symbol, days],
    queryFn: () => fetchKlineData(symbol!, days),
    enabled: !!symbol,
    staleTime: 60 * 1000, // 1 分钟
    gcTime: 5 * 60 * 1000, // 5 分钟
    retry: 2,
  });

  return {
    // 状态
    period,
    indicators,
    showVolume,
    isFullscreen,

    // 操作
    setPeriod,
    setIndicators,
    toggleVolume,
    toggleFullscreen,

    // 数据
    klineData,
    isLoading,
    error: error as Error | null,
  };
}

export default useChartIndicators;
