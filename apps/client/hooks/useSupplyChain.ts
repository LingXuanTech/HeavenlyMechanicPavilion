/**
 * 产业链知识图谱 Hooks
 */

import { useQuery } from '@tanstack/react-query';
import { API_BASE } from '../services/api';
import type * as T from '../src/types/schema';

// ============ Query Keys ============

export const supplyChainKeys = {
  all: ['supply-chain'] as const,
  chains: () => [...supplyChainKeys.all, 'chains'] as const,
  graph: (chainId: string) => [...supplyChainKeys.all, 'graph', chainId] as const,
  stock: (symbol: string) => [...supplyChainKeys.all, 'stock', symbol] as const,
  impact: (symbol: string) => [...supplyChainKeys.all, 'impact', symbol] as const,
};

// ============ Re-export Types ============
export type {
  ChainSummary,
  ChainListResponse,
  GraphNode,
  GraphEdge,
  ChainGraphResponse,
  ChainPosition,
  StockChainPositionResponse,
  SupplyChainImpact,
  SupplyChainImpactResponse,
} from '../src/types/schema';

// ============ Fetch ============

async function fetchJSON<R>(endpoint: string): Promise<R> {
  const response = await fetch(`${API_BASE}${endpoint}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

// ============ Hooks ============

/**
 * 获取所有产业链列表
 */
export function useChainList() {
  return useQuery({
    queryKey: supplyChainKeys.chains(),
    queryFn: () => fetchJSON<T.ChainListResponse>('/supply-chain/chains'),
    staleTime: 60 * 60 * 1000, // 1 小时
  });
}

/**
 * 获取产业链图谱数据
 */
export function useChainGraph(chainId: string) {
  return useQuery({
    queryKey: supplyChainKeys.graph(chainId),
    queryFn: () => fetchJSON<T.ChainGraphResponse>(`/supply-chain/graph/${chainId}`),
    enabled: !!chainId,
    staleTime: 60 * 60 * 1000,
  });
}

/**
 * 获取个股产业链位置
 */
export function useStockChainPosition(symbol: string) {
  return useQuery({
    queryKey: supplyChainKeys.stock(symbol),
    queryFn: () =>
      fetchJSON<T.StockChainPositionResponse>(
        `/supply-chain/stock/${encodeURIComponent(symbol)}`
      ),
    enabled: !!symbol,
    staleTime: 60 * 60 * 1000,
  });
}

/**
 * 获取产业链传导效应分析
 */
export function useSupplyChainImpact(symbol: string) {
  return useQuery({
    queryKey: supplyChainKeys.impact(symbol),
    queryFn: () =>
      fetchJSON<T.SupplyChainImpactResponse>(
        `/supply-chain/impact/${encodeURIComponent(symbol)}`
      ),
    enabled: !!symbol,
    staleTime: 30 * 60 * 1000,
  });
}
