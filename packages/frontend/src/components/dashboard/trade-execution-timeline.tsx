"use client";

import { useState } from "react";
import { Clock, TrendingUp, TrendingDown, CheckCircle, XCircle, Clock3, Filter } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { formatDate, formatCurrency } from "@tradingagents/shared/utils/format";
import type { Trade } from "@tradingagents/shared/domain";

interface TradeExecutionTimelineProps {
  trades: Trade[];
  isConnected: boolean;
}

type TradeFilter = "all" | "executed" | "pending" | "failed";

export function TradeExecutionTimeline({ trades, isConnected }: TradeExecutionTimelineProps) {
  const [filter, setFilter] = useState<TradeFilter>("all");

  const filteredTrades = trades.filter(trade => {
    if (filter === "all") return true;
    return trade.status === filter;
  });

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-primary" />
              Trade Execution Timeline
            </CardTitle>
            <CardDescription>
              Recent trades and execution history ({filteredTrades.length} trades)
            </CardDescription>
          </div>
          <ConnectionIndicator isConnected={isConnected} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="mb-4 flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select value={filter} onValueChange={(value) => setFilter(value as TradeFilter)}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter trades" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Trades</SelectItem>
              <SelectItem value="executed">Executed</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <ScrollArea className="h-[600px]">
          <div className="relative space-y-4 before:absolute before:left-[19px] before:top-2 before:h-[calc(100%-1rem)] before:w-px before:bg-border">
            {filteredTrades.length > 0 ? (
              filteredTrades.map((trade, index) => (
                <TradeItem key={trade.id} trade={trade} isFirst={index === 0} />
              ))
            ) : (
              <div className="flex h-40 items-center justify-center">
                <p className="text-sm text-muted-foreground">
                  {trades.length === 0 
                    ? "No trades yet. Waiting for executions..."
                    : "No trades match the current filter"}
                </p>
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

interface TradeItemProps {
  trade: Trade;
  isFirst: boolean;
}

function TradeItem({ trade, isFirst }: TradeItemProps) {
  const statusConfig = {
    executed: {
      icon: CheckCircle,
      color: "text-success",
      bgColor: "bg-success/10",
      dotColor: "bg-success",
    },
    pending: {
      icon: Clock3,
      color: "text-warning",
      bgColor: "bg-warning/10",
      dotColor: "bg-warning",
    },
    failed: {
      icon: XCircle,
      color: "text-destructive",
      bgColor: "bg-destructive/10",
      dotColor: "bg-destructive",
    },
    cancelled: {
      icon: XCircle,
      color: "text-muted-foreground",
      bgColor: "bg-muted/10",
      dotColor: "bg-muted-foreground",
    },
  };

  const config = statusConfig[trade.status];
  const Icon = config.icon;
  const TypeIcon = trade.tradeType === "BUY" ? TrendingUp : TrendingDown;

  return (
    <div className="relative flex gap-4 pl-10">
      <div className={cn(
        "absolute left-2 h-9 w-9 rounded-full flex items-center justify-center border-2 border-background",
        config.bgColor,
        isFirst && "animate-pulse"
      )}>
        <div className={cn("h-2 w-2 rounded-full", config.dotColor)} />
      </div>

      <div className={cn(
        "flex-1 rounded-lg border border-border/60 p-4 transition-colors hover:bg-surface-muted/50",
        config.bgColor
      )}>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <TypeIcon className={cn(
                "h-4 w-4",
                trade.tradeType === "BUY" ? "text-success" : "text-destructive"
              )} />
              <span className="font-semibold text-foreground">{trade.symbol}</span>
              <Badge variant={trade.tradeType === "BUY" ? "success" : "destructive"}>
                {trade.tradeType}
              </Badge>
              <Badge variant="outline" className="text-xs">
                <Icon className={cn("h-3 w-3 mr-1", config.color)} />
                {trade.status}
              </Badge>
            </div>

            <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-muted-foreground">Quantity: </span>
                <span className="font-medium text-foreground">{trade.quantity.toFixed(2)}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Price: </span>
                <span className="font-medium text-foreground">{formatCurrency(trade.price)}</span>
              </div>
              <div className="col-span-2">
                <span className="text-muted-foreground">Total: </span>
                <span className="font-semibold text-foreground">{formatCurrency(trade.totalCost)}</span>
              </div>
            </div>

            {trade.decisionRationale && (
              <p className="mt-2 text-sm text-muted-foreground border-t border-border/40 pt-2">
                {trade.decisionRationale}
              </p>
            )}

            {trade.confidenceScore !== undefined && (
              <div className="mt-2 flex items-center gap-2">
                <span className="text-xs text-muted-foreground">Confidence:</span>
                <Badge variant="outline" className="text-xs">
                  {(trade.confidenceScore * 100).toFixed(0)}%
                </Badge>
              </div>
            )}
          </div>

          <span className="text-xs text-muted-foreground whitespace-nowrap">
            {formatDate(trade.executedAt)}
          </span>
        </div>
      </div>
    </div>
  );
}

function ConnectionIndicator({ isConnected }: { isConnected: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <div
        className={cn(
          "h-2 w-2 rounded-full",
          isConnected ? "bg-success animate-pulse" : "bg-muted-foreground"
        )}
      />
      <span className="text-xs text-muted-foreground">
        {isConnected ? "Live" : "Offline"}
      </span>
    </div>
  );
}
