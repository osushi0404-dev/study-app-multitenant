import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import { toast } from 'react-hot-toast';
import { userActionLogger } from '../utils/userActionLogger';

export class ApiClient {
  private instance: AxiosInstance;
  private refreshingToken = false;
  private refreshPromise: Promise<string> | null = null;

  constructor(instance?: AxiosInstance) {
    this.instance =
      instance ??
      axios.create({
        baseURL: process.env.REACT_APP_API_BASE_URL ?? '',
        timeout: parseInt(process.env.REACT_APP_API_TIMEOUT || '10000'),
        headers: {
          'Content-Type': 'application/json',
        },
      });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor to add auth token
    this.instance.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('accessToken');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }

        // ユーザー操作履歴をヘッダーに追加
        const recentActions = userActionLogger.getActionsForAPI();
        config.headers['X-User-Actions'] = recentActions;

        // 削除: キャッシュ制御はサーバー側（Django）のレスポンスヘッダーで管理
        // Reactコンポーネントの再マウント時に自動的にAPIを再呼び出しするため、
        // クライアント側でのキャッシュ制御ヘッダー送信は不要

        // Log requests in development
        if (process.env.REACT_APP_ENABLE_API_LOGGING === 'true') {
          console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`, {
            data: config.data,
            params: config.params,
          });
        }

        return config;
      },
      (error) => {
        console.error('Request interceptor error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling and token refresh
    this.instance.interceptors.response.use(
      (response: AxiosResponse) => {
        // Log responses in development
        if (process.env.REACT_APP_ENABLE_API_LOGGING === 'true') {
          console.log(`✅ API Response: ${response.config.method?.toUpperCase()} ${response.config.url}`, {
            status: response.status,
            data: response.data,
          });
        }

        return response;
      },
      async (error: AxiosError) => {
        const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

        // Log errors in development
        if (process.env.REACT_APP_ENABLE_API_LOGGING === 'true') {
          console.error(`❌ API Error: ${originalRequest?.method?.toUpperCase()} ${originalRequest?.url}`, {
            status: error.response?.status,
            data: error.response?.data,
          });
        }

        // Handle 401 errors (token expired)
        if (error.response?.status === 401 && !originalRequest._retry) {
          if (this.refreshingToken) {
            // If already refreshing, wait for the promise
            try {
              const newToken = await this.refreshPromise;
              if (newToken && originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${newToken}`;
                return this.instance(originalRequest);
              }
            } catch (refreshError) {
              return Promise.reject(refreshError);
            }
          }

          originalRequest._retry = true;
          this.refreshingToken = true;

          try {
            const refreshToken = localStorage.getItem('refreshToken');
            if (!refreshToken) {
              throw new Error('No refresh token available');
            }

            this.refreshPromise = this.refreshAccessToken(refreshToken);
            const newToken = await this.refreshPromise;

            // Update the authorization header
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
            }

            return this.instance(originalRequest);
          } catch (refreshError) {
            // Refresh failed, redirect to login
            this.handleAuthFailure();
            return Promise.reject(refreshError);
          } finally {
            this.refreshingToken = false;
            this.refreshPromise = null;
          }
        }

        // Handle other errors
        this.handleApiError(error);
        return Promise.reject(error);
      }
    );
  }

  private async refreshAccessToken(refreshToken: string): Promise<string> {
    try {
      const response = await axios.post(
        `${process.env.REACT_APP_API_BASE_URL ?? ''}/api/auth/token/refresh/`,
        { refresh: refreshToken },
        {
          headers: { 'Content-Type': 'application/json' },
          timeout: parseInt(process.env.REACT_APP_API_TIMEOUT || '10000'),
        }
      );

      const { access } = response.data;
      localStorage.setItem('accessToken', access);
      return access;
    } catch (error) {
      console.error('Token refresh failed:', error);
      throw error;
    }
  }

  private handleAuthFailure() {
    // Clear tokens
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');

    // Only show error and redirect if not already on login page
    if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/register')) {
      // Show error message
      toast.error('セッションが期限切れです。再度ログインしてください。');

      // Redirect to login (you might want to use React Router for this)
      window.location.href = '/login';
    }
  }

  private handleApiError(error: AxiosError) {
    const status = error.response?.status;

    // Don't show error for auth endpoints (handled by auth context)
    if (error.config?.url?.includes('/auth/')) {
      return;
    }

    // 400 (validation/business errors) are handled by the calling component
    if (status === 400) return;

    // Handle common error cases
    switch (status) {
      case 403:
        toast.error('この操作を実行する権限がありません');
        break;
      case 404:
        toast.error('要求されたリソースが見つかりません');
        break;
      case 429:
        toast.error('リクエストが多すぎます。しばらく待ってから再試行してください');
        break;
      case 500:
        toast.error('サーバーエラーが発生しました');
        break;
      case 502:
      case 503:
      case 504:
        toast.error('サーバーが一時的に利用できません');
        break;
      default:
        if (error.code === 'ECONNABORTED') {
          toast.error('リクエストがタイムアウトしました');
        } else if (error.message === 'Network Error') {
          toast.error('ネットワークエラーが発生しました');
        } else {
          toast.error('予期しないエラーが発生しました');
        }
    }
  }

  // Public methods
  public get<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.instance.get<T>(url, config);
  }

  public post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.instance.post<T>(url, data, config);
  }

  public put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.instance.put<T>(url, data, config);
  }

  public patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.instance.patch<T>(url, data, config);
  }

  public delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.instance.delete<T>(url, config);
  }

  public setAuthToken(token: string) {
    this.instance.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }

  public removeAuthToken() {
    delete this.instance.defaults.headers.common['Authorization'];
  }
}

// Create and export a singleton instance
export const apiClient = new ApiClient();
export default apiClient;
