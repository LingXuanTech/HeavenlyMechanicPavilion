/**
 * 懒加载 Loading 占位组件
 *
 * 在页面懒加载时显示
 */
import React from 'react';
import { Loader2 } from 'lucide-react';

const LoadingFallback: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center h-full bg-gray-950">
      <div className="relative">
        {/* 外圈动画 */}
        <div className="w-16 h-16 border-4 border-gray-800 border-t-blue-500 rounded-full animate-spin" />
        {/* 内圈 */}
        <div className="absolute inset-0 flex items-center justify-center">
          <Loader2 className="w-6 h-6 text-blue-400 animate-pulse" />
        </div>
      </div>
      <p className="mt-4 text-sm text-gray-500">加载中...</p>
    </div>
  );
};

export default LoadingFallback;
