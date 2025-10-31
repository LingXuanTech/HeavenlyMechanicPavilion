"use client";

import { useState, useEffect } from "react";
import { PortfolioOverview } from "@/components/dashboard/portfolio-overview";
import { LiveSignalFeed } from "@/components/dashboard/live-signal-feed";
import { TradeExecutionTimeline } from "@/components/dashboard/trade-execution-timeline";
import { AgentActivityStream } from "@/components/dashboard/agent-activity-stream";
import { DashboardControls, type TimeRange, type ViewMode } from "@/components/dashboard/dashboard-controls";
import { useRealtimeStore } from "@/lib/store/use-realtime-store";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function RealtimeDashboardPage() {
  const [portfolioId] = useState(1);
  const [timeRange, setTimeRange] = useState<TimeRange>("1d");
  const [viewMode, setViewMode] = useState<ViewMode>("overview");

  // Zustand selectors for optimal re-renders
  const portfolio = useRealtimeStore((state) => state.portfolio);
  const portfolioConnected = useRealtimeStore((state) => state.portfolioConnected);
  const portfolioError = useRealtimeStore((state) => state.portfolioError);

  const signals = useRealtimeStore((state) => state.signals);
  const signalsConnected = useRealtimeStore((state) => state.signalsConnected);
  const signalsError = useRealtimeStore((state) => state.signalsError);

  const trades = useRealtimeStore((state) => state.trades);
  const tradesConnected = useRealtimeStore((state) => state.tradesConnected);
  const tradesError = useRealtimeStore((state) => state.tradesError);

  const agentActivities = useRealtimeStore((state) => state.agentActivities);
  const agentActivitiesConnected = useRealtimeStore((state) => state.agentActivitiesConnected);
  const agentActivitiesError = useRealtimeStore((state) => state.agentActivitiesError);

  // Connection management actions
  const connectPortfolio = useRealtimeStore((state) => state.connectPortfolio);
  const connectSignals = useRealtimeStore((state) => state.connectSignals);
  const connectTrades = useRealtimeStore((state) => state.connectTrades);
  const connectAgentActivities = useRealtimeStore((state) => state.connectAgentActivities);
  const disconnectAll = useRealtimeStore((state) => state.disconnectAll);

  // Connect to all streams on mount
  useEffect(() => {
    connectPortfolio(portfolioId);
    connectSignals(portfolioId);
    connectTrades(portfolioId);
    connectAgentActivities();

    // Cleanup on unmount
    return () => {
      disconnectAll();
    };
  }, [portfolioId, connectPortfolio, connectSignals, connectTrades, connectAgentActivities, disconnectAll]);

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
            data={portfolio}
            isConnected={portfolioConnected}
          />

          <div className="grid gap-6 lg:grid-cols-2">
            <LiveSignalFeed
              signals={signals}
              isConnected={signalsConnected}
            />
            <TradeExecutionTimeline
              trades={trades}
              isConnected={tradesConnected}
            />
          </div>

          <AgentActivityStream
            activities={agentActivities}
            isConnected={agentActivitiesConnected}
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
              data={portfolio}
              isConnected={portfolioConnected}
            />
          </TabsContent>

          <TabsContent value="signals" className="space-y-4">
            <LiveSignalFeed
              signals={signals}
              isConnected={signalsConnected}
            />
          </TabsContent>

          <TabsContent value="trades" className="space-y-4">
            <TradeExecutionTimeline
              trades={trades}
              isConnected={tradesConnected}
            />
          </TabsContent>

          <TabsContent value="agents" className="space-y-4">
            <AgentActivityStream
              activities={agentActivities}
              isConnected={agentActivitiesConnected}
            />
          </TabsContent>
        </Tabs>
      )}

      {(portfolioError || signalsError || tradesError || agentActivitiesError) && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <h3 className="font-semibold text-destructive">Connection Error</h3>
          <p className="text-sm text-destructive/80 mt-1">
            {portfolioError?.message ||
             signalsError?.message ||
             tradesError?.message ||
             agentActivitiesError?.message ||
             "Failed to connect to real-time data stream"}
          </p>
        </div>
      )}
    </div>
  );
}
