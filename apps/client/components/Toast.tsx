/**
 * Toast 通知系统
 *
 * 轻量级 toast 通知，支持 success/error/warning/info 类型。
 * 使用 React Context 提供全局访问。
 */
import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { X, CheckCircle, AlertTriangle, AlertCircle, Info } from 'lucide-react';

// =============================================================================
// 类型定义
// =============================================================================

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface Toast {
  id: string;
  type: ToastType;
  message: string;
  /** 自动消失时间（毫秒），0 表示不自动消失 */
  duration: number;
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (type: ToastType, message: string, duration?: number) => void;
  removeToast: (id: string) => void;
  success: (message: string, duration?: number) => void;
  error: (message: string, duration?: number) => void;
  warning: (message: string, duration?: number) => void;
  info: (message: string, duration?: number) => void;
}

// =============================================================================
// Context
// =============================================================================

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return ctx;
}

// =============================================================================
// Toast 图标和样式映射
// =============================================================================

const TOAST_CONFIG: Record<ToastType, {
  icon: typeof CheckCircle;
  bgClass: string;
  borderClass: string;
  iconClass: string;
}> = {
  success: {
    icon: CheckCircle,
    bgClass: 'bg-emerald-950/90',
    borderClass: 'border-emerald-700/50',
    iconClass: 'text-emerald-400',
  },
  error: {
    icon: AlertCircle,
    bgClass: 'bg-red-950/90',
    borderClass: 'border-red-700/50',
    iconClass: 'text-red-400',
  },
  warning: {
    icon: AlertTriangle,
    bgClass: 'bg-amber-950/90',
    borderClass: 'border-amber-700/50',
    iconClass: 'text-amber-400',
  },
  info: {
    icon: Info,
    bgClass: 'bg-blue-950/90',
    borderClass: 'border-blue-700/50',
    iconClass: 'text-blue-400',
  },
};

const DEFAULT_DURATIONS: Record<ToastType, number> = {
  success: 3000,
  error: 6000,
  warning: 5000,
  info: 4000,
};

// =============================================================================
// Provider
// =============================================================================

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (type: ToastType, message: string, duration?: number) => {
      const id = `toast_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
      const finalDuration = duration ?? DEFAULT_DURATIONS[type];

      setToasts((prev) => [...prev, { id, type, message, duration: finalDuration }]);

      if (finalDuration > 0) {
        setTimeout(() => removeToast(id), finalDuration);
      }
    },
    [removeToast]
  );

  const contextValue: ToastContextValue = {
    toasts,
    addToast,
    removeToast,
    success: useCallback((msg, dur) => addToast('success', msg, dur), [addToast]),
    error: useCallback((msg, dur) => addToast('error', msg, dur), [addToast]),
    warning: useCallback((msg, dur) => addToast('warning', msg, dur), [addToast]),
    info: useCallback((msg, dur) => addToast('info', msg, dur), [addToast]),
  };

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
}

// =============================================================================
// Toast 容器 + 单个 Toast
// =============================================================================

function ToastContainer({
  toasts,
  onRemove,
}: {
  toasts: Toast[];
  onRemove: (id: string) => void;
}) {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onRemove={onRemove} />
      ))}
    </div>
  );
}

function ToastItem({ toast, onRemove }: { toast: Toast; onRemove: (id: string) => void }) {
  const config = TOAST_CONFIG[toast.type];
  const Icon = config.icon;

  return (
    <div
      className={`
        pointer-events-auto flex items-start gap-3 p-3 rounded-lg border backdrop-blur-sm
        ${config.bgClass} ${config.borderClass}
        animate-[slideIn_0.2s_ease-out]
        shadow-lg shadow-black/30
      `}
      role="alert"
    >
      <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${config.iconClass}`} />
      <p className="text-sm text-stone-200 flex-1">{toast.message}</p>
      <button
        onClick={() => onRemove(toast.id)}
        className="text-stone-500 hover:text-stone-300 transition-colors flex-shrink-0"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

export default ToastProvider;
