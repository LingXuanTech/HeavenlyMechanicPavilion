"use client";

import { useState } from "react";
import { TrendingUp, TrendingDown, AlertCircle, Filter } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { formatDate } from "@tradingagents/shared/utils/format";
import type { TradingSignal } from "@tradingagents/shared/domain";

interface LiveSignalFeedProps {
  signals: TradingSignal[];
  isConnected: boolean;
}

type SignalFilter = "all" | "buy" | "sell" | "hold";

export function LiveSignalFeed({ signals, isConnected }: LiveSignalFeedProps) {
  const [filter, setFilter] = useState<SignalFilter>("all");

  const filteredSignals = signals.filter(signal => {
    if (filter === "all") return true;
    return signal.signal === filter;
  });

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-primary" />
              Live Signal Feed
            </CardTitle>
            <CardDescription>
              Real-time trading signals from analysis ({filteredSignals.length} signals)
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <ConnectionIndicator isConnected={isConnected} />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="mb-4 flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select value={filter} onValueChange={(value) => setFilter(value as SignalFilter)}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter signals" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Signals</SelectItem>
              <SelectItem value="buy">Buy Only</SelectItem>
              <SelectItem value="sell">Sell Only</SelectItem>
              <SelectItem value="hold">Hold Only</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <ScrollArea className="h-[600px]">
          <div className="space-y-3">
            {filteredSignals.length > 0 ? (
              filteredSignals.map((signal) => (
                <SignalCard key={signal.id} signal={signal} />
              ))
            ) : (
              <div className="flex h-40 items-center justify-center">
                <p className="text-sm text-muted-foreground">
                  {signals.length === 0 
                    ? "No signals yet. Waiting for new signals..."
                    : "No signals match the current filter"}
                </p>
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

interface SignalCardProps {
  signal: TradingSignal;
}

function SignalCard({ signal }: SignalCardProps) {
  const signalConfig = {
    buy: {
      icon: TrendingUp,
      color: "text-success",
      bgColor: "bg-success/10",
      variant: "success" as const,
    },
    sell: {
      icon: TrendingDown,
      color: "text-destructive",
      bgColor: "bg-destructive/10",
      variant: "destructive" as const,
    },
    hold: {
      icon: AlertCircle,
      color: "text-warning",
      bgColor: "bg-warning/10",
      variant: "warning" as const,
    },
  };

  const config = signalConfig[signal.signal];
  const Icon = config.icon;

  return (
    <div className={cn(
      "rounded-lg border border-border/60 p-4 transition-colors hover:bg-surface-muted/50",
      config.bgColor
    )}>
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <Icon className={cn("h-5 w-5 mt-0.5", config.color)} />
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-foreground">{signal.symbol}</span>
              <Badge variant={config.variant}>{signal.signal.toUpperCase()}</Badge>
              <Badge variant="outline" className="text-xs">
                Strength: {(signal.strength * 100).toFixed(0)}%
              </Badge>
            </div>
            <div className="mt-1 text-sm text-muted-foreground">
              Price: ${signal.price.toFixed(2)} • Source: {signal.source}
            </div>
            {signal.rationale && (
              <p className="mt-2 text-sm text-foreground/80">{signal.rationale}</p>
            )}
            {signal.indicators && Object.keys(signal.indicators).length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {Object.entries(signal.indicators).map(([key, value]) => (
                  <span key={key} className="text-xs text-muted-foreground">
                    {key}: {typeof value === "number" ? value.toFixed(2) : value}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
        <span className="text-xs text-muted-foreground whitespace-nowrap">
          {formatDate(signal.timestamp)}
        </span>
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
