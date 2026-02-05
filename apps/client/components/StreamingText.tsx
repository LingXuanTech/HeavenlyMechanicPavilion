import React, { memo, useEffect } from 'react';
import { useStreamTypewriter } from '../hooks/useTypewriter';
import { SkipForward, Loader2 } from 'lucide-react';

/**
 * 流式文本组件属性
 */
export interface StreamingTextProps {
  /** 当前已接收的完整文本 */
  text: string;
  /** 是否正在接收数据 */
  isStreaming?: boolean;
  /** 打字速度 (ms/字符) */
  speed?: number;
  /** 自定义类名 */
  className?: string;
  /** 是否显示跳过按钮 */
  showSkip?: boolean;
  /** 光标字符 */
  cursorChar?: string;
  /** 渲染文本的方式 */
  renderText?: (text: string) => React.ReactNode;
  /** 完成回调 */
  onComplete?: () => void;
}

/**
 * 流式文本组件
 *
 * 用于显示从 SSE 接收的流式文本，带打字机效果
 *
 * @example
 * ```tsx
 * // 基础用法
 * <StreamingText
 *   text={streamingReasoning}
 *   isStreaming={isTyping}
 *   speed={15}
 * />
 *
 * // 自定义渲染
 * <StreamingText
 *   text={reasoning}
 *   renderText={(text) => <ReactMarkdown>{text}</ReactMarkdown>}
 * />
 * ```
 */
export const StreamingText: React.FC<StreamingTextProps> = memo(({
  text,
  isStreaming = false,
  speed = 15,
  className = '',
  showSkip = true,
  cursorChar = '▌',
  renderText,
  onComplete,
}) => {
  const {
    displayedText,
    isTyping,
    skip,
  } = useStreamTypewriter({ speed, onChunk: undefined });

  // 当文本变化时追加
  useEffect(() => {
    // 这里不需要做什么，因为我们直接使用传入的 text
    // 流式效果由 useStreamTypewriter 内部处理
  }, [text]);

  // 如果已完成且有回调，则调用
  useEffect(() => {
    if (!isTyping && !isStreaming && displayedText === text && text.length > 0) {
      onComplete?.();
    }
  }, [isTyping, isStreaming, displayedText, text, onComplete]);

  // 将文本按换行符分割以便正确渲染
  const lines = text.split('\n');

  return (
    <div className={`relative ${className}`}>
      {/* 流式指示器 */}
      {(isStreaming || isTyping) && (
        <div className="absolute top-2 right-2 flex items-center gap-2 z-10">
          {isStreaming && (
            <span className="flex items-center gap-1.5 text-xs text-blue-400">
              <Loader2 className="w-3 h-3 animate-spin" />
              接收中...
            </span>
          )}
          {showSkip && (
            <button
              onClick={skip}
              className="flex items-center gap-1 px-2 py-1 text-xs text-gray-400 hover:text-gray-200 bg-gray-800/80 hover:bg-gray-700/80 rounded transition-colors"
              title="跳过动画"
            >
              <SkipForward className="w-3 h-3" />
              跳过
            </button>
          )}
        </div>
      )}

      {/* 文本内容 */}
      <div className="prose prose-invert prose-sm max-w-none">
        {renderText ? (
          renderText(text)
        ) : (
          lines.map((line, i) => (
            <p
              key={i}
              className={`mb-2 ${line.startsWith('#') ? 'font-bold text-lg text-blue-200' : ''} ${line.startsWith('##') ? 'font-semibold text-base text-blue-300' : ''}`}
            >
              {line.replace(/\*\*/g, '').replace(/^#+\s*/, '')}
              {/* 光标显示在最后一行末尾 */}
              {(isTyping || isStreaming) && i === lines.length - 1 && (
                <span className="animate-pulse text-blue-400 ml-0.5">{cursorChar}</span>
              )}
            </p>
          ))
        )}
      </div>
    </div>
  );
});

StreamingText.displayName = 'StreamingText';

/**
 * 分析推理流式组件
 *
 * 专门用于显示 AI 分析推理的流式文本
 */
export interface StreamingReasoningProps {
  /** 推理文本 */
  reasoning: string;
  /** 是否正在流式传输 */
  isStreaming?: boolean;
  /** 当前阶段 */
  stage?: string;
  /** 进度 (0-100) */
  progress?: number;
  /** 完成回调 */
  onComplete?: () => void;
}

export const StreamingReasoning: React.FC<StreamingReasoningProps> = memo(({
  reasoning,
  isStreaming = false,
  stage = '',
  progress = 0,
}) => {
  // 阶段标签映射
  const stageLabels: Record<string, string> = {
    analyst: '📊 分析师团队',
    debate: '⚔️ 多空辩论',
    risk: '⚠️ 风险评估',
    synthesis: '📝 报告合成',
    complete: '✅ 完成',
  };

  const lines = reasoning.split('\n');

  return (
    <div className="bg-gray-900/50 rounded-lg border border-gray-800 shadow-inner overflow-hidden">
      {/* 头部：阶段和进度 */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800/50 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-200">
            {stageLabels[stage] || stage}
          </span>
          {isStreaming && (
            <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
          )}
        </div>
        {progress > 0 && (
          <div className="flex items-center gap-2">
            <div className="w-24 h-1.5 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-xs text-gray-400">{Math.round(progress)}%</span>
          </div>
        )}
      </div>

      {/* 推理内容 */}
      <div className="p-4 max-h-96 overflow-y-auto">
        {lines.map((line, i) => (
          <p
            key={i}
            className={`mb-2 text-sm leading-relaxed ${
              line.startsWith('#') ? 'font-bold text-blue-200 mt-3' :
              line.startsWith('-') ? 'pl-4 text-gray-300' :
              'text-gray-200'
            }`}
          >
            {line.replace(/\*\*/g, '').replace(/^#+\s*/, '')}
            {/* 光标显示在最后一行末尾 */}
            {isStreaming && i === lines.length - 1 && line && (
              <span className="animate-pulse text-blue-400 ml-0.5">▌</span>
            )}
          </p>
        ))}

        {/* 空状态 */}
        {!reasoning && isStreaming && (
          <div className="flex items-center gap-2 text-gray-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">等待分析结果...</span>
          </div>
        )}
      </div>

      {/* 完成指示 */}
      {!isStreaming && reasoning && (
        <div className="px-4 py-2 bg-gray-800/30 border-t border-gray-700/50 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-xs text-green-400/80">分析完成</span>
        </div>
      )}
    </div>
  );
});

StreamingReasoning.displayName = 'StreamingReasoning';

export default StreamingText;
