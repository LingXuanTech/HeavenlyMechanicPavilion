import React from 'react';

/**
 * StockCard 骨架屏组件
 * 用于在数据加载时提供更好的用户体验
 */
const StockCardSkeleton: React.FC = () => {
  return (
    <div className="bg-surface-raised border border-border rounded-lg p-4 flex flex-col gap-4 animate-pulse">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center gap-2">
            <div className="h-6 w-20 bg-surface-overlay rounded" />
            <div className="h-4 w-8 bg-surface-overlay rounded" />
          </div>
          <div className="h-3 w-24 bg-surface-overlay rounded mt-1" />
        </div>
        <div className="text-right">
          <div className="h-6 w-16 bg-surface-overlay rounded" />
          <div className="h-4 w-12 bg-surface-overlay rounded mt-1" />
        </div>
      </div>

      {/* Chart placeholder */}
      <div className="h-16 bg-surface-overlay/50 rounded" />

      {/* Analysis section */}
      <div className="flex-1 bg-surface/50 rounded p-3 border border-border/50 flex flex-col gap-3">
        <div className="flex justify-between items-center">
          <div className="h-3 w-20 bg-surface-overlay rounded" />
          <div className="h-3 w-16 bg-surface-overlay rounded" />
        </div>

        {/* Signal area */}
        <div className="h-10 bg-surface-overlay/50 rounded" />

        {/* Grid */}
        <div className="grid grid-cols-2 gap-2">
          <div className="flex flex-col gap-1">
            <div className="h-3 w-16 bg-surface-overlay rounded" />
            <div className="h-4 w-12 bg-surface-overlay rounded" />
          </div>
          <div className="flex flex-col gap-1 items-end">
            <div className="h-3 w-16 bg-surface-overlay rounded" />
            <div className="h-4 w-12 bg-surface-overlay rounded" />
          </div>
        </div>

        {/* Entry zone */}
        <div className="h-12 bg-surface-overlay/30 rounded" />

        {/* Indicators */}
        <div className="pt-2 border-t border-border">
          <div className="flex gap-2 items-center mb-2">
            <div className="h-3 w-16 bg-surface-overlay rounded" />
            <div className="h-4 w-12 bg-surface-overlay rounded" />
            <div className="h-4 w-12 bg-surface-overlay rounded" />
          </div>
          <div className="h-3 w-full bg-surface-overlay/50 rounded" />
          <div className="h-3 w-3/4 bg-surface-overlay/50 rounded mt-1" />
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2 mt-auto pt-2">
        <div className="flex-1 h-8 bg-surface-overlay rounded" />
        <div className="w-8 h-8 bg-surface-overlay rounded" />
      </div>
    </div>
  );
};

export default StockCardSkeleton;
