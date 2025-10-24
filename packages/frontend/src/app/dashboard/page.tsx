"use client";

import { useState } from "react";
import { PortfolioOverview } from "@/components/dashboard/portfolio-overview";
import { LiveSignalFeed } from "@/components/dashboard/live-signal-feed";
import { TradeExecutionTimeline } from "@/components/dashboard/trade-execution-timeline";
import { AgentActivityStream } from "@/components/dashboard/agent-activity-stream";
import { DashboardControls, type TimeRange, type ViewMode } from "@/components/dashboard/dashboard-controls";
import { useRealtimePortfolio } from "@/lib/hooks/use-realtime-portfolio";
import { useRealtimeSignals } from "@/lib/hooks/use-realtime-signals";
import { useRealtimeTrades } from "@/lib/hooks/use-realtime-trades";
import { useRealtimeAgentActivity } from "@/lib/hooks/use-realtime-agent-activity";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function RealtimeDashboardPage() {
  const [portfolioId] = useState(1);
  const [timeRange, setTimeRange] = useState<TimeRange>("1d");
  const [viewMode, setViewMode] = useState<ViewMode>("overview");

  const portfolio = useRealtimePortfolio({ portfolioId, enabled: true });
  const signals = useRealtimeSignals({ portfolioId, enabled: true });
  const trades = useRealtimeTrades({ portfolioId, enabled: true });
  const agentActivity = useRealtimeAgentActivity({ enabled: true });

  const handleRefresh = () => {
    window.location.reload();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Real-Time Trading Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor portfolio performance, signals, trades, and agent activity in real-time
          </p>
        </div>

        <DashboardControls
          timeRange={timeRange}
          onTimeRangeChange={setTimeRange}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          onRefresh={handleRefresh}
        />
      </div>

      {viewMode === "overview" ? (
        <div className="space-y-6">
          <PortfolioOverview 
            data={portfolio.data} 
            isConnected={portfolio.isConnected} 
          />

          <div className="grid gap-6 lg:grid-cols-2">
            <LiveSignalFeed 
              signals={signals.signals} 
              isConnected={signals.isConnected} 
            />
            <TradeExecutionTimeline 
              trades={trades.trades} 
              isConnected={trades.isConnected} 
            />
          </div>

          <AgentActivityStream 
            activities={agentActivity.activities} 
            isConnected={agentActivity.isConnected} 
          />
        </div>
      ) : (
        <Tabs defaultValue="portfolio" className="space-y-4">
          <TabsList>
            <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
            <TabsTrigger value="signals">Signals</TabsTrigger>
            <TabsTrigger value="trades">Trades</TabsTrigger>
            <TabsTrigger value="agents">Agent Activity</TabsTrigger>
          </TabsList>

          <TabsContent value="portfolio" className="space-y-4">
            <PortfolioOverview 
              data={portfolio.data} 
              isConnected={portfolio.isConnected} 
            />
          </TabsContent>

          <TabsContent value="signals" className="space-y-4">
            <LiveSignalFeed 
              signals={signals.signals} 
              isConnected={signals.isConnected} 
            />
          </TabsContent>

          <TabsContent value="trades" className="space-y-4">
            <TradeExecutionTimeline 
              trades={trades.trades} 
              isConnected={trades.isConnected} 
            />
          </TabsContent>

          <TabsContent value="agents" className="space-y-4">
            <AgentActivityStream 
              activities={agentActivity.activities} 
              isConnected={agentActivity.isConnected} 
            />
          </TabsContent>
        </Tabs>
      )}

      {(portfolio.error || signals.error || trades.error || agentActivity.error) && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <h3 className="font-semibold text-destructive">Connection Error</h3>
          <p className="text-sm text-destructive/80 mt-1">
            {portfolio.error?.message || 
             signals.error?.message || 
             trades.error?.message || 
             agentActivity.error?.message || 
             "Failed to connect to real-time data stream"}
          </p>
        </div>
      )}
    </div>
  );
}
