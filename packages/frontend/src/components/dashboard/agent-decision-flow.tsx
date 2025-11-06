"use client";

import { useState } from "react";
import { Brain, TrendingUp, TrendingDown, Scale, Shield, ChevronDown, ChevronUp } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

interface AgentState {
  // 分析师报告
  market_report?: string;
  news_report?: string;
  fundamentals_report?: string;
  sentiment_report?: string;
  
  // 辩论历史
  investment_debate_state?: {
    bull_history: string[];
    bear_history: string[];
    judge_decision?: string;
  };
  
  risk_debate_state?: {
    risky_history: string[];
    neutral_history: string[];
    safe_history: string[];
    judge_decision?: string;
  };
  
  // 最终决策
  final_trade_decision?: string;
  processed_signal?: string;
  confidence_score?: number;
  trader_investment_plan?: string;
}

interface AgentDecisionFlowProps {
  sessionId: string;
  state: AgentState;
}

export function AgentDecisionFlow({ sessionId, state }: AgentDecisionFlowProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Brain className="h-5 w-5 text-primary" />
          Agent 决策流程
        </CardTitle>
        <CardDescription>
          多层 Agent 分析和决策过程 - Session: {sessionId}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[800px]">
          <div className="space-y-6">
            {/* 第一层: 分析师报告 */}
            <Section title="1. 专业分析" icon={Brain}>
              <div className="grid gap-4 md:grid-cols-2">
                <AnalystCard
                  name="市场分析师"
                  report={state.market_report}
                  sentiment="neutral"
                  icon="chart"
                />
                <AnalystCard
                  name="新闻分析师"
                  report={state.news_report}
                  sentiment="positive"
                  icon="news"
                />
                <AnalystCard
                  name="基本面分析师"
                  report={state.fundamentals_report}
                  sentiment="positive"
                  icon="fundamentals"
                />
                <AnalystCard
                  name="社交情绪分析师"
                  report={state.sentiment_report}
                  sentiment="negative"
                  icon="social"
                />
              </div>
            </Section>

            {/* 第二层: 投资辩论 */}
            {state.investment_debate_state && (
              <Section title="2. 投资辩论 (牛 vs 熊)" icon={Scale}>
                <DebateView
                  bullArguments={state.investment_debate_state.bull_history}
                  bearArguments={state.investment_debate_state.bear_history}
                  judgeDecision={state.investment_debate_state.judge_decision}
                />
              </Section>
            )}

            {/* 第三层: 风险辩论 */}
            {state.risk_debate_state && (
              <Section title="3. 风险评估 (激进/中性/保守)" icon={Shield}>
                <RiskDebateView
                  riskyView={state.risk_debate_state.risky_history}
                  neutralView={state.risk_debate_state.neutral_history}
                  safeView={state.risk_debate_state.safe_history}
                  finalAssessment={state.risk_debate_state.judge_decision}
                />
              </Section>
            )}

            {/* 第四层: 最终决策 */}
            {state.final_trade_decision && (
              <Section title="4. 最终交易决策" icon={TrendingUp}>
                <FinalDecisionCard
                  decision={state.final_trade_decision}
                  signal={state.processed_signal}
                  confidence={state.confidence_score}
                  rationale={state.trader_investment_plan}
                />
              </Section>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

interface SectionProps {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
}

function Section({ title, icon: Icon, children }: SectionProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div className="rounded-lg border border-border/60 bg-surface/50 p-4">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center justify-between text-left hover:opacity-80"
      >
        <h3 className="flex items-center gap-2 text-lg font-semibold text-foreground">
          <Icon className="h-5 w-5 text-primary" />
          {title}
        </h3>
        {isExpanded ? (
          <ChevronUp className="h-5 w-5 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-5 w-5 text-muted-foreground" />
        )}
      </button>
      {isExpanded && <div className="mt-4">{children}</div>}
    </div>
  );
}

interface AnalystCardProps {
  name: string;
  report?: string;
  sentiment: "positive" | "negative" | "neutral";
  icon: "chart" | "news" | "fundamentals" | "social";
}

function AnalystCard({ name, report, sentiment, icon }: AnalystCardProps) {
  const sentimentConfig = {
    positive: {
      color: "text-success",
      bgColor: "bg-success/10",
      label: "看涨",
    },
    negative: {
      color: "text-destructive",
      bgColor: "bg-destructive/10",
      label: "看跌",
    },
    neutral: {
      color: "text-warning",
      bgColor: "bg-warning/10",
      label: "中性",
    },
  };

  const config = sentimentConfig[sentiment];

  return (
    <div className={cn("rounded-lg border border-border/60 p-4", config.bgColor)}>
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold text-foreground">{name}</span>
        <Badge variant="outline" className={cn(config.color, config.bgColor)}>
          {config.label}
        </Badge>
      </div>
      <p className="text-sm text-foreground/80 line-clamp-4">
        {report || "分析进行中..."}
      </p>
    </div>
  );
}

interface DebateViewProps {
  bullArguments: string[];
  bearArguments: string[];
  judgeDecision?: string;
}

function DebateView({ bullArguments, bearArguments, judgeDecision }: DebateViewProps) {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        {/* 看涨观点 */}
        <div className="rounded-lg border border-border/60 bg-success/5 p-4">
          <div className="mb-3 flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-success" />
            <span className="font-semibold text-success">看涨研究员</span>
            <Badge variant="outline" className="text-success bg-success/10">
              {bullArguments.length} 轮
            </Badge>
          </div>
          <div className="space-y-2">
            {bullArguments.slice(0, 3).map((arg, i) => (
              <div key={i} className="text-sm text-foreground/80 border-l-2 border-success/30 pl-3">
                {arg}
              </div>
            ))}
          </div>
        </div>

        {/* 看跌观点 */}
        <div className="rounded-lg border border-border/60 bg-destructive/5 p-4">
          <div className="mb-3 flex items-center gap-2">
            <TrendingDown className="h-5 w-5 text-destructive" />
            <span className="font-semibold text-destructive">看跌研究员</span>
            <Badge variant="outline" className="text-destructive bg-destructive/10">
              {bearArguments.length} 轮
            </Badge>
          </div>
          <div className="space-y-2">
            {bearArguments.slice(0, 3).map((arg, i) => (
              <div key={i} className="text-sm text-foreground/80 border-l-2 border-destructive/30 pl-3">
                {arg}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 研究经理判断 */}
      {judgeDecision && (
        <div className="rounded-lg border border-primary/60 bg-primary/5 p-4">
          <div className="mb-2 flex items-center gap-2">
            <Scale className="h-5 w-5 text-primary" />
            <span className="font-semibold text-primary">研究经理综合判断</span>
          </div>
          <p className="text-sm text-foreground/90">{judgeDecision}</p>
        </div>
      )}
    </div>
  );
}

interface RiskDebateViewProps {
  riskyView: string[];
  neutralView: string[];
  safeView: string[];
  finalAssessment?: string;
}

function RiskDebateView({ riskyView, neutralView, safeView, finalAssessment }: RiskDebateViewProps) {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-3">
        {/* 激进观点 */}
        <div className="rounded-lg border border-border/60 bg-orange-500/5 p-4">
          <div className="mb-3 flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-orange-500" />
            <span className="font-semibold text-orange-500">激进派</span>
          </div>
          <div className="space-y-2">
            {riskyView.slice(0, 2).map((view, i) => (
              <p key={i} className="text-xs text-foreground/70 line-clamp-3">
                {view}
              </p>
            ))}
          </div>
        </div>

        {/* 中性观点 */}
        <div className="rounded-lg border border-border/60 bg-blue-500/5 p-4">
          <div className="mb-3 flex items-center gap-2">
            <Scale className="h-5 w-5 text-blue-500" />
            <span className="font-semibold text-blue-500">中性派</span>
          </div>
          <div className="space-y-2">
            {neutralView.slice(0, 2).map((view, i) => (
              <p key={i} className="text-xs text-foreground/70 line-clamp-3">
                {view}
              </p>
            ))}
          </div>
        </div>

        {/* 保守观点 */}
        <div className="rounded-lg border border-border/60 bg-purple-500/5 p-4">
          <div className="mb-3 flex items-center gap-2">
            <Shield className="h-5 w-5 text-purple-500" />
            <span className="font-semibold text-purple-500">保守派</span>
          </div>
          <div className="space-y-2">
            {safeView.slice(0, 2).map((view, i) => (
              <p key={i} className="text-xs text-foreground/70 line-clamp-3">
                {view}
              </p>
            ))}
          </div>
        </div>
      </div>

      {/* 风险经理最终评估 */}
      {finalAssessment && (
        <div className="rounded-lg border border-primary/60 bg-primary/5 p-4">
          <div className="mb-2 flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            <span className="font-semibold text-primary">风险经理最终评估</span>
          </div>
          <p className="text-sm text-foreground/90">{finalAssessment}</p>
        </div>
      )}
    </div>
  );
}

interface FinalDecisionCardProps {
  decision: string;
  signal?: string;
  confidence?: number;
  rationale?: string;
}

function FinalDecisionCard({ decision, signal, confidence, rationale }: FinalDecisionCardProps) {
  const signalConfig = {
    BUY: {
      color: "text-success",
      bgColor: "bg-success/10",
      icon: TrendingUp,
    },
    SELL: {
      color: "text-destructive",
      bgColor: "bg-destructive/10",
      icon: TrendingDown,
    },
    HOLD: {
      color: "text-warning",
      bgColor: "bg-warning/10",
      icon: Scale,
    },
  };

  const config = signal ? signalConfig[signal as keyof typeof signalConfig] : signalConfig.HOLD;
  const Icon = config.icon;

  return (
    <div className={cn("rounded-lg border border-border/60 p-6", config.bgColor)}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <Icon className={cn("h-8 w-8", config.color)} />
          <div>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-foreground">{signal || "HOLD"}</span>
              {confidence !== undefined && (
                <Badge variant="outline" className={cn(config.color, config.bgColor)}>
                  置信度: {(confidence * 100).toFixed(0)}%
                </Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground">交易员最终决策</p>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        <div className="rounded-lg bg-background/50 p-4">
          <h4 className="mb-2 text-sm font-semibold text-foreground">决策理由</h4>
          <p className="text-sm text-foreground/80">{decision}</p>
        </div>

        {rationale && (
          <div className="rounded-lg bg-background/50 p-4">
            <h4 className="mb-2 text-sm font-semibold text-foreground">投资计划</h4>
            <p className="text-sm text-foreground/80">{rationale}</p>
          </div>
        )}
      </div>
    </div>
  );
}