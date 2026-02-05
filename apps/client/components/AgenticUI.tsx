import React, { useState } from 'react';
import type * as T from '../src/types/schema';
import {
  AlertTriangle,
  AlertCircle,
  Info,
  ChevronDown,
  ChevronUp,
  Activity,
  Zap,
  Clock,
  BrainCircuit,
  Shield,
  Database,
  Lightbulb,
  Users,
  Layers,
  History,
} from 'lucide-react';

// ============ Alert Banner ============

const alertConfig: Record<T.AlertLevel, { bg: string; border: string; text: string; icon: React.ReactNode }> = {
  critical: {
    bg: 'bg-red-950/60',
    border: 'border-red-500/60',
    text: 'text-red-300',
    icon: <AlertTriangle className="w-4 h-4 text-red-400" />,
  },
  warning: {
    bg: 'bg-yellow-950/40',
    border: 'border-yellow-500/40',
    text: 'text-yellow-300',
    icon: <AlertCircle className="w-4 h-4 text-yellow-400" />,
  },
  info: {
    bg: 'bg-blue-950/30',
    border: 'border-blue-500/30',
    text: 'text-blue-300',
    icon: <Info className="w-4 h-4 text-blue-400" />,
  },
  none: {
    bg: '',
    border: '',
    text: '',
    icon: null,
  },
};

export const AlertBanner: React.FC<{ hints: T.UIHints }> = ({ hints }) => {
  if (hints.alert_level === 'none' || !hints.alert_message) return null;

  const config = alertConfig[hints.alert_level as T.AlertLevel];

  return (
    <div className={`${config.bg} border ${config.border} rounded-lg px-4 py-2.5 flex items-center gap-3 animate-in fade-in slide-in-from-top-2 duration-300`}>
      {config.icon}
      <span className={`text-sm font-medium ${config.text}`}>{hints.alert_message}</span>
    </div>
  );
};

// ============ Key Metrics Bar ============

export const KeyMetricsBar: React.FC<{ metrics: string[] }> = ({ metrics }) => {
  if (!metrics || metrics.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {metrics.map((metric, i) => (
        <span
          key={i}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-gray-800/80 border border-gray-700 rounded-full text-xs font-mono text-gray-300"
        >
          <Activity className="w-3 h-3 text-blue-400" />
          {metric}
        </span>
      ))}
    </div>
  );
};

// ============ Confidence Display ============

const ConfidenceGauge: React.FC<{ value: number }> = ({ value }) => {
  const angle = (value / 100) * 180;
  const radians = ((180 - angle) * Math.PI) / 180;
  const needleX = 50 + 35 * Math.cos(radians);
  const needleY = 50 - 35 * Math.sin(radians);

  const getColor = (v: number) => {
    if (v >= 70) return '#10B981';
    if (v >= 50) return '#F59E0B';
    return '#EF4444';
  };

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-20 h-12">
        <svg viewBox="0 0 100 55" className="w-full h-full">
          <defs>
            <linearGradient id="confGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#EF4444" />
              <stop offset="50%" stopColor="#F59E0B" />
              <stop offset="100%" stopColor="#10B981" />
            </linearGradient>
          </defs>
          <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#374151" strokeWidth="8" strokeLinecap="round" />
          <path
            d="M 10 50 A 40 40 0 0 1 90 50"
            fill="none"
            stroke="url(#confGradient)"
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={`${(angle / 180) * 125.6} 125.6`}
            className="transition-all duration-1000"
          />
          <line x1="50" y1="50" x2={needleX} y2={needleY} stroke="white" strokeWidth="2" strokeLinecap="round" className="transition-all duration-1000" />
          <circle cx="50" cy="50" r="3" fill="white" />
        </svg>
      </div>
      <span className="text-lg font-bold" style={{ color: getColor(value) }}>{value}%</span>
    </div>
  );
};

const ConfidenceProgress: React.FC<{ value: number }> = ({ value }) => {
  const getColor = (v: number) => {
    if (v >= 70) return 'bg-green-500';
    if (v >= 50) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="w-full space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-gray-400">Confidence</span>
        <span className="font-mono font-bold text-white">{value}%</span>
      </div>
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full ${getColor(value)} rounded-full transition-all duration-1000 ease-out`}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
};

const ConfidenceBadge: React.FC<{ value: number }> = ({ value }) => {
  const config = value >= 70
    ? { bg: 'bg-green-500/20', border: 'border-green-500/40', text: 'text-green-400', label: 'High' }
    : value >= 50
    ? { bg: 'bg-yellow-500/20', border: 'border-yellow-500/40', text: 'text-yellow-400', label: 'Medium' }
    : { bg: 'bg-red-500/20', border: 'border-red-500/40', text: 'text-red-400', label: 'Low' };

  return (
    <div className={`inline-flex items-center gap-2 ${config.bg} border ${config.border} rounded-lg px-3 py-1.5`}>
      <span className={`text-xs font-bold uppercase ${config.text}`}>{config.label}</span>
      <span className="font-mono font-bold text-white text-sm">{value}%</span>
    </div>
  );
};

export const ConfidenceDisplay: React.FC<{ value: number; mode: T.UIHints['confidence_display'] }> = ({ value, mode }) => {
  switch (mode) {
    case 'gauge':
      return <ConfidenceGauge value={value} />;
    case 'progress':
      return <ConfidenceProgress value={value} />;
    case 'badge':
      return <ConfidenceBadge value={value} />;
    default:
      return (
        <div className="text-center">
          <span className="text-2xl font-bold text-white">{value}</span>
          <span className="text-xs text-gray-500">%</span>
        </div>
      );
  }
};

// ============ Planner Insight ============

export const PlannerInsight: React.FC<{ hints: T.UIHints }> = ({ hints }) => {
  const [expanded, setExpanded] = useState(false);

  if (!hints.show_planner_reasoning || !hints.planner_insight) return null;

  return (
    <div className="bg-purple-950/20 border border-purple-800/30 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-purple-950/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <BrainCircuit className="w-4 h-4 text-purple-400" />
          <span className="text-xs font-bold text-purple-300 uppercase tracking-wider">Planner Decision</span>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-purple-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-purple-400" />
        )}
      </button>
      {expanded && (
        <div className="px-4 pb-3 text-sm text-gray-300 border-t border-purple-800/20 pt-2 animate-in fade-in slide-in-from-top-1 duration-200">
          {hints.planner_insight}
        </div>
      )}
    </div>
  );
};

// ============ Data Quality Warning ============

export const DataQualityWarning: React.FC<{ issues?: string[] }> = ({ issues }) => {
  if (!issues || issues.length === 0) return null;

  return (
    <div className="bg-amber-950/20 border border-amber-700/30 rounded-lg px-4 py-2.5">
      <div className="flex items-center gap-2 mb-2">
        <Database className="w-4 h-4 text-amber-400" />
        <span className="text-xs font-bold text-amber-300 uppercase tracking-wider">Data Quality Notes</span>
      </div>
      <ul className="space-y-1">
        {issues.map((issue, i) => (
          <li key={i} className="text-xs text-amber-200/80 flex items-start gap-2">
            <span className="mt-1.5 w-1 h-1 rounded-full bg-amber-400 shrink-0" />
            {issue}
          </li>
        ))}
      </ul>
    </div>
  );
};

// ============ Action Suggestions ============

export const ActionSuggestions: React.FC<{ suggestions: string[] }> = ({ suggestions }) => {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div className="bg-indigo-950/20 border border-indigo-700/30 rounded-lg px-4 py-3">
      <div className="flex items-center gap-2 mb-2.5">
        <Lightbulb className="w-4 h-4 text-indigo-400" />
        <span className="text-xs font-bold text-indigo-300 uppercase tracking-wider">AI Suggestions</span>
      </div>
      <ul className="space-y-2">
        {suggestions.map((suggestion, i) => (
          <li key={i} className="text-sm text-gray-300 flex items-start gap-2">
            <Zap className="w-3.5 h-3.5 text-indigo-400 mt-0.5 shrink-0" />
            {suggestion}
          </li>
        ))}
      </ul>
    </div>
  );
};

// ============ Analysis Level Badge ============

export const AnalysisLevelBadge: React.FC<{ level: 'L1' | 'L2' }> = ({ level }) => {
  const isL2 = level === 'L2';

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
        isL2
          ? 'bg-blue-500/10 border-blue-500/30 text-blue-400'
          : 'bg-gray-500/10 border-gray-500/30 text-gray-400'
      }`}
    >
      <Layers className="w-3 h-3" />
      {isL2 ? 'Full Analysis' : 'Quick Scan'}
    </div>
  );
};

// ============ Diagnostics Panel ============

export const DiagnosticsPanel: React.FC<{ diagnostics?: T.AgentAnalysisResponse['diagnostics'] }> = ({ diagnostics }) => {
  const [expanded, setExpanded] = useState(false);

  if (!diagnostics) return null;

  return (
    <div className="bg-gray-800/30 border border-gray-700/50 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-gray-800/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Shield className="w-3.5 h-3.5 text-gray-500" />
          <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Diagnostics</span>
        </div>
        {diagnostics.elapsed_seconds != null && (
          <div className="flex items-center gap-1 text-[10px] text-gray-500">
            <Clock className="w-3 h-3" />
            {diagnostics.elapsed_seconds}s
          </div>
        )}
      </button>
      {expanded && (
        <div className="px-3 pb-2 border-t border-gray-700/30 pt-2 space-y-1.5 text-[11px] text-gray-500 animate-in fade-in duration-200">
          {diagnostics.task_id && (
            <div className="flex justify-between">
              <span>Task ID</span>
              <span className="font-mono text-gray-400">{diagnostics.task_id.slice(0, 12)}...</span>
            </div>
          )}
          {diagnostics.analysts_used && diagnostics.analysts_used.length > 0 && (
            <div className="flex justify-between items-start">
              <span className="flex items-center gap-1"><Users className="w-3 h-3" /> Analysts</span>
              <span className="text-gray-400">{diagnostics.analysts_used.join(', ')}</span>
            </div>
          )}
          {diagnostics.planner_decision && (
            <div className="flex justify-between items-start">
              <span className="flex items-center gap-1"><BrainCircuit className="w-3 h-3" /> Planner</span>
              <span className="text-gray-400 text-right max-w-[200px]">{diagnostics.planner_decision}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ============ Historical Cases Count ============

export const HistoricalCasesCount: React.FC<{ count?: number }> = ({ count }) => {
  if (count == null || count === 0) return null;

  return (
    <div className="inline-flex items-center gap-1.5 text-[11px] text-gray-500">
      <History className="w-3 h-3" />
      <span>{count} historical case{count > 1 ? 's' : ''} referenced</span>
    </div>
  );
};

// ============ Market Specific Hints ============

export const MarketHints: React.FC<{ hints?: string[] }> = ({ hints }) => {
  if (!hints || hints.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {hints.map((hint, i) => (
        <span
          key={i}
          className="inline-flex items-center gap-1 px-2 py-0.5 bg-orange-950/20 border border-orange-800/30 rounded text-[10px] text-orange-300"
        >
          <AlertCircle className="w-3 h-3" />
          {hint}
        </span>
      ))}
    </div>
  );
};
