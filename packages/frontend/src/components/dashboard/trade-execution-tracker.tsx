"use client";

import { useState, useEffect } from "react";
import { Clock, CheckCircle, XCircle, AlertCircle, TrendingUp, TrendingDown } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { formatDate, formatCurrency } from "@tradingagents/shared/utils/format";

interface TradeExecutionStep {
  step: string;
  status: "completed" | "in-progress" | "pending" | "failed";
  timestamp?: string;
  message: string;
  details?: Record<string, unknown>;
}

interface TradeExecutionTrackerProps {
  tradeId: number;
  symbol: string;
  action: string;
  steps?: TradeExecutionStep[];
}

export function TradeExecutionTracker({ 
  tradeId, 
  symbol, 
  action,
  steps: initialSteps 
}: TradeExecutionTrackerProps) {
  const [steps, setSteps] = useState<TradeExecutionStep[]>(
    initialSteps || [
      {
        step: "agent_analysis",
        status: "completed",
        timestamp: new Date().toISOString(),
        message: `Agent 分析完成 - 决策: ${action} ${symbol}`,
      },
      {
        step: "risk_check",
        status: "in-progress",
        message: "风险检查进行中...",
      },
      {
        step: "order_submission",
        status: "pending",
        message: "等待订单提交",
      },
      {
        step: "order_confirmation",
        status: "pending",
        message: "等待成交确认",
      },
    ]
  );

  const statusConfig = {
    completed: {
      icon: CheckCircle,
      color: "text-success",
      bgColor: "bg-success/10",
      borderColor: "border-success/30",
    },
    "in-progress": {
      icon: Clock,
      color: "text-warning",
      bgColor: "bg-warning/10",
      borderColor: "border-warning/30",
    },
    pending: {
      icon: AlertCircle,
      color: "text-muted-foreground",
      bgColor: "bg-muted/10",
      borderColor: "border-muted/30",
    },
    failed: {
      icon: XCircle,
      color: "text-destructive",
      bgColor: "bg-destructive/10",
      borderColor: "border-destructive/30",
    },
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-primary" />
              订单执行追踪
            </CardTitle>
            <CardDescription>
              Trade ID: {tradeId} - {action} {symbol}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {action === "BUY" ? (
              <TrendingUp className="h-5 w-5 text-success" />
            ) : (
              <TrendingDown className="h-5 w-5 text-destructive" />
            )}
            <Badge variant={action === "BUY" ? "success" : "destructive"}>
              {action}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {steps.map((step, index) => {
            const config = statusConfig[step.status];
            const Icon = config.icon;
            const isLast = index === steps.length - 1;

            return (
              <div key={step.step} className="relative">
                {/* 连接线 */}
                {!isLast && (
                  <div className={cn(
                    "absolute left-[19px] top-10 h-full w-px",
                    step.status === "completed" ? "bg-success/30" : "bg-border"
                  )} />
                )}

                {/* 时间线节点 */}
                <div className="flex gap-4">
                  <div className={cn(
                    "relative flex h-10 w-10 items-center justify-center rounded-full border-2",
                    config.bgColor,
                    config.borderColor,
                    step.status === "in-progress" && "animate-pulse"
                  )}>
                    <Icon className={cn("h-5 w-5", config.color)} />
                  </div>

                  {/* 内容 */}
                  <div className="flex-1 pb-8">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-foreground">
                            {step.message}
                          </span>
                          <Badge 
                            variant="outline" 
                            className={cn("text-xs", config.color, config.bgColor)}
                          >
                            {step.status}
                          </Badge>
                        </div>
                        {step.timestamp && (
                          <span className="text-xs text-muted-foreground">
                            {formatDate(step.timestamp)}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* 详细信息 */}
                    {step.details && Object.keys(step.details).length > 0 && (
                      <div className="mt-2 rounded-lg bg-surface/50 p-3">
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          {Object.entries(step.details).map(([key, value]) => (
                            <div key={key}>
                              <span className="text-muted-foreground">{key}: </span>
                              <span className="font-medium text-foreground">
                                {typeof value === "number" && key.includes("price")
                                  ? formatCurrency(value)
                                  : String(value)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

// 用于实时更新的 Hook
export function useTradeExecutionTracker(tradeId: number) {
  const [steps, setSteps] = useState<TradeExecutionStep[]>([]);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    // TODO: 连接到 SSE 或 WebSocket 接收实时更新
    // 这里是模拟实现
    const simulateProgress = async () => {
      const progressSteps: TradeExecutionStep[] = [
        {
          step: "agent_analysis",
          status: "completed",
          timestamp: new Date().toISOString(),
          message: "Agent 分析完成",
          details: { confidence: "85%", signal: "BUY" },
        },
      ];

      setSteps([...progressSteps]);

      // 模拟延迟
      await new Promise(resolve => setTimeout(resolve, 1000));

      progressSteps.push({
        step: "risk_check",
        status: "completed",
        timestamp: new Date().toISOString(),
        message: "风险检查通过",
        details: { position_size: "2.5%", buying_power: "充足" },
      });
      setSteps([...progressSteps]);

      await new Promise(resolve => setTimeout(resolve, 1000));

      progressSteps.push({
        step: "order_submission",
        status: "completed",
        timestamp: new Date().toISOString(),
        message: "订单已提交",
        details: { order_id: "abc123", broker: "Alpaca" },
      });
      setSteps([...progressSteps]);

      await new Promise(resolve => setTimeout(resolve, 2000));

      progressSteps.push({
        step: "order_confirmation",
        status: "completed",
        timestamp: new Date().toISOString(),
        message: "订单已成交",
        details: { fill_price: "$150.25", quantity: "10" },
      });
      setSteps([...progressSteps]);
      setIsComplete(true);
    };

    simulateProgress();
  }, [tradeId]);

  return { steps, isComplete };
}