import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * 打字机效果配置选项
 */
export interface UseTypewriterOptions {
  /** 每字符延迟（ms），默认 30 */
  speed?: number;
  /** 是否立即开始，默认 true */
  autoStart?: boolean;
  /** 完成回调 */
  onComplete?: () => void;
  /** 是否启用光标闪烁，默认 true */
  cursor?: boolean;
}

/**
 * 打字机效果返回值
 */
export interface UseTypewriterReturn {
  /** 当前显示的文本 */
  displayedText: string;
  /** 是否正在打字 */
  isTyping: boolean;
  /** 是否已完成 */
  isComplete: boolean;
  /** 是否已暂停 */
  isPaused: boolean;
  /** 当前进度 (0-100) */
  progress: number;
  /** 暂停打字 */
  pause: () => void;
  /** 继续打字 */
  resume: () => void;
  /** 跳过动画，直接显示完整文本 */
  skip: () => void;
  /** 重新开始 */
  restart: () => void;
}

/**
 * 打字机效果 Hook
 *
 * @param text 要显示的完整文本
 * @param options 配置选项
 * @returns 打字机状态和控制方法
 *
 * @example
 * ```tsx
 * const { displayedText, isTyping, skip } = useTypewriter(analysis.reasoning, { speed: 20 });
 *
 * return (
 *   <div>
 *     <p>{displayedText}</p>
 *     {isTyping && <button onClick={skip}>跳过</button>}
 *   </div>
 * );
 * ```
 */
export function useTypewriter(
  text: string,
  options: UseTypewriterOptions = {}
): UseTypewriterReturn {
  const { speed = 30, autoStart = true, onComplete, cursor = true } = options;

  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isComplete, setIsComplete] = useState(false);

  const indexRef = useRef(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const textRef = useRef(text);

  // 清理定时器
  const clearTimer = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // 开始打字
  const startTyping = useCallback(() => {
    if (!textRef.current || intervalRef.current) return;

    setIsTyping(true);
    setIsPaused(false);
    setIsComplete(false);

    intervalRef.current = setInterval(() => {
      if (indexRef.current < textRef.current.length) {
        setDisplayedText(textRef.current.slice(0, indexRef.current + 1));
        indexRef.current++;
      } else {
        clearTimer();
        setIsTyping(false);
        setIsComplete(true);
        onComplete?.();
      }
    }, speed);
  }, [speed, onComplete, clearTimer]);

  // 暂停
  const pause = useCallback(() => {
    clearTimer();
    setIsPaused(true);
    setIsTyping(false);
  }, [clearTimer]);

  // 继续
  const resume = useCallback(() => {
    if (isPaused && !isComplete) {
      setIsPaused(false);
      startTyping();
    }
  }, [isPaused, isComplete, startTyping]);

  // 跳过
  const skip = useCallback(() => {
    clearTimer();
    setDisplayedText(textRef.current);
    indexRef.current = textRef.current.length;
    setIsTyping(false);
    setIsPaused(false);
    setIsComplete(true);
    onComplete?.();
  }, [clearTimer, onComplete]);

  // 重新开始
  const restart = useCallback(() => {
    clearTimer();
    indexRef.current = 0;
    setDisplayedText('');
    setIsComplete(false);
    setIsPaused(false);
    if (autoStart) {
      startTyping();
    }
  }, [clearTimer, autoStart, startTyping]);

  // 文本变化时重新开始
  useEffect(() => {
    textRef.current = text;
    clearTimer();
    indexRef.current = 0;
    setDisplayedText('');
    setIsComplete(false);
    setIsPaused(false);

    if (text && autoStart) {
      startTyping();
    }

    return clearTimer;
  }, [text, autoStart, startTyping, clearTimer]);

  // 计算进度
  const progress = textRef.current.length > 0
    ? Math.round((displayedText.length / textRef.current.length) * 100)
    : 0;

  return {
    displayedText,
    isTyping,
    isComplete,
    isPaused,
    progress,
    pause,
    resume,
    skip,
    restart,
  };
}

/**
 * 流式打字机 Hook - 用于处理 SSE 流式数据
 *
 * 与 useTypewriter 不同，此 Hook 支持动态追加文本
 */
export interface UseStreamTypewriterOptions {
  /** 每字符延迟（ms），默认 15 */
  speed?: number;
  /** 新增文本时的回调 */
  onChunk?: (chunk: string) => void;
}

export interface UseStreamTypewriterReturn {
  /** 当前显示的文本 */
  displayedText: string;
  /** 完整文本（包括未显示的部分） */
  fullText: string;
  /** 是否正在打字 */
  isTyping: boolean;
  /** 追加新文本 */
  append: (chunk: string) => void;
  /** 跳过当前动画 */
  skip: () => void;
  /** 清空所有文本 */
  clear: () => void;
}

/**
 * 流式打字机 Hook
 *
 * 用于处理 SSE 流式数据，支持动态追加文本
 *
 * @example
 * ```tsx
 * const { displayedText, append, isTyping } = useStreamTypewriter({ speed: 15 });
 *
 * // SSE 事件处理
 * useEffect(() => {
 *   eventSource.onmessage = (event) => {
 *     append(event.data);
 *   };
 * }, [append]);
 * ```
 */
export function useStreamTypewriter(
  options: UseStreamTypewriterOptions = {}
): UseStreamTypewriterReturn {
  const { speed = 15, onChunk } = options;

  const [displayedText, setDisplayedText] = useState('');
  const [fullText, setFullText] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  const indexRef = useRef(0);
  const fullTextRef = useRef('');
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 清理定时器
  const clearTimer = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // 开始/继续打字
  const startTyping = useCallback(() => {
    if (intervalRef.current) return;

    setIsTyping(true);

    intervalRef.current = setInterval(() => {
      if (indexRef.current < fullTextRef.current.length) {
        setDisplayedText(fullTextRef.current.slice(0, indexRef.current + 1));
        indexRef.current++;
      } else {
        clearTimer();
        setIsTyping(false);
      }
    }, speed);
  }, [speed, clearTimer]);

  // 追加文本
  const append = useCallback((chunk: string) => {
    fullTextRef.current += chunk;
    setFullText(fullTextRef.current);
    onChunk?.(chunk);

    // 如果不在打字，开始打字
    if (!intervalRef.current) {
      startTyping();
    }
  }, [startTyping, onChunk]);

  // 跳过
  const skip = useCallback(() => {
    clearTimer();
    setDisplayedText(fullTextRef.current);
    indexRef.current = fullTextRef.current.length;
    setIsTyping(false);
  }, [clearTimer]);

  // 清空
  const clear = useCallback(() => {
    clearTimer();
    fullTextRef.current = '';
    indexRef.current = 0;
    setDisplayedText('');
    setFullText('');
    setIsTyping(false);
  }, [clearTimer]);

  // 清理
  useEffect(() => {
    return clearTimer;
  }, [clearTimer]);

  return {
    displayedText,
    fullText,
    isTyping,
    append,
    skip,
    clear,
  };
}

export default useTypewriter;
