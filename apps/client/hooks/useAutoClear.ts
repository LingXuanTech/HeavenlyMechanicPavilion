import { useEffect } from 'react';

/**
 * 在指定延时后自动触发清理回调。
 * 常用于提示消息自动消失。
 */
export function useAutoClear(value: unknown, onClear: () => void, delayMs: number): void {
  useEffect(() => {
    if (value == null || typeof window === 'undefined') {
      return;
    }

    const timer = window.setTimeout(onClear, delayMs);
    return () => window.clearTimeout(timer);
  }, [value, onClear, delayMs]);
}
