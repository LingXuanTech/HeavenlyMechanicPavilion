import React, { useState, useRef, useEffect } from 'react';
import { Stock, StockPrice, AgentAnalysis, ChatMessage } from '../types';
import StockChart from './StockChart';
import * as api from '../services/api';
import { X, Send, MessageSquare, FileText, Bot, Volume2, VolumeX, Pause, Play, Square, Copy, Check, TrendingUp, TrendingDown, BrainCircuit, BarChart2, Target, ShieldAlert, Scale, Swords, CheckCircle2, Search, Gavel, UserCog } from 'lucide-react';

interface StockDetailModalProps {
  stock: Stock;
  priceData?: StockPrice;
  analysis?: AgentAnalysis;
  onClose: () => void;
}

const WorkflowStep: React.FC<{ icon: React.ReactNode; label: string; active?: boolean; completed?: boolean }> = ({ icon, label, active, completed }) => (
  <div className={`flex flex-col items-center gap-2 relative z-10 ${active ? 'opacity-100 scale-110' : 'opacity-60'} transition-all`}>
    <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 ${
      completed ? 'bg-blue-600 border-blue-500 text-white' :
      active ? 'bg-blue-900/50 border-blue-400 text-blue-300 animate-pulse' :
      'bg-gray-800 border-gray-700 text-gray-500'
    }`}>
      {completed ? <CheckCircle2 className="w-4 h-4" /> : icon}
    </div>
    <span className={`text-[10px] font-bold uppercase tracking-wider ${active || completed ? 'text-blue-200' : 'text-gray-600'}`}>
      {label}
    </span>
  </div>
);

// 辩论计组件 - 基于论点权重计算多空力量
const DebateMeter: React.FC<{ debate: AgentAnalysis['debate'] }> = ({ debate }) => {
  if (!debate) return null;

  // 基于论点权重计算真实的多空力量对比
  const weightMap: Record<string, number> = { High: 3, Medium: 2, Low: 1 };

  const bullScore = debate.bull.points.reduce(
    (sum, p) => sum + (weightMap[p.weight] || 1), 0
  );
  const bearScore = debate.bear.points.reduce(
    (sum, p) => sum + (weightMap[p.weight] || 1), 0
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
      <div className="relative h-3 bg-gray-800 rounded-full overflow-hidden">
        {/* 多方区域 */}
        <div
          className="absolute left-0 top-0 h-full bg-gradient-to-r from-green-600 to-green-400 transition-all duration-1000 ease-out"
          style={{ width: `${bullPercent}%` }}
        />
        {/* 空方区域 */}
        <div
          className="absolute right-0 top-0 h-full bg-gradient-to-l from-red-600 to-red-400"
          style={{ width: `${100 - bullPercent}%` }}
        />

        {/* 中心标记 */}
        <div className="absolute top-0 bottom-0 left-1/2 w-0.5 bg-white/30 -translate-x-1/2 z-10" />

        {/* 当前位置指示器 */}
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
          'bg-gray-500/20 text-gray-400'
        }`}>
          {debate.winner === 'Bull' ? '🐮 多方胜出' : debate.winner === 'Bear' ? '🐻 空方胜出' : '⚖️ 势均力敌'}
        </span>
      </div>
    </div>
  );
};

// 半圆风险仪表盘组件
const RiskGauge: React.FC<{ score: number; verdict: string }> = ({ score, verdict }) => {
  // 0-10 映射到 0-180 度
  const angle = (score / 10) * 180;
  const radians = ((180 - angle) * Math.PI) / 180;
  const needleX = 50 + 35 * Math.cos(radians);
  const needleY = 50 - 35 * Math.sin(radians);

  // 颜色映射
  const getColor = (s: number) => {
    if (s <= 3) return '#10B981'; // 绿色
    if (s <= 6) return '#F59E0B'; // 黄色
    return '#EF4444'; // 红色
  };

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-24 h-14">
        <svg viewBox="0 0 100 55" className="w-full h-full">
          {/* 渐变定义 */}
          <defs>
            <linearGradient id="riskGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#10B981" />
              <stop offset="50%" stopColor="#F59E0B" />
              <stop offset="100%" stopColor="#EF4444" />
            </linearGradient>
          </defs>

          {/* 背景弧 */}
          <path
            d="M 10 50 A 40 40 0 0 1 90 50"
            fill="none"
            stroke="#374151"
            strokeWidth="8"
            strokeLinecap="round"
          />

          {/* 彩色渐变弧 */}
          <path
            d="M 10 50 A 40 40 0 0 1 90 50"
            fill="none"
            stroke="url(#riskGradient)"
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={`${(angle / 180) * 125.6} 125.6`}
            className="transition-all duration-1000"
          />

          {/* 指针 */}
          <line
            x1="50" y1="50"
            x2={needleX} y2={needleY}
            stroke="white"
            strokeWidth="2"
            strokeLinecap="round"
            className="transition-all duration-1000"
          />

          {/* 中心点 */}
          <circle cx="50" cy="50" r="4" fill="white" />

          {/* 刻度标记 */}
          <text x="8" y="54" fill="#6B7280" fontSize="6">0</text>
          <text x="48" y="10" fill="#6B7280" fontSize="6">5</text>
          <text x="88" y="54" fill="#6B7280" fontSize="6">10</text>
        </svg>
      </div>

      {/* 分数显示 */}
      <div className="text-center -mt-1">
        <span className="text-2xl font-bold" style={{ color: getColor(score) }}>{score}</span>
        <span className="text-xs text-gray-500">/10</span>
      </div>
    </div>
  );
};

const StockDetailModal: React.FC<StockDetailModalProps> = ({ stock, priceData, analysis, onClose }) => {
  const isUp = priceData && priceData.change >= 0;
  const chartColor = isUp ? '#10B981' : '#EF4444';
  const [activeTab, setActiveTab] = useState<'report' | 'chat'>('report');

  // Audio State - 增强版
  const [audioState, setAudioState] = useState<'idle' | 'playing' | 'paused'>('idle');
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const [isCopied, setIsCopied] = useState(false);

  // Chat State
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize chat with greeting
  useEffect(() => {
    if (activeTab === 'chat' && messages.length === 0) {
      setMessages([{
        role: 'model',
        text: `Hello! I've analyzed ${stock.name}. I have insights from the Bull Researcher, Bear Researcher, and Risk Manager. What would you like to know?`
      }]);
    }
  }, [activeTab, stock.name, messages.length]);

  // Scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 清理 TTS
  useEffect(() => {
    return () => {
      window.speechSynthesis.cancel();
    };
  }, []);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !analysis) return;

    const userMsg: ChatMessage = { role: 'user', text: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    const response = await api.getChatResponse(stock.symbol, userMsg.text);

    setMessages(prev => [...prev, { role: 'model', text: response.content }]);
    setIsTyping(false);
  };

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
      const textToSpeak = analysis.anchor_script || analysis.reasoning;
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
      console.error("Audio failed", e);
      setAudioState('idle');
    }
  };

  const handleStopAudio = () => {
    window.speechSynthesis.cancel();
    setAudioState('idle');
  };

  const handleCopyReport = () => {
    if (!analysis) return;
    const text = `Stock: ${stock.symbol}\nSignal: ${analysis.signal}\nSetup: Entry ${analysis.tradeSetup?.entryZone || 'N/A'} -> TP ${analysis.tradeSetup?.targetPrice || 'N/A'}\n\nReasoning:\n${analysis.reasoning}`;
    navigator.clipboard.writeText(text);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  // Helper to calculate position for price bar
  const calculatePosition = (val: number, min: number, max: number) => {
    if (!val || !min || !max) return 50;
    const pos = ((val - min) / (max - min)) * 100;
    return Math.min(Math.max(pos, 0), 100);
  };

  return (
    <div 
      onClick={handleBackdropClick}
      className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200"
    >
      <div className="bg-gray-900 border border-gray-800 w-full max-w-6xl h-[95vh] rounded-xl flex flex-col shadow-2xl overflow-hidden relative animate-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="shrink-0 p-6 border-b border-gray-800 bg-gray-950/50 flex justify-between items-start">
           <div className="flex items-center gap-4">
              <div>
                <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                  {stock.symbol}
                  <span className="text-sm font-normal text-gray-400 bg-gray-800 px-2 py-1 rounded-md">{stock.market}</span>
                </h2>
                <p className="text-gray-400">{stock.name}</p>
              </div>
              
              {priceData && (
                <div className="hidden sm:block pl-6 border-l border-gray-800 ml-2">
                   <div className="text-2xl font-mono font-bold text-white">{priceData.price.toFixed(2)}</div>
                   <div className={`text-sm font-bold ${isUp ? 'text-green-400' : 'text-red-400'}`}>
                      {priceData.change > 0 ? '+' : ''}{priceData.change.toFixed(2)} ({priceData.changePercent.toFixed(2)}%)
                   </div>
                </div>
              )}
           </div>

           <div className="flex items-center gap-4">
             {/* Tab Switcher */}
             <div className="bg-gray-800 p-1 rounded-lg flex gap-1">
                <button 
                  onClick={() => setActiveTab('report')}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium flex items-center gap-2 transition-all ${activeTab === 'report' ? 'bg-gray-700 text-white shadow' : 'text-gray-400 hover:text-gray-200'}`}
                >
                  <FileText className="w-4 h-4" /> Report
                </button>
                <button 
                  onClick={() => setActiveTab('chat')}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium flex items-center gap-2 transition-all ${activeTab === 'chat' ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-gray-200'}`}
                >
                  <MessageSquare className="w-4 h-4" /> Ask Agent
                </button>
             </div>
             
             <button 
                onClick={onClose}
                className="text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 p-2 rounded-full transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
           </div>
        </div>

        {/* Agent Workflow Visualization */}
        {analysis && (
            <div className="bg-gray-950/80 border-b border-gray-800 py-3 px-6">
                <div className="flex justify-between items-center max-w-3xl mx-auto relative">
                    {/* Connecting Line */}
                    <div className="absolute top-4 left-0 right-0 h-0.5 bg-gray-800 -z-0"></div>
                    
                    <WorkflowStep icon={<Search className="w-4 h-4" />} label="Analyst Team" completed />
                    <WorkflowStep icon={<Swords className="w-4 h-4" />} label="Bull/Bear Debate" completed />
                    <WorkflowStep icon={<ShieldAlert className="w-4 h-4" />} label="Risk Check" completed />
                    <WorkflowStep icon={<UserCog className="w-4 h-4" />} label="Fund Manager" completed active />
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
                    <div className="bg-gray-950 rounded-lg p-4 border border-gray-800 h-64">
                      {priceData ? (
                        <StockChart data={priceData.history} color={chartColor} height={220} />
                      ) : (
                        <div className="h-full flex items-center justify-center text-gray-600">Loading Chart...</div>
                      )}
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
                                className="flex items-center gap-2 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-bold rounded-md transition-all"
                             >
                               {isCopied ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
                               {isCopied ? 'Copied' : 'Copy'}
                             </button>
                          </div>
                        </div>

                        {/* Executive Summary */}
                        <div className="prose prose-invert prose-sm max-w-none bg-gray-900/50 p-4 rounded-lg border border-gray-800 shadow-inner">
                            {analysis.reasoning.split('\n').map((line, i) => (
                              <p key={i} className={`mb-2 ${line.startsWith('#') ? 'font-bold text-lg text-blue-200' : ''}`}>
                                {line.replace(/\*\*/g, '')}
                              </p>
                            ))}
                        </div>
                        
                        {/* --- RESEARCHER TEAM DEBATE (ENHANCED UI) --- */}
                        {analysis.debate && (
                            <div className="space-y-4 mt-6">
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-2">
                                        <Gavel className="w-5 h-5 text-orange-400" />
                                        <h3 className="text-lg font-bold text-white">Researcher Team Debate</h3>
                                    </div>
                                </div>

                                {/* Debate Balance Meter - 使用增强组件 */}
                                <DebateMeter debate={analysis.debate} />

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {/* Bull Agent Card */}
                                    <div className={`bg-green-950/20 border rounded-lg p-4 relative overflow-hidden transition-all ${analysis.debate.winner === 'Bull' ? 'border-green-500/60 shadow-[0_0_15px_rgba(34,197,94,0.1)]' : 'border-green-900/40'}`}>
                                        <div className="absolute top-0 right-0 p-2 opacity-10">
                                            <TrendingUp className="w-24 h-24 text-green-500" />
                                        </div>
                                        <div className="flex justify-between items-start mb-3 border-b border-green-900/30 pb-2">
                                            <h4 className="text-green-400 font-bold flex items-center gap-2">
                                                <Bot className="w-4 h-4" /> Bull Agent
                                            </h4>
                                            {analysis.debate.winner === 'Bull' && <span className="text-[10px] bg-green-500 text-black px-1.5 py-0.5 rounded font-bold uppercase">Winner</span>}
                                        </div>
                                        <p className="text-sm font-semibold text-green-100 mb-3 italic leading-relaxed">"{analysis.debate.bull.thesis}"</p>
                                        <ul className="space-y-2">
                                            {analysis.debate.bull.points.map((p, i) => (
                                                <li key={i} className="text-xs text-gray-300 flex gap-2 items-start">
                                                    <span className="mt-1.5 w-1 h-1 rounded-full bg-green-500 shrink-0"></span>
                                                    <span>{p.argument}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>

                                    {/* Bear Agent Card */}
                                    <div className={`bg-red-950/20 border rounded-lg p-4 relative overflow-hidden transition-all ${analysis.debate.winner === 'Bear' ? 'border-red-500/60 shadow-[0_0_15px_rgba(239,68,68,0.1)]' : 'border-red-900/40'}`}>
                                        <div className="absolute top-0 right-0 p-2 opacity-10">
                                            <TrendingDown className="w-24 h-24 text-red-500" />
                                        </div>
                                        <div className="flex justify-between items-start mb-3 border-b border-red-900/30 pb-2">
                                            <h4 className="text-red-400 font-bold flex items-center gap-2">
                                                <Bot className="w-4 h-4" /> Bear Agent
                                            </h4>
                                            {analysis.debate.winner === 'Bear' && <span className="text-[10px] bg-red-500 text-white px-1.5 py-0.5 rounded font-bold uppercase">Winner</span>}
                                        </div>
                                        <p className="text-sm font-semibold text-red-100 mb-3 italic leading-relaxed">"{analysis.debate.bear.thesis}"</p>
                                        <ul className="space-y-2">
                                            {analysis.debate.bear.points.map((p, i) => (
                                                <li key={i} className="text-xs text-gray-300 flex gap-2 items-start">
                                                    <span className="mt-1.5 w-1 h-1 rounded-full bg-red-500 shrink-0"></span>
                                                    <span>{p.argument}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                </div>
                                <div className="bg-gray-800/50 p-3 rounded text-xs text-gray-400 border-l-2 border-gray-600 italic">
                                    <span className="font-bold text-gray-300 not-italic">Moderator Conclusion:</span> {analysis.debate.conclusion}
                                </div>
                            </div>
                        )}

                      </div>
                    )}
                </div>

                {/* --- RIGHT COLUMN: Trade Setup & Stats --- */}
                <div className="space-y-6">
                    {analysis ? (
                      <div className="space-y-6">
                        {/* Signal & Trade Setup Card */}
                        <div className="bg-gray-800/40 rounded-xl p-5 border border-gray-700">
                            <div className={`text-center py-4 rounded-lg border-2 mb-6 ${
                                analysis.signal.includes('Buy') ? 'border-green-500 bg-green-500/10 text-green-400' :
                                analysis.signal.includes('Sell') ? 'border-red-500 bg-red-500/10 text-red-400' :
                                'border-yellow-500 bg-yellow-500/10 text-yellow-400'
                            }`}>
                              <div className="text-2xl font-black uppercase tracking-wider">{analysis.signal}</div>
                              <div className="text-sm font-mono opacity-80">{analysis.confidence}% Confidence</div>
                            </div>

                            {/* Trade Setup Visualizer */}
                            {analysis.tradeSetup ? (
                                <div className="space-y-4">
                                   <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
                                      <span className="flex items-center gap-1"><Scale className="w-3 h-3" /> Risk/Reward</span>
                                      <span className={`font-mono font-bold ${analysis.tradeSetup.rewardToRiskRatio > 2 ? 'text-green-400' : 'text-gray-300'}`}>
                                        {analysis.tradeSetup.rewardToRiskRatio}R
                                      </span>
                                   </div>

                                   <div className="space-y-2">
                                      {/* Target */}
                                      <div className="flex justify-between items-center p-2.5 bg-gray-900/80 rounded border-l-4 border-green-500 hover:bg-gray-800 transition-colors">
                                          <div className="flex flex-col">
                                            <span className="text-[10px] text-gray-500 uppercase">Target</span>
                                            <span className="text-green-400 font-mono font-bold">{analysis.tradeSetup.targetPrice}</span>
                                          </div>
                                          <Target className="w-4 h-4 text-green-500/50" />
                                      </div>
                                      
                                      {/* Entry Zone */}
                                      <div className="flex justify-between items-center p-2.5 bg-gray-900/80 rounded border-l-4 border-blue-500 hover:bg-gray-800 transition-colors">
                                          <div className="flex flex-col">
                                            <span className="text-[10px] text-gray-500 uppercase">Entry Zone</span>
                                            <span className="text-blue-400 font-mono font-bold">{analysis.tradeSetup.entryZone}</span>
                                          </div>
                                          <div className="text-[10px] text-blue-300 bg-blue-500/20 px-2 py-0.5 rounded">Buy Zone</div>
                                      </div>

                                      {/* Stop Loss */}
                                      <div className="flex justify-between items-center p-2.5 bg-gray-900/80 rounded border-l-4 border-red-500 hover:bg-gray-800 transition-colors">
                                          <div className="flex flex-col">
                                            <span className="text-[10px] text-gray-500 uppercase">Stop Loss</span>
                                            <span className="text-red-400 font-mono font-bold">{analysis.tradeSetup.stopLossPrice}</span>
                                          </div>
                                          <ShieldAlert className="w-4 h-4 text-red-500/50" />
                                      </div>
                                   </div>
                                </div>
                            ) : (
                                <div className="text-center text-xs text-gray-500 py-4">No specific trade setup generated.</div>
                            )}
                        </div>

                        {/* --- RISK MANAGEMENT TEAM (ENHANCED UI) --- */}
                        {analysis.riskAssessment && (
                             <div className="bg-gray-800/40 rounded-xl p-4 border border-gray-700">
                                <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                                  <ShieldAlert className="w-4 h-4" /> Risk Assessment
                                </h4>

                                <div className="flex items-center justify-between mb-4">
                                    {/* 使用增强的半圆仪表盘组件 */}
                                    <RiskGauge score={analysis.riskAssessment.score} verdict={analysis.riskAssessment.verdict} />

                                    <div className="text-right">
                                        <div className={`inline-block px-3 py-1 rounded-full text-xs font-bold border mb-1 ${
                                            analysis.riskAssessment.verdict === 'Approved' ? 'bg-green-500/20 border-green-500 text-green-400' :
                                            analysis.riskAssessment.verdict === 'Rejected' ? 'bg-red-500/20 border-red-500 text-red-400' :
                                            'bg-yellow-500/20 border-yellow-500 text-yellow-400'
                                        }`}>
                                            {analysis.riskAssessment.verdict.toUpperCase()}
                                        </div>
                                        <p className="text-[10px] text-gray-500">Risk Score (0-10)</p>
                                    </div>
                                </div>

                                <div className="space-y-2 text-xs">
                                    <div className="flex justify-between border-b border-gray-700/50 pb-1">
                                        <span className="text-gray-400">Volatility</span>
                                        <span className="text-gray-200">{analysis.riskAssessment.volatilityStatus}</span>
                                    </div>
                                    <div className="flex justify-between border-b border-gray-700/50 pb-1">
                                        <span className="text-gray-400">Max Drawdown Risk</span>
                                        <span className="text-gray-200">{analysis.riskAssessment.maxDrawdownRisk}</span>
                                    </div>
                                    <div className="flex justify-between pt-1">
                                        <span className="text-gray-400">Liquidity</span>
                                        <span className={analysis.riskAssessment.liquidityConcerns ? "text-red-400 font-bold" : "text-green-400"}>
                                            {analysis.riskAssessment.liquidityConcerns ? "Concerns Detected" : "Good"}
                                        </span>
                                    </div>
                                </div>
                             </div>
                        )}

                        {/* Price Levels (Visual Bar) */}
                        {analysis.priceLevels && priceData && (
                          <div className="bg-gray-800/40 rounded-xl p-4 border border-gray-700">
                            <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                              <BarChart2 className="w-4 h-4" /> Technical Levels
                            </h4>
                            <div className="relative h-12 mt-6 mb-2">
                              {/* Range Bar */}
                              <div className="absolute top-1/2 left-0 right-0 h-1 bg-gray-700 -translate-y-1/2 rounded-full"></div>
                              
                              {/* Support */}
                              <div className="absolute top-1/2 -translate-y-1/2" style={{ left: '0%' }}>
                                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                                <div className="absolute top-4 left-0 -translate-x-1/2 text-[10px] text-green-400 font-mono whitespace-nowrap">
                                  Sup: {analysis.priceLevels.support}
                                </div>
                              </div>
                              
                              {/* Resistance */}
                              <div className="absolute top-1/2 -translate-y-1/2" style={{ right: '0%' }}>
                                <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                                <div className="absolute top-4 right-0 translate-x-1/2 text-[10px] text-red-400 font-mono whitespace-nowrap">
                                  Res: {analysis.priceLevels.resistance}
                                </div>
                              </div>

                              {/* Current Price Marker */}
                              <div 
                                className="absolute top-1/2 -translate-y-1/2 transition-all duration-500"
                                style={{ 
                                  left: `${calculatePosition(priceData.price, analysis.priceLevels.support * 0.98, analysis.priceLevels.resistance * 1.02)}%` 
                                }}
                              >
                                <div className="w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[8px] border-t-white -translate-x-1/2 -translate-y-full mb-1"></div>
                                <div className="absolute -top-6 left-0 -translate-x-1/2 bg-white text-gray-950 text-[10px] font-bold px-1.5 rounded shadow-sm">
                                  {priceData.price.toFixed(2)}
                                </div>
                              </div>
                            </div>
                          </div>
                        )}

                      </div>
                    ) : (
                      <div className="bg-gray-800/40 rounded-xl p-8 border border-gray-700 text-center text-gray-500">
                        Run analysis to see data.
                      </div>
                    )}
                </div>
              </div>
            ) : (
              // CHAT INTERFACE
              <div className="h-full flex flex-col">
                <div className="flex-1 overflow-y-auto pr-2 space-y-4">
                   {messages.map((msg, idx) => (
                     <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[80%] rounded-lg p-3 ${
                          msg.role === 'user' 
                            ? 'bg-blue-600 text-white rounded-br-none' 
                            : 'bg-gray-800 text-gray-200 rounded-bl-none border border-gray-700'
                        }`}>
                           <div className="flex items-center gap-2 mb-1 opacity-50 text-xs">
                              {msg.role === 'model' ? <Bot className="w-3 h-3" /> : 'You'}
                           </div>
                           <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.text}</p>
                        </div>
                     </div>
                   ))}
                   {isTyping && (
                     <div className="flex justify-start">
                        <div className="bg-gray-800 text-gray-400 rounded-lg p-3 rounded-bl-none border border-gray-700 text-sm flex items-center gap-2">
                          <Bot className="w-3 h-3" /> Thinking...
                        </div>
                     </div>
                   )}
                   <div ref={messagesEndRef} />
                </div>
                
                <form onSubmit={handleSendMessage} className="mt-4 relative">
                   <input 
                      type="text" 
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder={analysis ? "Ask about risks, targets, or details..." : "Run analysis first to chat..."}
                      disabled={!analysis || isTyping}
                      className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg pl-4 pr-12 py-3 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
                   />
                   <button 
                      type="submit" 
                      disabled={!input.trim() || !analysis || isTyping}
                      className="absolute right-2 top-2 p-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 transition-colors"
                   >
                     <Send className="w-4 h-4" />
                   </button>
                </form>
              </div>
            )}

          </div>
        </div>
      </div>
    </div>
  );
};

export default StockDetailModal;