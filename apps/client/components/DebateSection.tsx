/**
 * DebateSection - 多空辩论区域
 *
 * 从 StockDetailModal 拆分，包含：
 * - DebateMeter: 多空力量对比条
 * - Bull/Bear Agent 卡片
 * - Moderator 结论
 */
import React, { memo } from 'react';
import type * as T from '../src/types/schema';
import { TrendingUp, TrendingDown, Bot, Gavel } from 'lucide-react';

// ============ DebateMeter ============

/** 辩论计组件 - 基于论点权重计算多空力量 */
const DebateMeter: React.FC<{ debate: T.ResearcherDebate }> = ({ debate }) => {
  if (!debate) return null;

  const weightMap: Record<string, number> = { High: 3, Medium: 2, Low: 1 };

  const bullScore = (debate.bull.points || []).reduce(
    (sum: number, p: T.DebatePoint) => sum + (weightMap[p.weight] || 1), 0
  );
  const bearScore = (debate.bear.points || []).reduce(
    (sum: number, p: T.DebatePoint) => sum + (weightMap[p.weight] || 1), 0
  );

  const total = bullScore + bearScore;
  const bullPercent = total > 0 ? Math.round((bullScore / total) * 100) : 50;

  return (
    <div className="space-y-2">
      {/* 标签行 */}
      <div className="flex justify-between text-xs">
        <span className="text-green-400 font-bold">Bull {bullPercent}%</span>
        <span className="text-red-400 font-bold">Bear {100 - bullPercent}%</span>
      </div>

      {/* 力量条 */}
      <div className="relative h-3 bg-surface-overlay rounded-full overflow-hidden">
        <div
          className="absolute left-0 top-0 h-full bg-gradient-to-r from-green-600 to-green-400 transition-all duration-1000 ease-out"
          style={{ width: `${bullPercent}%` }}
        />
        <div
          className="absolute right-0 top-0 h-full bg-gradient-to-l from-red-600 to-red-400"
          style={{ width: `${100 - bullPercent}%` }}
        />
        <div className="absolute top-0 bottom-0 left-1/2 w-0.5 bg-white/30 -translate-x-1/2 z-10" />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-1 h-5 bg-yellow-400 rounded-full shadow-[0_0_8px_rgba(250,204,21,0.8)] transition-all duration-1000 z-20"
          style={{ left: `${bullPercent}%`, transform: 'translate(-50%, -50%)' }}
        />
      </div>

      {/* 赢家标记 */}
      <div className="text-center">
        <span className={`text-xs font-bold px-3 py-1 rounded-full ${
          debate.winner === 'Bull' ? 'bg-green-500/20 text-green-400' :
          debate.winner === 'Bear' ? 'bg-red-500/20 text-red-400' :
          'bg-stone-500/20 text-stone-400'
        }`}>
          {debate.winner === 'Bull' ? '🐮 多方胜出' : debate.winner === 'Bear' ? '🐻 空方胜出' : '⚖️ 势均力敌'}
        </span>
      </div>
    </div>
  );
};

// ============ DebateSection ============

interface DebateSectionProps {
  debate: T.ResearcherDebate;
}

const DebateSection: React.FC<DebateSectionProps> = memo(({ debate }) => {
  if (!debate) return null;

  return (
    <div className="space-y-4 mt-6">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Gavel className="w-5 h-5 text-orange-400" />
          <h3 className="text-lg font-bold text-white">Researcher Team Debate</h3>
        </div>
      </div>

      <DebateMeter debate={debate} />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Bull Agent Card */}
        <div className={`bg-green-950/20 border rounded-lg p-4 relative overflow-hidden transition-all ${
          debate.winner === 'Bull' ? 'border-green-500/60 shadow-[0_0_15px_rgba(34,197,94,0.1)]' : 'border-green-900/40'
        }`}>
          <div className="absolute top-0 right-0 p-2 opacity-10">
            <TrendingUp className="w-24 h-24 text-green-500" />
          </div>
          <div className="flex justify-between items-start mb-3 border-b border-green-900/30 pb-2">
            <h4 className="text-green-400 font-bold flex items-center gap-2">
              <Bot className="w-4 h-4" /> Bull Agent
            </h4>
            {debate.winner === 'Bull' && (
              <span className="text-[10px] bg-green-500 text-black px-1.5 py-0.5 rounded font-bold uppercase">Winner</span>
            )}
          </div>
          <p className="text-sm font-semibold text-green-100 mb-3 italic leading-relaxed">"{debate.bull.thesis}"</p>
          <ul className="space-y-2">
            {(debate.bull.points || []).map((p: T.DebatePoint, i: number) => (
              <li key={i} className="text-xs text-stone-300 flex gap-2 items-start">
                <span className="mt-1.5 w-1 h-1 rounded-full bg-green-500 shrink-0"></span>
                <span>{p.argument}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Bear Agent Card */}
        <div className={`bg-red-950/20 border rounded-lg p-4 relative overflow-hidden transition-all ${
          debate.winner === 'Bear' ? 'border-red-500/60 shadow-[0_0_15px_rgba(239,68,68,0.1)]' : 'border-red-900/40'
        }`}>
          <div className="absolute top-0 right-0 p-2 opacity-10">
            <TrendingDown className="w-24 h-24 text-red-500" />
          </div>
          <div className="flex justify-between items-start mb-3 border-b border-red-900/30 pb-2">
            <h4 className="text-red-400 font-bold flex items-center gap-2">
              <Bot className="w-4 h-4" /> Bear Agent
            </h4>
            {debate.winner === 'Bear' && (
              <span className="text-[10px] bg-red-500 text-white px-1.5 py-0.5 rounded font-bold uppercase">Winner</span>
            )}
          </div>
          <p className="text-sm font-semibold text-red-100 mb-3 italic leading-relaxed">"{debate.bear.thesis}"</p>
          <ul className="space-y-2">
            {(debate.bear.points || []).map((p: T.DebatePoint, i: number) => (
              <li key={i} className="text-xs text-stone-300 flex gap-2 items-start">
                <span className="mt-1.5 w-1 h-1 rounded-full bg-red-500 shrink-0"></span>
                <span>{p.argument}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="bg-surface-overlay/50 p-3 rounded text-xs text-stone-400 border-l-2 border-accent italic">
        <span className="font-bold text-stone-300 not-italic">Moderator Conclusion:</span> {debate.conclusion}
      </div>
    </div>
  );
});
DebateSection.displayName = 'DebateSection';

export default DebateSection;
