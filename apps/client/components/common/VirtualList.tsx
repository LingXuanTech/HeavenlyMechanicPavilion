/**
 * 通用虚拟滚动列表组件
 *
 * 基于 @tanstack/react-virtual，适用于长列表场景（龙虎榜、北向资金持仓等）。
 * 仅渲染可视区域内的元素，大幅降低 DOM 节点数量。
 */
import React, { useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';

interface VirtualListProps<T> {
  /** 数据列表 */
  items: T[];
  /** 预估每行高度 (px) */
  estimateSize: number;
  /** 渲染单行的函数 */
  renderItem: (item: T, index: number) => React.ReactNode;
  /** 容器最大高度 (px)，默认 400 */
  maxHeight?: number;
  /** 额外的容器 className */
  className?: string;
  /** 过扫描行数（上下各多渲染几行，减少滚动白屏），默认 5 */
  overscan?: number;
  /** 空列表占位 */
  emptyText?: string;
  /** 为 true 时使用 height: 100% 替代 maxHeight，适配 flex 布局容器 */
  fillHeight?: boolean;
}

function VirtualList<T>({
  items,
  estimateSize,
  renderItem,
  maxHeight = 400,
  className = '',
  overscan = 5,
  emptyText = '暂无数据',
  fillHeight = false,
}: VirtualListProps<T>) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => estimateSize,
    overscan,
  });

  if (items.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-stone-500 text-sm">
        {emptyText}
      </div>
    );
  }

  return (
    <div
      ref={parentRef}
      className={`overflow-y-auto custom-scrollbar ${className}`}
      style={fillHeight ? { height: '100%' } : { maxHeight }}
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualItem) => (
          <div
            key={virtualItem.key}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualItem.size}px`,
              transform: `translateY(${virtualItem.start}px)`,
            }}
          >
            {renderItem(items[virtualItem.index], virtualItem.index)}
          </div>
        ))}
      </div>
    </div>
  );
}

export default VirtualList;
