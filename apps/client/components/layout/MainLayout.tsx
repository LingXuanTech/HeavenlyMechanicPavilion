/**
 * 主布局组件
 *
 * 包含侧边栏和主内容区域，所有认证后的页面共享此布局
 * 使用 AnimatePresence 支持页面退出动画
 */
import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import Sidebar from '../Sidebar';
import PageTransition from './PageTransition';

const MainLayout: React.FC = () => {
  const location = useLocation();

  return (
    <div className="flex h-screen bg-surface text-stone-50 overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <AnimatePresence mode="wait">
          <PageTransition key={location.pathname}>
            <Outlet />
          </PageTransition>
        </AnimatePresence>
      </div>
    </div>
  );
};

export default MainLayout;
