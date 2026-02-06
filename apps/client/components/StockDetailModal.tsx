import React, { useState, useRef, useEffect } from 'react';
import type * as T from '../src/types/schema';
import { logger } from '../utils/logger';
import StockChart from './StockChart';
import { TradingViewChart } from './TradingViewChart';
import { ChartToolbar } from './ChartToolbar';
import { AnalysisTypewriter } from './TypewriterText';
import {
  AlertBanner,
  KeyMetricsBar,
  ConfidenceDisplay,
  AnalysisLevelBadge,
  DiagnosticsPanel,
  HistoricalCasesCount,
  MarketHints,
} from './AgenticUI';
import { AnalysisComparison } from './AnalysisComparison';
import DebateSection from './DebateSection';
import RiskGauge from './RiskGauge';
import ChatPanel from './ChatPanel';
import { useChartIndicators } from '../hooks';
import { X, MessageSquare, FileText, Volume2, Pause, Play, Square, Copy, Check, BrainCircuit, ShieldAlert, CheckCircle2, Search, Swords, UserCog, CandlestickChart, LineChart } from 'lucide-react';

interface StockDetailModalProps {
  stock: T.AssetPrice;
  priceData?: T.StockPrice;
  analysis?: T.AgentAnalysisResponse;
  onClose: () => void;
  /** 是否启用打字机效果（新分析时为 true） */
  enableTypewriter?: boolean;
}

const WorkflowStep: React.FC<{ icon: React.ReactNode; label: string; active?: boolean; completed?: boolean }> = ({ icon, label, active, completed }) => (
  <div className={`flex flex-col items-center gap-2 relative z-10 ${active ? 'opacity-100 scale-110' : 'opacity-60'} transition-all`}>
    <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 ${
      completed ? 'bg-accent border-accent text-white' :
      active ? 'bg-accent/10 border-accent text-accent animate-pulse' :
      'bg-surface-overlay border-border-strong text-stone-500'
    }`}>
      {completed ? <CheckCircle2 className="w-4 h-4" /> : icon}
    </div>
    <span className={`text-[10px] font-bold uppercase tracking-wider ${active || completed ? 'text-amber-200' : 'text-stone-600'}`}>
      {label}
    </span>
  </div>
);

const StockDetailModal: React.FC<StockDetailModalProps> = ({ stock, priceData, analysis, onClose, enableTypewriter = false }) => {
  const isUp = priceData && priceData.change >= 0;
  const chartColor = isUp ? '#10B981' : '#EF4444';
  const [activeTab, setActiveTab] = useState<'report' | 'chat'>('report');

  // 打字机效果状态 - 只在组件首次接收到 analysis 时启用一次
  const [typewriterEnabled, setTypewriterEnabled] = useState(enableTypewriter);
  const analysisRef = useRef<string | null>(null);

  // 当 analysis 变化时，决定是否启用打字机
  useEffect(() => {
    if (analysis?.full_report.reasoning && analysis.full_report.reasoning !== analysisRef.current) {
      // 新的分析结果到来
      if (enableTypewriter) {
        setTypewriterEnabled(true);
      }
      analysisRef.current = analysis.full_report.reasoning;
    }
  }, [analysis?.full_report.reasoning, enableTypewriter]);

  // 打字机完成回调
  const handleTypewriterComplete = () => {
    // 打字完成后禁用，避免重新打字
    setTypewriterEnabled(false);
  };

  // Audio State - 增强版
  const [audioState, setAudioState] = useState<'idle' | 'playing' | 'paused'>('idle');
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const [isCopied, setIsCopied] = useState(false);

  // 图表类型切换状态
  const [chartType, setChartType] = useState<'area' | 'candlestick'>('candlestick');

  // 图表指标状态（时间周期、技术指标、成交量、全屏、K 线数据）
  const {
    period,
    indicators: chartIndicators,
    showVolume,
    isFullscreen: isChartFullscreen,
    setPeriod,
    setIndicators: setChartIndicators,
    toggleVolume,
    toggleFullscreen: toggleChartFullscreen,
    klineData,
    isLoading: isChartLoading,
  } = useChartIndicators({ symbol: stock.symbol });

  // ESC 键退出全屏
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isChartFullscreen) {
        toggleChartFullscreen();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isChartFullscreen, toggleChartFullscreen]);

  // 清理 TTS
  useEffect(() => {
    return () => {
      window.speechSynthesis.cancel();
    };
  }, []);

  // 增强的 TTS 控制
  const handlePlayAudio = () => {
    if (!analysis) return;

    // 如果是暂停状态，恢复播放
    if (audioState === 'paused') {
      window.speechSynthesis.resume();
      setAudioState('playing');
      return;
    }

    // 如果正在播放，暂停
    if (audioState === 'playing') {
      window.speechSynthesis.pause();
      setAudioState('paused');
      return;
    }

    // 新建播放
    try {
      const textToSpeak = analysis.anchor_script || analysis.full_report.reasoning;
      const utterance = new SpeechSynthesisUtterance(textToSpeak);
      utterance.lang = 'zh-CN';
      utterance.rate = 1.1;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;

      utterance.onend = () => setAudioState('idle');
      utterance.onerror = () => setAudioState('idle');

      utteranceRef.current = utterance;
      window.speechSynthesis.speak(utterance);
      setAudioState('playing');
    } catch (e) {
      logger.error("Audio failed", e);
      setAudioState('idle');
    }
  };

  const handleStopAudio = () => {
    window.speechSynthesis.cancel();
    setAudioState('idle');
  };

  const handleCopyReport = () => {
    if (!analysis) return;
    const { full_report } = analysis;
    const text = `Stock: ${stock.symbol}
Signal: ${analysis.signal}
Setup: Entry ${full_report.trade_setup?.entry_zone || 'N/A'} -> TP ${full_report.trade_setup?.target_price || 'N/A'}

Reasoning:
${full_report.reasoning}`;
    navigator.clipboard.writeText(text);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  // Helper to calculate position for price bar

  return (
    <div 
      onClick={handleBackdropClick}
      className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200"
    >
      <div className="bg-surface-raised border border-border w-full max-w-6xl h-[95vh] rounded-xl flex flex-col shadow-2xl overflow-hidden relative animate-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="shrink-0 p-6 border-b border-border bg-surface/50 flex justify-between items-start">
           <div className="flex items-center gap-4">
              <div>
                <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                  {stock.symbol}
                  <span className="text-sm font-normal text-stone-400 bg-surface-overlay px-2 py-1 rounded-md">
                    {priceData?.market || 'N/A'}
                  </span>
                  {/* Analysis Level Badge */}
                  {analysis?.ui_hints?.analysis_level && (
                    <AnalysisLevelBadge level={analysis.ui_hints.analysis_level as 'L1' | 'L2'} />
                  )}
                </h2>
                <p className="text-stone-400">{stock.name}</p>
              </div>
              
              {priceData && (
                <div className="hidden sm:block pl-6 border-l border-border ml-2">
                   <div className="text-2xl font-mono font-bold text-white">{priceData.price.toFixed(2)}</div>
                   <div className={`text-sm font-bold ${isUp ? 'text-green-400' : 'text-red-400'}`}>
                      {priceData.change > 0 ? '+' : ''}{priceData.change.toFixed(2)} ({priceData.change_percent.toFixed(2)}%)
                   </div>
                </div>
              )}
           </div>

           <div className="flex items-center gap-4">
             {/* Tab Switcher */}
             <div className="bg-surface-overlay p-1 rounded-lg flex gap-1">
                <button 
                  onClick={() => setActiveTab('report')}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium flex items-center gap-2 transition-all ${activeTab === 'report' ? 'bg-surface-muted text-white shadow' : 'text-stone-400 hover:text-stone-200'}`}
                >
                  <FileText className="w-4 h-4" /> Report
                </button>
                <button 
                  onClick={() => setActiveTab('chat')}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium flex items-center gap-2 transition-all ${activeTab === 'chat' ? 'bg-accent text-white shadow' : 'text-stone-400 hover:text-stone-200'}`}
                >
                  <MessageSquare className="w-4 h-4" /> Ask Agent
                </button>
             </div>
             
             <button 
                onClick={onClose}
                className="text-stone-400 hover:text-stone-50 bg-surface-overlay hover:bg-surface-muted p-2 rounded-full transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
           </div>
        </div>

        {/* Agent Workflow Visualization */}
        {analysis && (
            <div className="bg-surface/80 border-b border-border py-3 px-6">
                <div className="flex justify-between items-center max-w-3xl mx-auto relative">
                    {/* Connecting Line */}
                    <div className="absolute top-4 left-0 right-0 h-0.5 bg-surface-overlay -z-0"></div>

                    <WorkflowStep icon={<Search className="w-4 h-4" />} label="Analyst Team" completed />
                    <WorkflowStep icon={<Swords className="w-4 h-4" />} label="Bull/Bear Debate" completed />
                    <WorkflowStep icon={<ShieldAlert className="w-4 h-4" />} label="Risk Check" completed />
                    <WorkflowStep icon={<UserCog className="w-4 h-4" />} label="Fund Manager" completed active />
                </div>
            </div>
        )}

        {/* Agentic UI Alerts & Key Metrics */}
        {analysis?.ui_hints && (
          <div className="px-6 py-3 space-y-3 border-b border-border/50 bg-surface-raised/30">
            {/* Alert Banner */}
            <AlertBanner hints={analysis.ui_hints} />

            {/* Key Metrics & Market Hints Row */}
            <div className="flex flex-wrap items-center justify-between gap-4">
              <KeyMetricsBar metrics={analysis.ui_hints.key_metrics || []} />
              <div className="flex items-center gap-3">
                <MarketHints hints={analysis.ui_hints.market_specific_hints || []} />
                <HistoricalCasesCount count={analysis.ui_hints.historical_cases_count ?? undefined} />
              </div>
            </div>
          </div>
        )}

        {/* Content Area */}
        <div className="flex-1 overflow-hidden flex flex-col md:flex-row">
          
          {/* Main Content */}
          <div className="flex-1 overflow-y-auto p-6 scroll-smooth relative custom-scrollbar">
            
            {activeTab === 'report' ? (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* --- LEFT COLUMN: Chart & Deep Dive --- */}
                <div className="lg:col-span-2 space-y-6">
                    {/* 图表区域 - 支持全屏 */}
                    <div className={`bg-surface rounded-lg border border-border overflow-hidden ${
                      isChartFullscreen ? 'fixed inset-0 z-[60] rounded-none' : ''
                    }`}>
                      {/* 图表类型切换栏 */}
                      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-border bg-surface-raised/50">
                        <div className="flex bg-surface-overlay rounded-md p-0.5">
                          <button
                            onClick={() => setChartType('candlestick')}
                            className={`flex items-center gap-1 px-2 py-1 text-xs rounded transition-all ${
                              chartType === 'candlestick'
                                ? 'bg-surface-muted text-white'
                                : 'text-stone-400 hover:text-stone-200'
                            }`}
                            title="K 线图"
                          >
                            <CandlestickChart className="w-3 h-3" />
                          </button>
                          <button
                            onClick={() => setChartType('area')}
                            className={`flex items-center gap-1 px-2 py-1 text-xs rounded transition-all ${
                              chartType === 'area'
                                ? 'bg-surface-muted text-white'
                                : 'text-stone-400 hover:text-stone-200'
                            }`}
                            title="面积图"
                          >
                            <LineChart className="w-3 h-3" />
                          </button>
                        </div>
                        <div className="w-px h-4 bg-surface-muted" />
                        <span className="text-xs text-stone-500">{stock.symbol} · {priceData?.market || 'N/A'}</span>
                        {isChartFullscreen && (
                          <button
                            onClick={toggleChartFullscreen}
                            className="ml-auto px-2 py-1 text-xs text-stone-400 hover:text-stone-50 bg-surface-overlay hover:bg-surface-muted rounded transition-colors"
                          >
                            ✕ 退出全屏
                          </button>
                        )}
                      </div>

                      {/* 专业工具栏（仅 K 线模式） */}
                      {chartType === 'candlestick' && (
                        <ChartToolbar
                          activePeriod={period}
                          onPeriodChange={setPeriod}
                          activeIndicators={chartIndicators}
                          onIndicatorsChange={setChartIndicators}
                          showVolume={showVolume}
                          onVolumeToggle={toggleVolume}
                          isFullscreen={isChartFullscreen}
                          onFullscreenToggle={toggleChartFullscreen}
                        />
                      )}

                      {/* 图表内容 */}
                      <div
                        className={isChartFullscreen ? 'flex-1 p-2' : 'h-64 p-2'}
                        style={isChartFullscreen ? { height: 'calc(100vh - 90px)' } : undefined}
                      >
                        {priceData || klineData.length > 0 ? (
                          chartType === 'candlestick' ? (
                            <TradingViewChart
                              data={klineData.length > 0 ? klineData : undefined}
                              simpleData={undefined}
                              symbol={stock.symbol}
                              height={isChartFullscreen ? window.innerHeight - 100 : 240}
                              showVolume={showVolume}
                              indicators={chartIndicators}
                              isUp={isUp}
                              crosshair
                              grid
                              timeScale
                            />
                          ) : (
                            <StockChart
                              data={[]}
                              color={chartColor}
                              height={isChartFullscreen ? window.innerHeight - 100 : 240}
                            />
                          )
                        ) : isChartLoading ? (
                          <div className="h-full flex items-center justify-center text-stone-600">
                            <div className="flex flex-col items-center gap-2">
                              <div className="w-6 h-6 border-2 border-border-strong border-t-accent rounded-full animate-spin" />
                              <span className="text-sm">加载图表数据...</span>
                            </div>
                          </div>
                        ) : (
                          <div className="h-full flex items-center justify-center text-stone-600">
                            <div className="flex flex-col items-center gap-2">
                              <div className="w-6 h-6 border-2 border-border-strong border-t-accent rounded-full animate-spin" />
                              <span className="text-sm">Loading Chart...</span>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    {analysis && (
                      <div className="space-y-4">
                        <div className="flex justify-between items-center">
                          <h3 className="text-xl font-bold text-white flex items-center gap-2">
                            <BrainCircuit className="w-5 h-5 text-purple-400" /> Fund Manager's Synthesis
                          </h3>
                          <div className="flex gap-2">
                             {/* TTS 播放/暂停按钮 */}
                             <button
                                onClick={handlePlayAudio}
                                className={`flex items-center gap-2 px-3 py-1.5 text-white text-xs font-bold rounded-md transition-all ${
                                  audioState === 'playing' ? 'bg-amber-600 hover:bg-amber-500' :
                                  audioState === 'paused' ? 'bg-green-600 hover:bg-green-500' :
                                  'bg-indigo-600 hover:bg-indigo-500'
                                }`}
                             >
                               {audioState === 'playing' ? (
                                 <><Pause className="w-3 h-3" /> Pause</>
                               ) : audioState === 'paused' ? (
                                 <><Play className="w-3 h-3" /> Resume</>
                               ) : (
                                 <><Volume2 className="w-3 h-3" /> Briefing</>
                               )}
                             </button>
                             {/* TTS 停止按钮 */}
                             {audioState !== 'idle' && (
                               <button
                                  onClick={handleStopAudio}
                                  className="flex items-center gap-2 px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white text-xs font-bold rounded-md transition-all"
                               >
                                 <Square className="w-3 h-3" /> Stop
                               </button>
                             )}
                             <button 
                                onClick={handleCopyReport}
                                className="flex items-center gap-2 px-3 py-1.5 bg-surface-overlay hover:bg-surface-muted text-stone-300 text-xs font-bold rounded-md transition-all"
                             >
                               {isCopied ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
                               {isCopied ? 'Copied' : 'Copy'}
                             </button>
                          </div>
                        </div>

                        {/* Executive Summary - 使用打字机效果 */}
                        <AnalysisTypewriter
                          reasoning={analysis.full_report.reasoning}
                          enabled={typewriterEnabled}
                          speed={15}
                          onComplete={handleTypewriterComplete}
                        />

                        {/* Researcher Team Debate Section */}
                        <DebateSection debate={analysis.full_report.debate} />

                      </div>
                    )}
                </div>

                {/* --- RIGHT COLUMN: Trade Setup & Stats --- */}
                <div className="space-y-6">
                    {analysis ? (
                      <div className="space-y-6">
                        {/* Signal & Trade Setup Card */}
                        <div className="bg-surface-overlay/40 rounded-xl p-5 border border-border-strong">
                          <div
                            className={`text-center py-4 rounded-lg border-2 mb-4 ${
                              analysis.signal.includes('Buy')
                                ? 'border-green-500 bg-green-500/10 text-green-400'
                                : analysis.signal.includes('Sell')
                                ? 'border-red-500 bg-red-500/10 text-red-400'
                                : 'border-yellow-500 bg-yellow-500/10 text-yellow-400'
                            }`}
                          >
                            <div className="text-2xl font-black uppercase tracking-wider">{analysis.signal}</div>
                          </div>

                          {/* Confidence Display */}
                          <div className="flex justify-center mb-6">
                            <ConfidenceDisplay value={analysis.confidence} mode={(analysis.ui_hints?.confidence_display as any) || "number"} />
                          </div>
                        </div>

                        {/* --- RISK MANAGEMENT TEAM (ENHANCED UI) --- */}
                        {analysis.full_report.risk_assessment && (
                          <div className="bg-surface-overlay/40 rounded-xl p-4 border border-border-strong">
                            <h4 className="text-xs font-bold text-stone-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                              <ShieldAlert className="w-4 h-4" /> Risk Assessment
                            </h4>

                            <div className="flex items-center justify-between mb-4">
                              {/* 使用增强的半圆仪表盘组件 */}
                              <RiskGauge
                                score={analysis.full_report.risk_assessment.score}
                                verdict={analysis.full_report.risk_assessment.verdict}
                              />

                              <div className="text-right">
                                <div
                                  className={`inline-block px-3 py-1 rounded-full text-xs font-bold border mb-1 ${
                                    analysis.full_report.risk_assessment.verdict === 'Approved'
                                      ? 'bg-green-500/20 border-green-500 text-green-400'
                                      : analysis.full_report.risk_assessment.verdict === 'Rejected'
                                      ? 'bg-red-500/20 border-red-500 text-red-400'
                                      : 'bg-yellow-500/20 border-yellow-500 text-yellow-400'
                                  }`}
                                >
                                  {analysis.full_report.risk_assessment.verdict.toUpperCase()}
                                </div>
                                <p className="text-[10px] text-stone-500">Risk Score (0-10)</p>
                              </div>
                            </div>

                            <div className="space-y-2 text-xs">
                              <div className="flex justify-between border-b border-border-strong/50 pb-1">
                                <span className="text-stone-400">Volatility</span>
                                <span className="text-stone-200">
                                  {analysis.full_report.risk_assessment.volatility_status}
                                </span>
                              </div>
                              <div className="flex justify-between border-b border-border-strong/50 pb-1">
                                <span className="text-stone-400">Max Drawdown Risk</span>
                                <span className="text-stone-200">
                                  {analysis.full_report.risk_assessment.max_drawdown_risk}
                                </span>
                              </div>
                              <div className="flex justify-between pt-1">
                                <span className="text-stone-400">Liquidity</span>
                                <span
                                  className={
                                    analysis.full_report.risk_assessment.liquidity_concerns
                                      ? 'text-red-400 font-bold'
                                      : 'text-green-400'
                                  }
                                >
                                  {analysis.full_report.risk_assessment.liquidity_concerns
                                    ? 'Concerns Detected'
                                    : 'Good'}
                                </span>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Diagnostics Panel */}
                        <DiagnosticsPanel diagnostics={analysis.diagnostics} />

                        {/* Historical Analysis Comparison */}
                        <AnalysisComparison symbol={stock.symbol} />

                      </div>
                    ) : (
                      <div className="bg-surface-overlay/40 rounded-xl p-8 border border-border-strong text-center text-stone-500">
                        Run analysis to see data.
                      </div>
                    )}
                </div>
              </div>
            ) : (
              // Chat Interface
              <ChatPanel stock={stock} analysis={analysis} />
            )}

          </div>
        </div>
      </div>
    </div>
  );
};

export default StockDetailModal;
