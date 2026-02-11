/**
 * 认证上下文
 *
 * 管理用户认证状态和令牌
 */
import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';
import { API_BASE } from '../config/api';

// ============ 类型定义 ============

export interface User {
  id: number;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  email_verified: boolean;
  created_at: string;
}

interface AuthContextType {
  /** 当前用户 */
  user: User | null;
  /** 是否正在加载 */
  isLoading: boolean;
  /** 是否已认证 */
  isAuthenticated: boolean;
  /** Access Token */
  accessToken: string | null;
  /** 登录 */
  login: (email: string, password: string) => Promise<void>;
  /** 注册 */
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  /** 登出 */
  logout: () => Promise<void>;
  /** 刷新令牌 */
  refreshToken: () => Promise<boolean>;
  /** 设置 token（用于 OAuth 回调） */
  setToken: (token: string) => void;
}

// ============ Context ============

const AuthContext = createContext<AuthContextType | null>(null);

// ============ API 函数 ============

async function apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    credentials: 'include', // 包含 cookies
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Request failed');
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// ============ Provider ============

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(() => {
    // 从 localStorage 恢复 token
    return localStorage.getItem('access_token');
  });
  const [isLoading, setIsLoading] = useState(true);

  // 获取用户信息
  const fetchUser = useCallback(async (token: string): Promise<User | null> => {
    try {
      const user = await apiRequest<User>('/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      });
      return user;
    } catch {
      return null;
    }
  }, []);

  // 初始化：检查现有 token
  useEffect(() => {
    const initAuth = async () => {
      // 检查 URL 中是否有 OAuth 回调的 token
      const urlParams = new URLSearchParams(window.location.search);
      const urlToken = urlParams.get('token');

      if (urlToken) {
        // 清除 URL 中的 token
        window.history.replaceState({}, '', window.location.pathname);
        setAccessToken(urlToken);
        localStorage.setItem('access_token', urlToken);

        const userData = await fetchUser(urlToken);
        if (userData) {
          setUser(userData);
        }
      } else if (accessToken) {
        const userData = await fetchUser(accessToken);
        if (userData) {
          setUser(userData);
        } else {
          // Token 无效，清除
          setAccessToken(null);
          localStorage.removeItem('access_token');
        }
      }

      setIsLoading(false);
    };

    initAuth();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 登录
  const login = useCallback(async (email: string, password: string) => {
    const response = await apiRequest<{ access_token: string; expires_in: number }>(
      '/auth/login',
      {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }
    );

    const token = response.access_token;
    setAccessToken(token);
    localStorage.setItem('access_token', token);

    const userData = await fetchUser(token);
    if (userData) {
      setUser(userData);
    }
  }, [fetchUser]);

  // 注册
  const register = useCallback(async (email: string, password: string, displayName?: string) => {
    await apiRequest<User>(
      '/auth/register',
      {
        method: 'POST',
        body: JSON.stringify({ email, password, display_name: displayName }),
      }
    );

    // 注册后自动登录
    await login(email, password);
  }, [login]);

  // 登出
  const logout = useCallback(async () => {
    try {
      await apiRequest('/auth/logout', {
        method: 'POST',
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      });
    } catch {
      // 忽略登出错误
    }

    setUser(null);
    setAccessToken(null);
    localStorage.removeItem('access_token');
  }, [accessToken]);

  // 刷新令牌
  const refreshTokenFn = useCallback(async (): Promise<boolean> => {
    try {
      // 从 cookie 获取 refresh_token（由浏览器自动发送）
      const response = await apiRequest<{ access_token: string; expires_in: number }>(
        '/auth/refresh',
        {
          method: 'POST',
          body: JSON.stringify({ refresh_token: '' }), // Cookie 中的 token
        }
      );

      const token = response.access_token;
      setAccessToken(token);
      localStorage.setItem('access_token', token);
      return true;
    } catch {
      setUser(null);
      setAccessToken(null);
      localStorage.removeItem('access_token');
      return false;
    }
  }, []);

  // 设置 token（用于 OAuth 回调）
  const setToken = useCallback((token: string) => {
    setAccessToken(token);
    localStorage.setItem('access_token', token);
    fetchUser(token).then(userData => {
      if (userData) {
        setUser(userData);
      }
    });
  }, [fetchUser]);

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user,
    accessToken,
    login,
    register,
    logout,
    refreshToken: refreshTokenFn,
    setToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// ============ Hook ============

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
