"use client";

import { TrendingUp, TrendingDown, DollarSign, Wallet } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { formatCurrency, formatPercent } from "@tradingagents/shared/utils/format";
import type { PortfolioUpdate, Position } from "@tradingagents/shared/domain";
import { LineChart, Line, ResponsiveContainer, Tooltip } from "recharts";

interface PortfolioOverviewProps {
  data: PortfolioUpdate | null;
  isConnected: boolean;
}

export function PortfolioOverview({ data, isConnected }: PortfolioOverviewProps) {
  if (!data) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  const totalPnl = data.totalUnrealizedPnl + data.totalRealizedPnl;
  const totalPnlPercent = data.totalValue > 0 ? (totalPnl / data.totalValue) * 100 : 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Portfolio Overview</h2>
        <ConnectionStatus isConnected={isConnected} />
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Total Value"
          value={formatCurrency(data.totalValue)}
          icon={Wallet}
          trend={data.dailyPnlPercent}
        />
        <MetricCard
          title="Cash"
          value={formatCurrency(data.cash)}
          icon={DollarSign}
        />
        <MetricCard
          title="Today's P&L"
          value={formatCurrency(data.dailyPnl)}
          description={formatPercent(data.dailyPnlPercent / 100)}
          icon={data.dailyPnl >= 0 ? TrendingUp : TrendingDown}
          trend={data.dailyPnlPercent}
        />
        <MetricCard
          title="Total P&L"
          value={formatCurrency(totalPnl)}
          description={formatPercent(totalPnlPercent / 100)}
          icon={totalPnl >= 0 ? TrendingUp : TrendingDown}
          trend={totalPnlPercent}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Holdings</CardTitle>
          <CardDescription>
            Current positions in your portfolio ({data.positions.length})
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data.positions.length > 0 ? (
            <div className="space-y-3">
              {data.positions.map((position) => (
                <PositionRow key={position.id} position={position} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No active positions</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

interface MetricCardProps {
  title: string;
  value: string;
  description?: string;
  icon: React.ComponentType<{ className?: string }>;
  trend?: number;
}

function MetricCard({ title, value, description, icon: Icon, trend }: MetricCardProps) {
  const trendColor = trend !== undefined 
    ? trend >= 0 
      ? "text-success" 
      : "text-destructive"
    : "";

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className={cn("h-4 w-4 text-muted-foreground", trendColor)} />
      </CardHeader>
      <CardContent>
        <div className={cn("text-2xl font-bold", trendColor)}>{value}</div>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
      </CardContent>
    </Card>
  );
}

interface PositionRowProps {
  position: Position;
}

function PositionRow({ position }: PositionRowProps) {
  const marketValue = position.quantity * position.currentPrice;
  const pnlPercent = position.averageCost > 0 
    ? ((position.currentPrice - position.averageCost) / position.averageCost) * 100
    : 0;

  return (
    <div className="flex items-center justify-between rounded-lg border border-border/60 bg-surface/80 p-4">
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-foreground">{position.symbol}</span>
          <Badge variant="outline" className="text-xs">
            {position.positionType}
          </Badge>
        </div>
        <div className="mt-1 text-sm text-muted-foreground">
          {position.quantity.toFixed(2)} @ {formatCurrency(position.averageCost)}
        </div>
      </div>
      <div className="text-right">
        <div className="font-semibold text-foreground">{formatCurrency(marketValue)}</div>
        <div className={cn(
          "text-sm font-medium",
          position.unrealizedPnl >= 0 ? "text-success" : "text-destructive"
        )}>
          {formatCurrency(position.unrealizedPnl)} ({formatPercent(pnlPercent / 100)})
        </div>
      </div>
    </div>
  );
}

function ConnectionStatus({ isConnected }: { isConnected: boolean }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <div
        className={cn(
          "h-2 w-2 rounded-full",
          isConnected ? "bg-success animate-pulse" : "bg-muted-foreground"
        )}
      />
      <span className="text-muted-foreground">
        {isConnected ? "Live" : "Disconnected"}
      </span>
    </div>
  );
}

function SkeletonCard() {
  return (
    <Card>
      <CardHeader className="space-y-0 pb-2">
        <div className="h-4 w-24 animate-pulse rounded bg-muted" />
      </CardHeader>
      <CardContent>
        <div className="h-8 w-32 animate-pulse rounded bg-muted" />
      </CardContent>
    </Card>
  );
}
