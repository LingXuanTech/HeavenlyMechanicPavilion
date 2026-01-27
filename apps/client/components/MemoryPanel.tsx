/**
 * 记忆面板
 *
 * 显示股票的历史分析记忆和反思报告
 */
import React from 'react';
import {
  Brain,
  History,
  Lightbulb,
  TrendingUp,
  TrendingDown,
  Calendar,
  BarChart3,
  AlertCircle,
  ChevronRight,
  RefreshCw
} from 'lucide-react';
import { useMemoryRetrieve, useReflection } from '../hooks';
import type { MemoryRetrievalResult, ReflectionReport } from '../types';

interface MemoryPanelProps {
  symbol: string;
  onSelectMemory?: (memory: MemoryRetrievalResult) => void;
}

const getSignalColor = (signal: string): string => {
  const s = signal.toLowerCase();
  if (s.includes('strong buy')) return 'text-green-400 bg-green-900/20';
  if (s.includes('buy')) return 'text-green-300 bg-green-900/10';
  if (s.includes('strong sell')) return 'text-red-400 bg-red-900/20';
  if (s.includes('sell')) return 'text-red-300 bg-red-900/10';
  return 'text-yellow-400 bg-yellow-900/10';
};

const MemoryPanel: React.FC<MemoryPanelProps> = ({ symbol, onSelectMemory }) => {
  const { data: memories, isLoading: memoriesLoading, refetch: refetchMemories } = useMemoryRetrieve(symbol, 5, 365);
  const { data: reflection, isLoading: reflectionLoading } = useReflection(symbol);

  const hasMemories = memories && memories.length > 0;
  const hasReflection = reflection && reflection.patterns && reflection.patterns.length > 0;

  return (
    <div className="space-y-4">
      {/* Historical Memories */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 bg-gray-950/50 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-purple-400" />
            <span className="text-sm font-semibold text-white">Historical Analysis</span>
            {hasMemories && (
              <span className="text-xs text-gray-500">({memories.length} records)</span>
            )}
          </div>
          <button
            onClick={() => refetchMemories()}
            className="p-1 hover:bg-gray-800 rounded transition-colors"
            title="刷新记忆"
          >
            <RefreshCw className={`w-3 h-3 text-gray-400 ${memoriesLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        <div className="p-4">
          {memoriesLoading ? (
            <div className="flex items-center justify-center py-6">
              <RefreshCw className="w-5 h-5 text-gray-500 animate-spin" />
            </div>
          ) : hasMemories ? (
            <div className="space-y-2">
              {memories.map((item, index) => (
                <div
                  key={index}
                  onClick={() => onSelectMemory?.(item)}
                  className="flex items-center justify-between p-3 bg-gray-950/50 rounded border border-gray-800 hover:border-purple-500/30 cursor-pointer transition-colors group"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs px-2 py-0.5 rounded ${getSignalColor(item.memory.signal)}`}>
                        {item.memory.signal}
                      </span>
                      <span className="text-xs text-gray-500">
                        {item.memory.confidence}% confidence
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-[10px] text-gray-400">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {item.memory.date}
                      </span>
                      <span>{item.days_ago} days ago</span>
                      <span className="text-purple-400">
                        {(item.similarity * 100).toFixed(0)}% similar
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 mt-1 truncate">
                      {item.memory.reasoning_summary}
                    </p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-600 group-hover:text-purple-400 transition-colors" />
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-6 text-gray-500">
              <Brain className="w-8 h-8 mb-2 opacity-50" />
              <p className="text-sm">No historical analysis found</p>
              <p className="text-xs mt-1">Run analysis to build memory</p>
            </div>
          )}
        </div>
      </div>

      {/* Reflection Report */}
      {(reflectionLoading || hasReflection) && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-3 bg-gray-950/50 border-b border-gray-800">
            <Lightbulb className="w-4 h-4 text-yellow-400" />
            <span className="text-sm font-semibold text-white">AI Reflection</span>
          </div>

          <div className="p-4">
            {reflectionLoading ? (
              <div className="flex items-center justify-center py-4">
                <RefreshCw className="w-5 h-5 text-gray-500 animate-spin" />
              </div>
            ) : reflection ? (
              <div className="space-y-4">
                {/* Patterns */}
                {reflection.patterns.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs text-gray-400">
                      <BarChart3 className="w-3 h-3" />
                      <span>Identified Patterns</span>
                    </div>
                    <div className="space-y-1">
                      {reflection.patterns.map((pattern, i) => (
                        <div
                          key={i}
                          className="flex items-start gap-2 text-xs text-gray-300 bg-gray-950/50 p-2 rounded"
                        >
                          <TrendingUp className="w-3 h-3 text-blue-400 mt-0.5 shrink-0" />
                          <span>{pattern}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Lessons */}
                {reflection.lessons.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs text-gray-400">
                      <AlertCircle className="w-3 h-3" />
                      <span>Key Lessons</span>
                    </div>
                    <div className="space-y-1">
                      {reflection.lessons.map((lesson, i) => (
                        <div
                          key={i}
                          className="flex items-start gap-2 text-xs text-gray-300 bg-gray-950/50 p-2 rounded"
                        >
                          <Lightbulb className="w-3 h-3 text-yellow-400 mt-0.5 shrink-0" />
                          <span>{lesson}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Confidence Adjustment */}
                {reflection.confidence_adjustment !== 0 && (
                  <div className="flex items-center justify-between p-3 bg-gray-950/50 rounded border border-gray-800">
                    <span className="text-xs text-gray-400">Confidence Adjustment</span>
                    <span className={`text-sm font-bold ${
                      reflection.confidence_adjustment > 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {reflection.confidence_adjustment > 0 ? '+' : ''}
                      {reflection.confidence_adjustment}%
                    </span>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
};

export default MemoryPanel;
