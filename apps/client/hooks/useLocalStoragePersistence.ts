import { useEffect } from 'react';

/**
 * 将值以 JSON 形式持久化到 localStorage。
 */
export function useLocalStoragePersistence<T>(storageKey: string, value: T): void {
  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    try {
      window.localStorage.setItem(storageKey, JSON.stringify(value));
    } catch {
      // 忽略写入失败，避免影响主流程（如隐私模式或配额不足）
    }
  }, [storageKey, value]);
}
