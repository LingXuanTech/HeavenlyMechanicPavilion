/**
 * A 股特有功能 Hooks - 北向资金、龙虎榜、限售解禁
 *
 * 基于 TanStack Query
 */

import { useQuery } from '@tanstack/react-query';
import {
  getNorthMoneyFlow,
  getNorthMoneySummary,
  getNorthMoneyHistory,
  getNorthMoneyHolding,
  getNorthMoneyTopBuys,
  getNorthMoneyTopSells,
  getLHBDaily,
  getLHBSummary,
  getLHBHotMoneyActivity,
  getLHBTopBuys,
  getLHBTopSells,
  getLHBInstitutionActivity,
  getLHBHotMoneyStocks,
  getJiejinUpcoming,
  getJiejinCalendar,
  getJiejinSummary,
  getJiejinHighPressure,
  getJiejinToday,
  getJiejinWeek,
  getJiejinWarning,
} from '../services/api';

// ============ Query Keys ============

export const NORTH_MONEY_KEY = 'north-money';
export const LHB_KEY = 'lhb';
export const JIEJIN_KEY = 'jiejin';

// ============ 北向资金 Hooks ============

/**
 * 获取北向资金流向
 */
export function useNorthMoneyFlow() {
  return useQuery({
    queryKey: [NORTH_MONEY_KEY, 'flow'],
    queryFn: getNorthMoneyFlow,
    staleTime: 60 * 1000, // 1 分钟
  });
}

/**
 * 获取北向资金概览
 */
export function useNorthMoneySummary() {
  return useQuery({
    queryKey: [NORTH_MONEY_KEY, 'summary'],
    queryFn: getNorthMoneySummary,
    staleTime: 60 * 1000,
  });
}

/**
 * 获取北向资金历史
 */
export function useNorthMoneyHistory(days: number = 30) {
  return useQuery({
    queryKey: [NORTH_MONEY_KEY, 'history', days],
    queryFn: () => getNorthMoneyHistory(days),
    staleTime: 5 * 60 * 1000, // 5 分钟
  });
}

/**
 * 获取个股北向持仓
 */
export function useNorthMoneyHolding(symbol: string) {
  return useQuery({
    queryKey: [NORTH_MONEY_KEY, 'holding', symbol],
    queryFn: () => getNorthMoneyHolding(symbol),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * 获取北向资金净买入 TOP
 */
export function useNorthMoneyTopBuys(limit: number = 20) {
  return useQuery({
    queryKey: [NORTH_MONEY_KEY, 'top-buys', limit],
    queryFn: () => getNorthMoneyTopBuys(limit),
    staleTime: 60 * 1000,
  });
}

/**
 * 获取北向资金净卖出 TOP
 */
export function useNorthMoneyTopSells(limit: number = 20) {
  return useQuery({
    queryKey: [NORTH_MONEY_KEY, 'top-sells', limit],
    queryFn: () => getNorthMoneyTopSells(limit),
    staleTime: 60 * 1000,
  });
}

// ============ 龙虎榜 Hooks ============

/**
 * 获取每日龙虎榜
 */
export function useLHBDaily(tradeDate?: string) {
  return useQuery({
    queryKey: [LHB_KEY, 'daily', tradeDate],
    queryFn: () => getLHBDaily(tradeDate),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * 获取龙虎榜概览
 */
export function useLHBSummary() {
  return useQuery({
    queryKey: [LHB_KEY, 'summary'],
    queryFn: getLHBSummary,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * 获取知名游资活动
 */
export function useLHBHotMoney(days: number = 5) {
  return useQuery({
    queryKey: [LHB_KEY, 'hot-money', days],
    queryFn: () => getLHBHotMoneyActivity(days),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * 获取龙虎榜净买入 TOP
 */
export function useLHBTopBuys(limit: number = 10) {
  return useQuery({
    queryKey: [LHB_KEY, 'top-buys', limit],
    queryFn: () => getLHBTopBuys(limit),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * 获取龙虎榜净卖出 TOP
 */
export function useLHBTopSells(limit: number = 10) {
  return useQuery({
    queryKey: [LHB_KEY, 'top-sells', limit],
    queryFn: () => getLHBTopSells(limit),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * 获取机构动向
 */
export function useLHBInstitution(direction: 'buy' | 'sell' | 'all' = 'all') {
  return useQuery({
    queryKey: [LHB_KEY, 'institution', direction],
    queryFn: () => getLHBInstitutionActivity(direction),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * 获取有游资参与的股票
 */
export function useLHBHotMoneyStocks() {
  return useQuery({
    queryKey: [LHB_KEY, 'hot-money-stocks'],
    queryFn: getLHBHotMoneyStocks,
    staleTime: 5 * 60 * 1000,
  });
}

// ============ 限售解禁 Hooks ============

/**
 * 获取近期解禁股票
 */
export function useJiejinUpcoming(days: number = 30) {
  return useQuery({
    queryKey: [JIEJIN_KEY, 'upcoming', days],
    queryFn: () => getJiejinUpcoming(days),
    staleTime: 30 * 60 * 1000, // 30 分钟
  });
}

/**
 * 获取解禁日历
 */
export function useJiejinCalendar(days: number = 30) {
  return useQuery({
    queryKey: [JIEJIN_KEY, 'calendar', days],
    queryFn: () => getJiejinCalendar(days),
    staleTime: 30 * 60 * 1000,
  });
}

/**
 * 获取解禁概览
 */
export function useJiejinSummary(days: number = 30) {
  return useQuery({
    queryKey: [JIEJIN_KEY, 'summary', days],
    queryFn: () => getJiejinSummary(days),
    staleTime: 30 * 60 * 1000,
  });
}

/**
 * 获取高解禁压力股票
 */
export function useJiejinHighPressure(days: number = 7) {
  return useQuery({
    queryKey: [JIEJIN_KEY, 'high-pressure', days],
    queryFn: () => getJiejinHighPressure(days),
    staleTime: 30 * 60 * 1000,
  });
}

/**
 * 获取今日解禁
 */
export function useJiejinToday() {
  return useQuery({
    queryKey: [JIEJIN_KEY, 'today'],
    queryFn: getJiejinToday,
    staleTime: 30 * 60 * 1000,
  });
}

/**
 * 获取本周解禁
 */
export function useJiejinWeek() {
  return useQuery({
    queryKey: [JIEJIN_KEY, 'week'],
    queryFn: getJiejinWeek,
    staleTime: 30 * 60 * 1000,
  });
}

/**
 * 获取个股解禁预警
 */
export function useJiejinWarning(symbol: string, days: number = 30) {
  return useQuery({
    queryKey: [JIEJIN_KEY, 'warning', symbol, days],
    queryFn: () => getJiejinWarning(symbol, days),
    enabled: !!symbol,
    staleTime: 30 * 60 * 1000,
  });
}
