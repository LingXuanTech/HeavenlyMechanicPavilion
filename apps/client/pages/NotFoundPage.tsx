/**
 * 404 页面
 *
 * 未找到页面时显示
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Home, ArrowLeft, Search } from 'lucide-react';

const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center h-full bg-surface text-white p-8">
      {/* 404 动画图形 */}
      <div className="relative mb-8">
        <div className="text-[180px] font-bold text-surface-overlay leading-none select-none">
          404
        </div>
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-32 h-32 rounded-full bg-gradient-to-br from-amber-500/20 to-purple-500/20 backdrop-blur-sm border border-border-strong flex items-center justify-center">
            <Search className="w-12 h-12 text-stone-500" />
          </div>
        </div>
      </div>

      {/* 文字内容 */}
      <h1 className="text-2xl font-bold text-white mb-2">页面未找到</h1>
      <p className="text-stone-400 text-center max-w-md mb-8">
        抱歉，您访问的页面不存在或已被移动。请检查 URL 是否正确，或返回首页。
      </p>

      {/* 操作按钮 */}
      <div className="flex gap-4">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 px-4 py-2 bg-surface-overlay hover:bg-surface-muted text-stone-300 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          返回上页
        </button>
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors"
        >
          <Home className="w-4 h-4" />
          回到首页
        </button>
      </div>

      {/* 装饰性背景 */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-amber-500/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/5 rounded-full blur-3xl" />
      </div>
    </div>
  );
};

export default NotFoundPage;
