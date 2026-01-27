import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';

// 创建 QueryClient 实例，配置全局默认值
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 全局默认配置
      staleTime: 60 * 1000, // 1分钟内认为数据新鲜
      gcTime: 10 * 60 * 1000, // 10分钟后清理未使用的缓存
      retry: 2, // 失败后重试2次
      refetchOnWindowFocus: false, // 窗口聚焦时不自动刷新
    },
    mutations: {
      retry: 1,
    },
  },
});

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error("Could not find root element to mount to");
}

const root = ReactDOM.createRoot(rootElement);
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);
