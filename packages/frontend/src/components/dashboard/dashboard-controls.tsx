"use client";

import { Calendar, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

export type TimeRange = "1h" | "4h" | "1d" | "1w" | "1m" | "all";
export type ViewMode = "overview" | "detailed";

interface DashboardControlsProps {
  timeRange: TimeRange;
  onTimeRangeChange: (range: TimeRange) => void;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export function DashboardControls({
  timeRange,
  onTimeRangeChange,
  viewMode,
  onViewModeChange,
  onRefresh,
  isRefreshing = false,
}: DashboardControlsProps) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-2">
        <Calendar className="h-4 w-4 text-muted-foreground" />
        <Select value={timeRange} onValueChange={(value) => onTimeRangeChange(value as TimeRange)}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Select time range" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="1h">Last Hour</SelectItem>
            <SelectItem value="4h">Last 4 Hours</SelectItem>
            <SelectItem value="1d">Last Day</SelectItem>
            <SelectItem value="1w">Last Week</SelectItem>
            <SelectItem value="1m">Last Month</SelectItem>
            <SelectItem value="all">All Time</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center gap-4">
        <Tabs value={viewMode} onValueChange={(value) => onViewModeChange(value as ViewMode)}>
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="detailed">Detailed</TabsTrigger>
          </TabsList>
        </Tabs>

        {onRefresh && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={isRefreshing}
            className="gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        )}
      </div>
    </div>
  );
}
