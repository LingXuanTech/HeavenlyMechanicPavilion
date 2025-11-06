"use client";

import { Trophy, TrendingUp, Target, Brain } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { formatPercent, formatCurrency } from "@tradingagents/shared/utils/format";

interface AgentPerformance {
  agentName: string;
  agentRole: string;
  accuracy: number;
  avgReturn: number;
  winRate: number;
  totalDecisions: number;
  successfulDecisions: number;
  avgConfidence: number;
}

interface AgentPerformanceComparisonProps {
  performances?: AgentPerformance[];
}

export function AgentPerformanceComparison({ 
  performances: initialPerformances 
}: AgentPerformanceComparisonProps) {
  // 模拟数据（实际应该从 API 获取）
  const performances = initialPerformances || generateMockPerformances();

  // 按准确率排序
  const sortedPerformances = [...performances].sort((a, b) => b.accuracy - a.accuracy);

  // 找出最佳表现者
  const bestPerformer = sortedPerformances[0];
  const bestReturn = performances.reduce((max, p) => p.avgReturn > max.avgReturn ? p : max);
  const mostConsistent = performances.reduce((max, p) => p.winRate > max.winRate ? p : max);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Trophy className="h-5 w-5 text-primary" />
              Agent 表现对比
            </CardTitle>
            <CardDescription>
              各 Agent 的历史决策质量和收益贡献分析
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* 顶部统计卡片 */}
        <div className="mb-6 grid gap-4 md:grid-cols-3">
          <TopPerformerCard
            title="最高准确率"
            agentName={bestPerformer.agentName}
            value={formatPercent(bestPerformer.accuracy / 100)}
            icon={Target}
          />
          <TopPerformerCard
            title="最佳收益"
            agentName={bestReturn.agentName}
            value={`+${bestReturn.avgReturn.toFixed(2)}%`}
            icon={TrendingUp}
          />
          <TopPerformerCard
            title="最稳定表现"
            agentName={mostConsistent.agentName}
            value={formatPercent(mostConsistent.winRate / 100)}
            icon={Brain}
          />
        </div>

        {/* 详细表格 */}
        <div className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Agent</TableHead>
                <TableHead>角色</TableHead>
                <TableHead className="text-right">准确率</TableHead>
                <TableHead className="text-right">平均收益</TableHead>
                <TableHead className="text-right">胜率</TableHead>
                <TableHead className="text-right">决策次数</TableHead>
                <TableHead className="text-right">平均置信度</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedPerformances.map((performance, index) => (
                <TableRow key={performance.agentName}>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {index < 3 && (
                        <Trophy className={cn(
                          "h-4 w-4",
                          index === 0 && "text-yellow-500",
                          index === 1 && "text-gray-400",
                          index === 2 && "text-orange-600"
                        )} />
                      )}
                      <span className="font-medium">{performance.agentName}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{performance.agentRole}</Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <span className={cn(
                      "font-medium",
                      performance.accuracy >= 70 ? "text-success" : 
                      performance.accuracy >= 60 ? "text-warning" : "text-destructive"
                    )}>
                      {performance.accuracy.toFixed(1)}%
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <span className={cn(
                      "font-medium",
                      performance.avgReturn >= 0 ? "text-success" : "text-destructive"
                    )}>
                      {performance.avgReturn >= 0 ? "+" : ""}{performance.avgReturn.toFixed(2)}%
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <span className="font-medium">
                      {performance.winRate.toFixed(1)}%
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="text-sm">
                      <div className="font-medium">{performance.totalDecisions}</div>
                      <div className="text-muted-foreground">
                        ({performance.successfulDecisions} 成功)
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <div className="h-2 w-16 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full bg-primary transition-all"
                          style={{ width: `${performance.avgConfidence}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium">
                        {performance.avgConfidence.toFixed(0)}%
                      </span>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* 说明文字 */}
        <div className="mt-4 rounded-lg bg-muted/50 p-4">
          <h4 className="mb-2 text-sm font-semibold text-foreground">指标说明</h4>
          <div className="grid gap-2 text-xs text-muted-foreground md:grid-cols-2">
            <div>
              <span className="font-medium">准确率:</span> Agent 决策与实际市场走势的匹配度
            </div>
            <div>
              <span className="font-medium">平均收益:</span> 基于 Agent 建议的平均投资回报率
            </div>
            <div>
              <span className="font-medium">胜率:</span> Agent 成功决策占总决策的比例
            </div>
            <div>
              <span className="font-medium">平均置信度:</span> Agent 对自身决策的平均信心水平
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface TopPerformerCardProps {
  title: string;
  agentName: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
}

function TopPerformerCard({ title, agentName, value, icon: Icon }: TopPerformerCardProps) {
  return (
    <div className="rounded-lg border border-border bg-surface/50 p-4">
      <div className="mb-2 flex items-center gap-2">
        <Icon className="h-4 w-4 text-primary" />
        <span className="text-sm font-medium text-muted-foreground">{title}</span>
      </div>
      <div className="text-2xl font-bold text-foreground">{value}</div>
      <div className="mt-1 text-sm text-muted-foreground">{agentName}</div>
    </div>
  );
}

function generateMockPerformances(): AgentPerformance[] {
  const agents = [
    { name: "市场分析师", role: "Analyst", baseAccuracy: 72 },
    { name: "新闻分析师", role: "Analyst", baseAccuracy: 68 },
    { name: "基本面分析师", role: "Analyst", baseAccuracy: 75 },
    { name: "社交情绪分析师", role: "Analyst", baseAccuracy: 64 },
    { name: "看涨研究员", role: "Researcher", baseAccuracy: 70 },
    { name: "看跌研究员", role: "Researcher", baseAccuracy: 69 },
    { name: "研究经理", role: "Manager", baseAccuracy: 78 },
    { name: "风险经理", role: "Risk Manager", baseAccuracy: 80 },
    { name: "交易员", role: "Trader", baseAccuracy: 76 },
  ];

  return agents.map((agent) => {
    const accuracy = agent.baseAccuracy + (Math.random() - 0.5) * 4;
    const avgReturn = (accuracy - 50) * 0.1 + (Math.random() - 0.5) * 2;
    const winRate = accuracy * 0.85 + Math.random() * 5;
    const totalDecisions = Math.floor(100 + Math.random() * 200);
    const successfulDecisions = Math.floor(totalDecisions * (winRate / 100));
    const avgConfidence = 60 + Math.random() * 30;

    return {
      agentName: agent.name,
      agentRole: agent.role,
      accuracy,
      avgReturn,
      winRate,
      totalDecisions,
      successfulDecisions,
      avgConfidence,
    };
  });
}