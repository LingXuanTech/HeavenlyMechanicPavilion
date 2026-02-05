/**
 * AI Market Scout Hook
 *
 * 提供 AI 驱动的股票发现功能
 */
import { useState, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { discoverStocks } from '../services/api';
import type * as T from '../src/types/schema';

export const SCOUT_KEY = ['scout'];

export interface UseScoutReturn {
  // 状态
  query: string;
  results: T.MarketOpportunity[];
  isLoading: boolean;
  error: Error | null;
  isOpen: boolean;

  // 操作
  setQuery: (query: string) => void;
  scout: () => Promise<void>;
  reset: () => void;
  toggle: () => void;
  open: () => void;
  close: () => void;
}

/**
 * AI Market Scout Hook
 *
 * 使用方法:
 * ```tsx
 * const { query, setQuery, results, isLoading, scout, isOpen, toggle } = useScout();
 * ```
 */
export function useScout(): UseScoutReturn {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<T.MarketOpportunity[]>([]);
  const [isOpen, setIsOpen] = useState(false);

  const mutation = useMutation({
    mutationFn: (searchQuery: string) => discoverStocks(searchQuery),
    onSuccess: (data) => {
      setResults(data);
    },
  });

  const scout = useCallback(async () => {
    if (!query.trim()) return;
    setResults([]); // 清空旧结果
    await mutation.mutateAsync(query);
  }, [query, mutation]);

  const reset = useCallback(() => {
    setQuery('');
    setResults([]);
    mutation.reset();
  }, [mutation]);

  const toggle = useCallback(() => {
    setIsOpen(prev => !prev);
  }, []);

  const open = useCallback(() => {
    setIsOpen(true);
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
    reset();
  }, [reset]);

  return {
    query,
    results,
    isLoading: mutation.isPending,
    error: mutation.error,
    isOpen,
    setQuery,
    scout,
    reset,
    toggle,
    open,
    close,
  };
}
