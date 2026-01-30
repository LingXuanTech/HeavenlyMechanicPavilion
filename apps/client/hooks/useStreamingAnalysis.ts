import { useState, useEffect, useCallback, useRef } from 'react';
import { useStreamTypewriter } from './useTypewriter';
import type { AgentAnalysis } from '../types';
import { API_BASE } from '../services/api';

/**
 * SSE 流式事件类型
 */
interface SSETextChunkEvent {
  event: 'text_chunk';
  data: {
    stage: string;
    chunk: string;
    progress: number;
    is_complete: boolean;
  };
}

interface SSEStageEvent {
  event: string;
  data: {
    node?: string;
    stage?: string;
    status?: string;
    message?: string;
  };
}

interface SSEAnalysisCompleteEvent {
  event: 'analysis_complete';
  data: AgentAnalysis;
}

type SSEEvent = SSETextChunkEvent | SSEStageEvent | SSEAnalysisCompleteEvent;

/**
 * 流式分析状态
 */
export interface StreamingAnalysisState {
  /** 当前阶段 */
  stage: 'idle' | 'analyst' | 'debate' | 'risk' | 'synthesis' | 'complete' | 'error';
  /** 阶段进度 (0-100) */
  stageProgress: number;
  /** 流式推理文本（正在显示的） */
  streamingReasoning: string;
  /** 完整推理文本（已接收的） */
  fullReasoning: string;
  /** 是否正在打字 */
  isTyping: boolean;
  /** 最终分析结果 */
  analysis: AgentAnalysis | null;
  /** 错误信息 */
  error: string | null;
  /** 是否已连接 */
  isConnected: boolean;
}

/**
 * 流式分析 Hook 配置
 */
export interface UseStreamingAnalysisOptions {
  /** 打字速度 (ms/字符) */
  typewriterSpeed?: number;
  /** 是否自动开始 */
  autoStart?: boolean;
  /** 阶段变化回调 */
  onStageChange?: (stage: string) => void;
  /** 完成回调 */
  onComplete?: (analysis: AgentAnalysis) => void;
  /** 错误回调 */
  onError?: (error: string) => void;
}

/**
 * 流式分析 Hook
 *
 * 连接 SSE 事件流，提供实时的分析进度和流式推理文本显示
 *
 * @example
 * ```tsx
 * const {
 *   state,
 *   startAnalysis,
 *   skipTypewriter,
 *   disconnect,
 * } = useStreamingAnalysis({ typewriterSpeed: 15 });
 *
 * // 开始分析
 * startAnalysis('AAPL');
 *
 * // 在 UI 中显示
 * <div>{state.streamingReasoning}</div>
 * {state.isTyping && <button onClick={skipTypewriter}>跳过</button>}
 * ```
 */
export function useStreamingAnalysis(options: UseStreamingAnalysisOptions = {}) {
  const {
    typewriterSpeed = 15,
    onStageChange,
    onComplete,
    onError,
  } = options;

  // 流式打字机
  const {
    displayedText,
    fullText,
    isTyping,
    append,
    skip: skipTypewriter,
    clear: clearTypewriter,
  } = useStreamTypewriter({ speed: typewriterSpeed });

  // 状态
  const [stage, setStage] = useState<StreamingAnalysisState['stage']>('idle');
  const [stageProgress, setStageProgress] = useState(0);
  const [analysis, setAnalysis] = useState<AgentAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  // Refs
  const eventSourceRef = useRef<EventSource | null>(null);
  const taskIdRef = useRef<string | null>(null);

  // 断开连接
  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsConnected(false);
  }, []);

  // 重置状态
  const reset = useCallback(() => {
    disconnect();
    setStage('idle');
    setStageProgress(0);
    setAnalysis(null);
    setError(null);
    clearTypewriter();
    taskIdRef.current = null;
  }, [disconnect, clearTypewriter]);

  // 开始分析
  const startAnalysis = useCallback(async (symbol: string, date?: string) => {
    reset();
    setStage('analyst');

    try {
      // 1. 发起分析请求，获取 task_id
      const tradeDate = date || new Date().toISOString().split('T')[0];
      const response = await fetch(`${API_BASE}/analyze/${symbol}?trade_date=${tradeDate}`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`Analysis request failed: ${response.status}`);
      }

      const data = await response.json();
      const taskId = data.task_id;
      taskIdRef.current = taskId;

      // 2. 连接 SSE 流
      const eventSource = new EventSource(`${API_BASE}/analyze/stream/${taskId}`);
      eventSourceRef.current = eventSource;
      setIsConnected(true);

      eventSource.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as SSEEvent;

          // 处理文本块事件
          if (parsed.event === 'text_chunk') {
            const chunkData = (parsed as SSETextChunkEvent).data;
            append(chunkData.chunk);
            setStageProgress(chunkData.progress);
          }
          // 处理阶段事件
          else if (parsed.event?.startsWith('stage_')) {
            const stageData = (parsed as SSEStageEvent).data;
            const newStage = stageData.stage || parsed.event.replace('stage_', '');

            if (newStage === 'analyst') setStage('analyst');
            else if (newStage === 'debate') setStage('debate');
            else if (newStage === 'risk') setStage('risk');
            else if (newStage === 'final') setStage('synthesis');

            onStageChange?.(newStage);
          }
          // 处理完成事件
          else if (parsed.event === 'analysis_complete') {
            const analysisData = (parsed as SSEAnalysisCompleteEvent).data;
            setAnalysis(analysisData);
            setStage('complete');
            setStageProgress(100);
            disconnect();
            onComplete?.(analysisData);
          }
          // 处理错误事件
          else if (parsed.event === 'error') {
            const errMsg = (parsed as SSEStageEvent).data.message || 'Unknown error';
            setError(errMsg);
            setStage('error');
            disconnect();
            onError?.(errMsg);
          }
        } catch {
          // 忽略解析错误
        }
      };

      eventSource.onerror = () => {
        setError('Connection lost');
        setStage('error');
        disconnect();
        onError?.('Connection lost');
      };

    } catch (err) {
      const errMsg = err instanceof Error ? err.message : 'Unknown error';
      setError(errMsg);
      setStage('error');
      onError?.(errMsg);
    }
  }, [reset, append, disconnect, onStageChange, onComplete, onError]);

  // 清理
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  // 构建状态对象
  const state: StreamingAnalysisState = {
    stage,
    stageProgress,
    streamingReasoning: displayedText,
    fullReasoning: fullText,
    isTyping,
    analysis,
    error,
    isConnected,
  };

  return {
    state,
    startAnalysis,
    skipTypewriter,
    reset,
    disconnect,
  };
}

export default useStreamingAnalysis;
