import React, { useRef, useState, useEffect } from 'react';
import StockCard from './StockCard';
import StockCardSkeleton from './StockCardSkeleton';
import type * as T from '../src/types/schema';
import type { AnalysisOptions } from '../services/api';

interface LazyStockCardProps {
  stock: T.AssetPrice;
  priceData?: T.StockPrice;
  analysis?: T.AgentAnalysis;
  onRefresh: (symbol: string, name: string, options?: AnalysisOptions) => void;
  isAnalyzing: boolean;
  currentStage?: string;
  onDelete: (symbol: string) => void;
  onClick: (stock: T.AssetPrice) => void;
}

/**
 * 惰性渲染的 StockCard 包装器
 *
 * 使用 IntersectionObserver 检测可见性：
 * - 视口外（超过 200px margin）：渲染轻量骨架屏
 * - 视口内或接近视口：渲染完整 StockCard
 * - 一旦渲染完整卡片后不再降级（保持组件状态）
 */
const LazyStockCard: React.FC<LazyStockCardProps> = (props) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hasBeenVisible, setHasBeenVisible] = useState(false);

  useEffect(() => {
    // 已可见过，无需继续观察
    if (hasBeenVisible) return;

    const el = containerRef.current;
    if (!el) return;

    // rootMargin 200px：提前 200px 开始渲染（预加载）
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setHasBeenVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: '200px' }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [hasBeenVisible]);

  // 正在分析中的卡片始终完整渲染（需要展示实时进度）
  if (hasBeenVisible || props.isAnalyzing) {
    return (
      <StockCard
        stock={props.stock}
        priceData={props.priceData}
        analysis={props.analysis}
        onRefresh={props.onRefresh}
        isAnalyzing={props.isAnalyzing}
        currentStage={props.currentStage}
        onDelete={props.onDelete}
        onClick={props.onClick}
      />
    );
  }

  // 尚未进入视口，渲染骨架屏占位
  return (
    <div ref={containerRef}>
      <StockCardSkeleton />
    </div>
  );
};

export default LazyStockCard;
