"use client";

import { useState } from "react";
import { TrendingUp, Calendar } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  LineChart, 
  Line, 
  AreaChart,
  Area,
  XAxis, 
  YAxis, 
  CartesianGrid,
  Tooltip, 
  Legend,
  ResponsiveContainer,
  TooltipProps
} from "recharts";
import { formatCurrency, formatPercent } from "@tradingagents/shared/utils/format";

interface PerformanceDataPoint {
  date: string;
  portfolioValue: number;
  cumulativePnl: number;
  dailyReturn: number;
  benchmark?: number;
}

interface PerformanceChartProps {
  portfolioId: number;
  data?: PerformanceDataPoint[];
  timeRange?: "1d" | "1w" | "1m" | "3m" | "1y" | "all";
}

export function PerformanceChart({ 
  portfolioId, 
  data: initialData,
  timeRange: initialTimeRange = "1m"
}: PerformanceChartProps) {
  const [timeRange, setTimeRange] = useState(initialTimeRange);
  const [chartType, setChartType] = useState<"line" | "area">("area");

  // 模拟数据生成（实际应该从 API 获取）
  const data = initialData || generateMockData(timeRange);

  // 计算统计信息
  const stats = calculateStats(data);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-primary" />
              投资组合表现
            </CardTitle>
            <CardDescription>
              Portfolio ID: {portfolioId} - 历史收益走势
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Select value={chartType} onValueChange={(v) => setChartType(v as "line" | "area")}>
              <SelectTrigger className="w-[120px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="line">折线图</SelectItem>
                <SelectItem value="area">面积图</SelectItem>
              </SelectContent>
            </Select>
            <Select value={timeRange} onValueChange={(v) => setTimeRange(v as typeof timeRange)}>
              <SelectTrigger className="w-[120px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1d">1天</SelectItem>
                <SelectItem value="1w">1周</SelectItem>
                <SelectItem value="1m">1月</SelectItem>
                <SelectItem value="3m">3月</SelectItem>
                <SelectItem value="1y">1年</SelectItem>
                <SelectItem value="all">全部</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* 统计摘要 */}
        <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
          <StatCard
            label="当前价值"
            value={formatCurrency(stats.currentValue)}
            change={stats.totalReturn}
          />
          <StatCard
            label="累计收益"
            value={formatCurrency(stats.totalPnl)}
            change={stats.totalReturn}
          />
          <StatCard
            label="收益率"
            value={formatPercent(stats.totalReturn / 100)}
            change={stats.totalReturn}
          />
          <StatCard
            label="夏普比率"
            value={stats.sharpeRatio.toFixed(2)}
          />
        </div>

        {/* 图表 */}
        <ResponsiveContainer width="100%" height={400}>
          {chartType === "area" ? (
            <AreaChart data={data}>
              <defs>
                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorPnl" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--success))" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="hsl(var(--success))" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border/30" />
              <XAxis 
                dataKey="date" 
                className="text-xs"
                tickFormatter={(value) => formatDateShort(value)}
              />
              <YAxis 
                className="text-xs"
                tickFormatter={(value) => formatCurrency(value)}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Area
                type="monotone"
                dataKey="portfolioValue"
                stroke="hsl(var(--primary))"
                fill="url(#colorValue)"
                strokeWidth={2}
                name="总资产"
              />
              <Area
                type="monotone"
                dataKey="cumulativePnl"
                stroke="hsl(var(--success))"
                fill="url(#colorPnl)"
                strokeWidth={2}
                name="累计盈亏"
              />
              {data[0]?.benchmark !== undefined && (
                <Area
                  type="monotone"
                  dataKey="benchmark"
                  stroke="hsl(var(--muted-foreground))"
                  fill="none"
                  strokeWidth={1}
                  strokeDasharray="5 5"
                  name="基准指数"
                />
              )}
            </AreaChart>
          ) : (
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border/30" />
              <XAxis 
                dataKey="date" 
                className="text-xs"
                tickFormatter={(value) => formatDateShort(value)}
              />
              <YAxis 
                className="text-xs"
                tickFormatter={(value) => formatCurrency(value)}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Line
                type="monotone"
                dataKey="portfolioValue"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                dot={false}
                name="总资产"
              />
              <Line
                type="monotone"
                dataKey="cumulativePnl"
                stroke="hsl(var(--success))"
                strokeWidth={2}
                dot={false}
                name="累计盈亏"
              />
              {data[0]?.benchmark !== undefined && (
                <Line
                  type="monotone"
                  dataKey="benchmark"
                  stroke="hsl(var(--muted-foreground))"
                  strokeWidth={1}
                  strokeDasharray="5 5"
                  dot={false}
                  name="基准指数"
                />
              )}
            </LineChart>
          )}
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

interface StatCardProps {
  label: string;
  value: string;
  change?: number;
}

function StatCard({ label, value, change }: StatCardProps) {
  return (
    <div className="rounded-lg border border-border/60 bg-surface/50 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold text-foreground">{value}</p>
      {change !== undefined && (
        <p className={`text-xs ${change >= 0 ? "text-success" : "text-destructive"}`}>
          {change >= 0 ? "+" : ""}{change.toFixed(2)}%
        </p>
      )}
    </div>
  );
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload || !payload.length) {
    return null;
  }

  return (
    <div className="rounded-lg border border-border bg-background/95 p-3 shadow-lg backdrop-blur">
      <p className="mb-2 text-sm font-semibold text-foreground">{label}</p>
      <div className="space-y-1">
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center justify-between gap-4 text-sm">
            <span className="text-muted-foreground">{entry.name}:</span>
            <span className="font-medium" style={{ color: entry.color }}>
              {typeof entry.value === "number" && entry.dataKey?.toString().includes("Value")
                ? formatCurrency(entry.value)
                : formatCurrency(entry.value as number)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatDateShort(dateStr: string): string {
  const date = new Date(dateStr);
  return `${date.getMonth() + 1}/${date.getDate()}`;
}

function generateMockData(timeRange: string): PerformanceDataPoint[] {
  const days = {
    "1d": 1,
    "1w": 7,
    "1m": 30,
    "3m": 90,
    "1y": 365,
    "all": 730,
  }[timeRange] || 30;

  const data: PerformanceDataPoint[] = [];
  const startValue = 100000;
  let currentValue = startValue;
  let cumulativePnl = 0;

  for (let i = 0; i < days; i++) {
    const date = new Date();
    date.setDate(date.getDate() - (days - i));

    // 模拟每日收益波动 (-2% 到 +2%)
    const dailyReturn = (Math.random() - 0.45) * 4;
    const dailyPnl = currentValue * (dailyReturn / 100);
    
    currentValue += dailyPnl;
    cumulativePnl += dailyPnl;

    // 模拟基准指数（略低于组合表现）
    const benchmark = startValue * (1 + cumulativePnl / startValue * 0.7);

    data.push({
      date: date.toISOString().split("T")[0],
      portfolioValue: currentValue,
      cumulativePnl,
      dailyReturn,
      benchmark,
    });
  }

  return data;
}

function calculateStats(data: PerformanceDataPoint[]) {
  if (data.length === 0) {
    return {
      currentValue: 0,
      totalPnl: 0,
      totalReturn: 0,
      sharpeRatio: 0,
    };
  }

  const first = data[0];
  const last = data[data.length - 1];
  
  const totalReturn = ((last.portfolioValue - first.portfolioValue) / first.portfolioValue) * 100;
  
  // 计算夏普比率（简化版）
  const returns = data.map(d => d.dailyReturn);
  const avgReturn = returns.reduce((a, b) => a + b, 0) / returns.length;
  const stdDev = Math.sqrt(
    returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length
  );
  const sharpeRatio = stdDev > 0 ? (avgReturn / stdDev) * Math.sqrt(252) : 0;

  return {
    currentValue: last.portfolioValue,
    totalPnl: last.cumulativePnl,
    totalReturn,
    sharpeRatio,
  };
}