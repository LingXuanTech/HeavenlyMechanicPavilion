/**
 * ErrorBoundary - 全局错误边界组件
 *
 * 捕获子组件树中的 JavaScript 错误，防止整个应用崩溃。
 * 展示友好的错误回退界面。
 */
import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** 可选的自定义回退 UI */
  fallback?: ReactNode;
  /** 错误发生时的回调 */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });
    console.error('[ErrorBoundary] Caught error:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  handleReload = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex items-center justify-center min-h-screen bg-surface text-stone-50 p-8">
          <div className="max-w-md w-full bg-surface-raised border border-border rounded-xl p-8 text-center">
            <div className="flex justify-center mb-4">
              <AlertTriangle className="w-12 h-12 text-amber-500" />
            </div>
            <h2 className="text-xl font-semibold mb-2">页面出现错误</h2>
            <p className="text-stone-400 mb-6 text-sm">
              {this.state.error?.message || '发生了未知错误'}
            </p>

            <div className="flex gap-3 justify-center">
              <button
                onClick={this.handleReset}
                className="px-4 py-2 bg-surface-overlay hover:bg-stone-700 rounded-lg text-sm transition-colors"
              >
                重试
              </button>
              <button
                onClick={this.handleReload}
                className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover rounded-lg text-sm transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                刷新页面
              </button>
            </div>

            {/* 开发模式显示错误详情 */}
            {import.meta.env.DEV && this.state.errorInfo && (
              <details className="mt-6 text-left">
                <summary className="text-stone-500 text-xs cursor-pointer hover:text-stone-400">
                  错误详情（开发模式）
                </summary>
                <pre className="mt-2 p-3 bg-surface rounded text-xs text-red-400 overflow-auto max-h-48">
                  {this.state.error?.stack}
                  {'\n\n'}
                  {this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
