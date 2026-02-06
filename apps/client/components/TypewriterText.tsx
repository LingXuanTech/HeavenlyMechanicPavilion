import React, { memo } from 'react';
import { useTypewriter, UseTypewriterOptions } from '../hooks/useTypewriter';
import { SkipForward, Pause, Play } from 'lucide-react';

/**
 * TypewriterText 组件属性
 */
export interface TypewriterTextProps extends UseTypewriterOptions {
  /** 要显示的文本 */
  text: string;
  /** 自定义类名 */
  className?: string;
  /** 是否显示控制按钮 */
  showControls?: boolean;
  /** 是否显示进度条 */
  showProgress?: boolean;
  /** 光标字符，默认 '▌' */
  cursorChar?: string;
  /** 光标类名 */
  cursorClassName?: string;
  /** 渲染文本的方式 */
  renderText?: (text: string) => React.ReactNode;
}

/**
 * 打字机文本组件
 *
 * 提供开箱即用的打字机效果，支持暂停、继续、跳过等控制
 *
 * @example
 * ```tsx
 * // 基础用法
 * <TypewriterText text={analysis.reasoning} speed={20} />
 *
 * // 带控制按钮
 * <TypewriterText
 *   text={longText}
 *   showControls
 *   showProgress
 *   speed={30}
 * />
 *
 * // 自定义渲染
 * <TypewriterText
 *   text={markdownText}
 *   renderText={(text) => <ReactMarkdown>{text}</ReactMarkdown>}
 * />
 * ```
 */
export const TypewriterText: React.FC<TypewriterTextProps> = memo(({
  text,
  className = '',
  showControls = false,
  showProgress = false,
  cursorChar = '▌',
  cursorClassName = 'animate-pulse text-accent',
  renderText,
  ...options
}) => {
  const {
    displayedText,
    isTyping,
    isPaused,
    isComplete,
    progress,
    pause,
    resume,
    skip,
  } = useTypewriter(text, options);

  return (
    <div className={`relative ${className}`}>
      {/* 进度条 */}
      {showProgress && !isComplete && (
        <div className="absolute -top-2 left-0 right-0 h-0.5 bg-border-strong rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-accent to-purple-500 transition-all duration-100"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* 文本内容 */}
      <div className="relative">
        {renderText ? (
          renderText(displayedText)
        ) : (
          <span>{displayedText}</span>
        )}

        {/* 光标 */}
        {isTyping && (
          <span className={cursorClassName}>{cursorChar}</span>
        )}
      </div>

      {/* 控制按钮 */}
      {showControls && !isComplete && (
        <div className="flex items-center gap-2 mt-3">
          {isTyping ? (
            <button
              onClick={pause}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-stone-300 bg-surface-overlay hover:bg-surface-muted rounded-md transition-colors"
            >
              <Pause className="w-3 h-3" />
              暂停
            </button>
          ) : isPaused ? (
            <button
              onClick={resume}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-stone-300 bg-surface-overlay hover:bg-surface-muted rounded-md transition-colors"
            >
              <Play className="w-3 h-3" />
              继续
            </button>
          ) : null}

          <button
            onClick={skip}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-stone-400 hover:text-stone-200 transition-colors"
          >
            <SkipForward className="w-3 h-3" />
            跳过
          </button>

          {showProgress && (
            <span className="text-xs text-stone-500 ml-2">{progress}%</span>
          )}
        </div>
      )}
    </div>
  );
});

TypewriterText.displayName = 'TypewriterText';

/**
 * 分析推理打字机组件
 *
 * 专门用于显示 AI 分析推理过程的打字机效果
 */
export interface AnalysisTypewriterProps {
  /** 推理文本 */
  reasoning: string;
  /** 是否启用打字机效果 */
  enabled?: boolean;
  /** 打字速度 */
  speed?: number;
  /** 完成回调 */
  onComplete?: () => void;
}

export const AnalysisTypewriter: React.FC<AnalysisTypewriterProps> = memo(({
  reasoning,
  enabled = true,
  speed = 15,
  onComplete,
}) => {
  const {
    displayedText,
    isTyping,
    isComplete,
    skip,
    progress,
  } = useTypewriter(reasoning, {
    speed,
    autoStart: enabled,
    onComplete,
  });

  // 如果禁用打字机效果，直接显示完整文本
  if (!enabled) {
    return (
      <div className="prose prose-invert prose-sm max-w-none bg-surface-raised/50 p-4 rounded-lg border border-border shadow-inner">
        {reasoning.split('\n').map((line, i) => (
          <p key={i} className={`mb-2 ${line.startsWith('#') ? 'font-bold text-lg text-amber-200' : ''}`}>
            {line.replace(/\*\*/g, '')}
          </p>
        ))}
      </div>
    );
  }

  // 将显示的文本按换行符分割
  const lines = displayedText.split('\n');

  return (
    <div className="prose prose-invert prose-sm max-w-none bg-surface-raised/50 p-4 rounded-lg border border-border shadow-inner relative">
      {/* 进度指示器 */}
      {isTyping && (
        <div className="absolute top-2 right-2 flex items-center gap-2">
          <div className="w-16 h-1 bg-border-strong rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-accent to-purple-500 transition-all duration-100"
              style={{ width: `${progress}%` }}
            />
          </div>
          <button
            onClick={skip}
            className="text-xs text-stone-500 hover:text-stone-300 transition-colors"
            title="跳过动画"
          >
            <SkipForward className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* 文本内容 */}
      {lines.map((line, i) => (
        <p key={i} className={`mb-2 ${line.startsWith('#') ? 'font-bold text-lg text-amber-200' : ''}`}>
          {line.replace(/\*\*/g, '')}
          {/* 光标显示在最后一行末尾 */}
          {isTyping && i === lines.length - 1 && (
            <span className="animate-pulse text-accent ml-0.5">▌</span>
          )}
        </p>
      ))}

      {/* 完成状态指示 */}
      {isComplete && (
        <div className="absolute bottom-2 right-2 text-xs text-green-500/60 flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
          分析完成
        </div>
      )}
    </div>
  );
});

AnalysisTypewriter.displayName = 'AnalysisTypewriter';

export default TypewriterText;
