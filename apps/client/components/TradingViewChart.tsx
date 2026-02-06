import React, { useEffect, useRef, memo } from 'react';
import {
  createChart,
  ColorType,
  CrosshairMode,
  LineStyle,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  HistogramData,
  Time,
} from 'lightweight-charts';

/**
 * K 线数据格式
 */
export interface KlineDataPoint {
  time: string;  // ISO 日期字符串或时间戳
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

/**
 * 简单价格数据格式（兼容现有 StockChart）
 */
export interface SimpleDataPoint {
  time: string;
  value: number;
}

/**
 * 指标类型
 */
export type IndicatorType = 'ma5' | 'ma10' | 'ma20' | 'ma60' | 'ma120' | 'bollinger';

/**
 * TradingViewChart 组件属性
 */
export interface TradingViewChartProps {
  /** K 线数据 */
  data?: KlineDataPoint[];
  /** 简单价格数据（兼容现有格式） */
  simpleData?: SimpleDataPoint[];
  /** 股票代码 */
  symbol?: string;
  /** 图表高度 */
  height?: number;
  /** 是否显示成交量 */
  showVolume?: boolean;
  /** 要显示的指标 */
  indicators?: IndicatorType[];
  /** 是否为上涨（用于颜色） */
  isUp?: boolean;
  /** 自定义类名 */
  className?: string;
  /** 是否显示十字光标 */
  crosshair?: boolean;
  /** 是否显示网格 */
  grid?: boolean;
  /** 是否显示时间刻度 */
  timeScale?: boolean;
  /** 主题 */
  theme?: 'dark' | 'light';
}

// 颜色配置
const COLORS = {
  dark: {
    background: '#1a1a2e',
    text: '#d1d4dc',
    grid: '#2B2B43',
    up: '#26a69a',
    down: '#ef5350',
    ma5: '#f7931a',
    ma10: '#627eea',
    ma20: '#00d4aa',
    ma60: '#ff6b6b',
    ma120: '#a855f7',
    bollingerUpper: '#ff9800',
    bollingerLower: '#ff9800',
    bollingerMiddle: '#9c27b0',
    volume: {
      up: 'rgba(38, 166, 154, 0.5)',
      down: 'rgba(239, 83, 80, 0.5)',
    },
  },
  light: {
    background: '#ffffff',
    text: '#333333',
    grid: '#e0e0e0',
    up: '#26a69a',
    down: '#ef5350',
    ma5: '#f7931a',
    ma10: '#627eea',
    ma20: '#00d4aa',
    ma60: '#ff6b6b',
    ma120: '#a855f7',
    bollingerUpper: '#ff9800',
    bollingerLower: '#ff9800',
    bollingerMiddle: '#9c27b0',
    volume: {
      up: 'rgba(38, 166, 154, 0.5)',
      down: 'rgba(239, 83, 80, 0.5)',
    },
  },
};

/**
 * 计算移动平均线
 */
function calculateMA(data: KlineDataPoint[], period: number): { time: Time; value: number }[] {
  const result: { time: Time; value: number }[] = [];

  for (let i = period - 1; i < data.length; i++) {
    let sum = 0;
    for (let j = 0; j < period; j++) {
      sum += data[i - j].close;
    }
    result.push({
      time: data[i].time as Time,
      value: sum / period,
    });
  }

  return result;
}

/**
 * 计算布林带
 */
function calculateBollinger(
  data: KlineDataPoint[],
  period: number = 20,
  multiplier: number = 2
): {
  upper: { time: Time; value: number }[];
  middle: { time: Time; value: number }[];
  lower: { time: Time; value: number }[];
} {
  const upper: { time: Time; value: number }[] = [];
  const middle: { time: Time; value: number }[] = [];
  const lower: { time: Time; value: number }[] = [];

  for (let i = period - 1; i < data.length; i++) {
    let sum = 0;
    for (let j = 0; j < period; j++) {
      sum += data[i - j].close;
    }
    const ma = sum / period;

    let variance = 0;
    for (let j = 0; j < period; j++) {
      variance += Math.pow(data[i - j].close - ma, 2);
    }
    const std = Math.sqrt(variance / period);

    middle.push({ time: data[i].time as Time, value: ma });
    upper.push({ time: data[i].time as Time, value: ma + multiplier * std });
    lower.push({ time: data[i].time as Time, value: ma - multiplier * std });
  }

  return { upper, middle, lower };
}

/**
 * 将简单数据转换为 K 线格式（用于兼容）
 */
function simpleToKline(data: SimpleDataPoint[]): KlineDataPoint[] {
  return data.map((d, i) => ({
    time: d.time,
    open: i > 0 ? data[i - 1].value : d.value,
    high: d.value * 1.005,
    low: d.value * 0.995,
    close: d.value,
  }));
}

/**
 * TradingView 专业级图表组件
 *
 * 使用 lightweight-charts 库实现
 */
export const TradingViewChart: React.FC<TradingViewChartProps> = memo(({
  data,
  simpleData,
  symbol,
  height = 400,
  showVolume = true,
  indicators = [],
  className = '',
  crosshair = true,
  grid = true,
  timeScale = true,
  theme = 'dark',
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const indicatorSeriesRef = useRef<Map<string, ISeriesApi<'Line'>>>(new Map());

  const colors = COLORS[theme];

  // 处理数据
  const klineData = data || (simpleData ? simpleToKline(simpleData) : []);

  // 初始化图表
  useEffect(() => {
    if (!chartContainerRef.current || klineData.length === 0) return;

    // 清理旧图表
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
      candlestickSeriesRef.current = null;
      volumeSeriesRef.current = null;
      indicatorSeriesRef.current.clear();
    }

    // 创建图表
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: colors.background },
        textColor: colors.text,
      },
      grid: {
        vertLines: { color: grid ? colors.grid : 'transparent' },
        horzLines: { color: grid ? colors.grid : 'transparent' },
      },
      width: chartContainerRef.current.clientWidth,
      height: showVolume ? height * 0.75 : height,
      crosshair: {
        mode: crosshair ? CrosshairMode.Normal : CrosshairMode.Hidden,
        vertLine: {
          color: 'rgba(255, 255, 255, 0.2)',
          width: 1,
          style: LineStyle.Dashed,
          labelBackgroundColor: colors.background,
        },
        horzLine: {
          color: 'rgba(255, 255, 255, 0.2)',
          width: 1,
          style: LineStyle.Dashed,
          labelBackgroundColor: colors.background,
        },
      },
      rightPriceScale: {
        borderColor: colors.grid,
        scaleMargins: {
          top: 0.1,
          bottom: showVolume ? 0.2 : 0.1,
        },
      },
      timeScale: {
        borderColor: colors.grid,
        visible: timeScale,
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // 添加蜡烛图系列
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: colors.up,
      downColor: colors.down,
      borderVisible: false,
      wickUpColor: colors.up,
      wickDownColor: colors.down,
    });

    // 格式化数据
    const formattedData: CandlestickData[] = klineData.map((d) => ({
      time: d.time as Time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));

    candlestickSeries.setData(formattedData);
    candlestickSeriesRef.current = candlestickSeries;

    // 添加成交量
    if (showVolume && klineData.some((d) => d.volume !== undefined)) {
      const volumeSeries = chart.addHistogramSeries({
        color: colors.volume.up,
        priceFormat: {
          type: 'volume',
        },
        priceScaleId: '',
      });

      chart.priceScale('').applyOptions({
        scaleMargins: {
          top: 0.85,
          bottom: 0,
        },
      });

      const volumeData: HistogramData[] = klineData.map((d) => ({
        time: d.time as Time,
        value: d.volume || 0,
        color: d.close >= d.open ? colors.volume.up : colors.volume.down,
      }));

      volumeSeries.setData(volumeData);
      volumeSeriesRef.current = volumeSeries;
    }

    // 添加指标
    indicators.forEach((indicator) => {
      let seriesData: { time: Time; value: number }[] = [];
      let color = colors.ma20;

      switch (indicator) {
        case 'ma5':
          seriesData = calculateMA(klineData, 5);
          color = colors.ma5;
          break;
        case 'ma10':
          seriesData = calculateMA(klineData, 10);
          color = colors.ma10;
          break;
        case 'ma20':
          seriesData = calculateMA(klineData, 20);
          color = colors.ma20;
          break;
        case 'ma60':
          seriesData = calculateMA(klineData, 60);
          color = colors.ma60;
          break;
        case 'ma120':
          seriesData = calculateMA(klineData, 120);
          color = colors.ma120;
          break;
        case 'bollinger': {
          const bollinger = calculateBollinger(klineData);

          // 上轨
          const upperSeries = chart.addLineSeries({
            color: colors.bollingerUpper,
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
          });
          upperSeries.setData(bollinger.upper);
          indicatorSeriesRef.current.set('bollinger_upper', upperSeries);

          // 中轨
          const middleSeries = chart.addLineSeries({
            color: colors.bollingerMiddle,
            lineWidth: 1,
          });
          middleSeries.setData(bollinger.middle);
          indicatorSeriesRef.current.set('bollinger_middle', middleSeries);

          // 下轨
          const lowerSeries = chart.addLineSeries({
            color: colors.bollingerLower,
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
          });
          lowerSeries.setData(bollinger.lower);
          indicatorSeriesRef.current.set('bollinger_lower', lowerSeries);

          return;
        }
      }

      if (seriesData.length > 0) {
        const series = chart.addLineSeries({
          color,
          lineWidth: 1,
        });
        series.setData(seriesData);
        indicatorSeriesRef.current.set(indicator, series);
      }
    });

    // 自适应时间范围
    chart.timeScale().fitContent();

    // 响应式调整
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [klineData, showVolume, indicators, colors, grid, crosshair, timeScale, height]);

  // 空数据状态
  if (klineData.length === 0) {
    return (
      <div
        className={`flex items-center justify-center bg-surface-raised/50 rounded-lg ${className}`}
        style={{ height }}
      >
        <span className="text-stone-500">No chart data available</span>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      <div ref={chartContainerRef} style={{ height }} />

      {/* 图例 */}
      {indicators.length > 0 && (
        <div className="absolute top-2 left-2 flex flex-wrap gap-2 text-[10px]">
          {indicators.includes('ma5') && (
            <span className="px-1.5 py-0.5 rounded" style={{ backgroundColor: `${colors.ma5}33`, color: colors.ma5 }}>
              MA5
            </span>
          )}
          {indicators.includes('ma10') && (
            <span className="px-1.5 py-0.5 rounded" style={{ backgroundColor: `${colors.ma10}33`, color: colors.ma10 }}>
              MA10
            </span>
          )}
          {indicators.includes('ma20') && (
            <span className="px-1.5 py-0.5 rounded" style={{ backgroundColor: `${colors.ma20}33`, color: colors.ma20 }}>
              MA20
            </span>
          )}
          {indicators.includes('ma60') && (
            <span className="px-1.5 py-0.5 rounded" style={{ backgroundColor: `${colors.ma60}33`, color: colors.ma60 }}>
              MA60
            </span>
          )}
          {indicators.includes('bollinger') && (
            <span className="px-1.5 py-0.5 rounded" style={{ backgroundColor: `${colors.bollingerMiddle}33`, color: colors.bollingerMiddle }}>
              BOLL
            </span>
          )}
        </div>
      )}

      {/* 股票代码标签 */}
      {symbol && (
        <div className="absolute top-2 right-2 text-xs text-stone-500 bg-surface-raised/80 px-2 py-1 rounded">
          {symbol}
        </div>
      )}
    </div>
  );
});

TradingViewChart.displayName = 'TradingViewChart';

export default TradingViewChart;
