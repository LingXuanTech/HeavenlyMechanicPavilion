import React, { Suspense, lazy } from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ErrorBoundary from './components/ErrorBoundary';
import { ToastProvider } from './components/Toast';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/auth/ProtectedRoute';
import MainLayout from './components/layout/MainLayout';
import LoadingFallback from './components/layout/LoadingFallback';

// 懒加载页面组件
const LoginPage = lazy(() => import('./pages/LoginPage'));
const RegisterPage = lazy(() => import('./pages/RegisterPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const NewsPage = lazy(() => import('./pages/NewsPage'));
const ChinaMarketPage = lazy(() => import('./pages/ChinaMarketPage'));
const MacroPage = lazy(() => import('./pages/MacroPage'));
const PortfolioPage = lazy(() => import('./pages/PortfolioPage'));
const PromptsPage = lazy(() => import('./pages/PromptsPage'));
const SchedulerPage = lazy(() => import('./pages/SchedulerPage'));
const AIConfigPage = lazy(() => import('./pages/AIConfigPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'));

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
    <ErrorBoundary>
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <ToastProvider>
              <Suspense fallback={<LoadingFallback />}>
                <Routes>
                  {/* 公开路由 */}
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/register" element={<RegisterPage />} />

                  {/* 受保护路由 - 使用 MainLayout */}
                  <Route
                    element={
                      <ProtectedRoute>
                        <MainLayout />
                      </ProtectedRoute>
                    }
                  >
                    <Route index element={<DashboardPage />} />
                    <Route path="news" element={<NewsPage />} />
                    <Route path="china-market" element={<ChinaMarketPage />} />
                    <Route path="macro" element={<MacroPage />} />
                    <Route path="portfolio" element={<PortfolioPage />} />
                    <Route path="prompts" element={<PromptsPage />} />
                    <Route path="scheduler" element={<SchedulerPage />} />
                    <Route path="ai-config" element={<AIConfigPage />} />
                    <Route path="settings" element={<SettingsPage />} />
                    {/* 404 页面 - 放在 MainLayout 内以保持侧边栏 */}
                    <Route path="*" element={<NotFoundPage />} />
                  </Route>

                  {/* 未认证状态的 404 */}
                  <Route path="*" element={<NotFoundPage />} />
                </Routes>
              </Suspense>
            </ToastProvider>
          </AuthProvider>
        </QueryClientProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>
);
