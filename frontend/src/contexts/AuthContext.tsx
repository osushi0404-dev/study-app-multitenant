import React, { createContext, useContext, useState, useEffect, ReactNode, useRef } from 'react';
import authService from '../services/auth.service';
import apiClient from '../services/api';
import { User } from '../services/types';
import { toast } from 'react-hot-toast';
import { showErrorToast, showSuccessToast } from '../components/ErrorToast';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, userId: string, password: string, firstName?: string, lastName?: string, organizationSlug?: string, subjectIds?: number[]) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  verifyEmail: (token: string) => Promise<void>;
  resendEmailVerification: (email: string) => Promise<void>;
  requestPasswordReset: (email: string) => Promise<void>;
  confirmPasswordReset: (token: string, newPassword: string) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  updateProfile: (userData: Partial<User>) => Promise<void>;
  extendSession: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Auto-logout functionality
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const warningTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const warningShownRef = useRef(false);
  const TIMEOUT_MINUTES = 30;
  const WARNING_MINUTES = 5;

  // Initialize auth state on app load
  useEffect(() => {
    const initializeAuth = async () => {
      setLoading(true);
      
      // Check if user data is stored
      const storedUser = authService.getStoredUser();
      const accessToken = authService.getAccessToken();
      
      if (storedUser && accessToken) {
        setUser(storedUser);
        apiClient.setAuthToken(accessToken);
        
        // Verify token is still valid by fetching current user
        try {
          const currentUser = await authService.getCurrentUser();
          setUser(currentUser);
          localStorage.setItem('user', JSON.stringify(currentUser));
        } catch (error) {
          console.error('Token validation failed:', error);
          // Silent logout without showing error message
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          localStorage.removeItem('user');
          setUser(null);
          apiClient.removeAuthToken();
        }
      }
      
      setLoading(false);
    };

    initializeAuth();
  }, []);

  const handleLogout = async () => {
    // Clear auto-logout timers
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    if (warningTimeoutRef.current) {
      clearTimeout(warningTimeoutRef.current);
    }
    
    await authService.logout();
    setUser(null);
    apiClient.removeAuthToken();
  };

  const resetAutoLogoutTimer = () => {
    // Clear existing timers
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    if (warningTimeoutRef.current) {
      clearTimeout(warningTimeoutRef.current);
    }

    // Reset warning flag
    warningShownRef.current = false;

    if (!user) return;

    const timeoutMs = TIMEOUT_MINUTES * 60 * 1000;
    const warningMs = (TIMEOUT_MINUTES - WARNING_MINUTES) * 60 * 1000;

    // Set warning timer
    warningTimeoutRef.current = setTimeout(() => {
      if (!warningShownRef.current && user) {
        warningShownRef.current = true;
        toast((t) => (
          <div>
            <strong>セッション期限警告</strong>
            <br />
            {WARNING_MINUTES}分後に自動ログアウトします
            <br />
            <button
              onClick={() => {
                toast.dismiss(t.id);
                resetAutoLogoutTimer();
              }}
              style={{
                marginTop: '8px',
                padding: '4px 8px',
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              セッション延長
            </button>
          </div>
        ), {
          duration: WARNING_MINUTES * 60 * 1000,
          icon: '⚠️',
        });
      }
    }, warningMs);

    // Set logout timer
    timeoutRef.current = setTimeout(async () => {
      if (user) {
        showErrorToast({ response: { data: { error: { main_message: 'セッションタイムアウト', sub_message: '再度ログインしてください' } } } });
        await handleLogout();
      }
    }, timeoutMs);
  };

  const extendSession = () => {
    resetAutoLogoutTimer();
    showSuccessToast('セッションを延長しました');
  };

  const login = async (email: string, password: string) => {
    try {
      const loginResponse = await authService.login({ email, password });
      
      localStorage.setItem('accessToken', loginResponse.access);
      localStorage.setItem('refreshToken', loginResponse.refresh);
      localStorage.setItem('user', JSON.stringify(loginResponse.user));
      
      apiClient.setAuthToken(loginResponse.access);
      setUser(loginResponse.user);
      
      // Start auto-logout timer
      setTimeout(() => resetAutoLogoutTimer(), 100);
      
      showSuccessToast('ログインしました');
    } catch (error: any) {
      showErrorToast(error);
      throw error;
    }
  };

  const register = async (email: string, userId: string, password: string, firstName?: string, lastName?: string, organizationSlug?: string, subjectIds?: number[]) => {
    try {
      await authService.register({
        email,
        user_id: userId,
        password,
        password_confirm: password,
        first_name: firstName,
        last_name: lastName,
        subject_ids: subjectIds || []
      }, organizationSlug);

      showSuccessToast('会員登録が完了しました。メールアドレスに送信された確認リンクをクリックしてください。');
    } catch (error: any) {
      showErrorToast(error);
      throw error;
    }
  };

  const logout = async () => {
    try {
      await handleLogout();
      showSuccessToast('ログアウトしました');
    } catch (error) {
      console.error('Logout error:', error);
      // Still proceed with local logout even if API call fails
      await handleLogout();
    }
  };

  const refreshToken = async () => {
    try {
      const refreshTokenValue = authService.getRefreshToken();
      if (!refreshTokenValue) {
        throw new Error('No refresh token available');
      }

      const response = await authService.refreshToken(refreshTokenValue);
      localStorage.setItem('accessToken', response.access);
      apiClient.setAuthToken(response.access);
    } catch (error) {
      console.error('Token refresh failed:', error);
      await handleLogout();
      throw error;
    }
  };

  const verifyEmail = async (token: string) => {
    try {
      await authService.verifyEmail(token);
      showSuccessToast('メールアドレスが確認されました');
    } catch (error: any) {
      showErrorToast(error);
      throw error;
    }
  };

  const resendEmailVerification = async (email: string) => {
    try {
      await authService.resendEmailVerification(email);
      showSuccessToast('確認メールを再送信しました');
    } catch (error: any) {
      showErrorToast(error);
      throw error;
    }
  };

  const requestPasswordReset = async (email: string) => {
    try {
      await authService.requestPasswordReset(email);
      showSuccessToast('パスワードリセットのメールを送信しました');
    } catch (error: any) {
      showErrorToast(error);
      throw error;
    }
  };

  const confirmPasswordReset = async (token: string, newPassword: string) => {
    try {
      await authService.confirmPasswordReset(token, newPassword);
      showSuccessToast('パスワードがリセットされました');
    } catch (error: any) {
      showErrorToast(error);
      throw error;
    }
  };

  const changePassword = async (currentPassword: string, newPassword: string) => {
    try {
      await authService.changePassword(currentPassword, newPassword);
      showSuccessToast('パスワードが変更されました');
    } catch (error: any) {
      showErrorToast(error);
      throw error;
    }
  };

  const updateProfile = async (userData: Partial<User>) => {
    try {
      const updatedUser = await authService.updateProfile(userData);
      setUser(updatedUser);
      localStorage.setItem('user', JSON.stringify(updatedUser));
      showSuccessToast('プロフィールが更新されました');
    } catch (error: any) {
      showErrorToast(error);
      throw error;
    }
  };

  // Add activity listeners when user is logged in
  useEffect(() => {
    if (!user) return;

    const events = [
      'mousedown',
      'mousemove',
      'keypress',
      'scroll',
      'touchstart',
      'click',
    ];

    const resetOnActivity = () => {
      resetAutoLogoutTimer();
    };

    // Add event listeners for user activity
    events.forEach(event => {
      document.addEventListener(event, resetOnActivity, true);
    });

    // Handle page visibility change
    const handleVisibilityChange = () => {
      if (!document.hidden && user) {
        resetAutoLogoutTimer();
      }
    };

    // Handle window focus
    const handleWindowFocus = () => {
      if (user) {
        resetAutoLogoutTimer();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('focus', handleWindowFocus);

    // Start initial timer
    resetAutoLogoutTimer();

    // Cleanup function
    return () => {
      events.forEach(event => {
        document.removeEventListener(event, resetOnActivity, true);
      });
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('focus', handleWindowFocus);
      
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      if (warningTimeoutRef.current) {
        clearTimeout(warningTimeoutRef.current);
      }
    };
  }, [user]);

  return (
    <AuthContext.Provider value={{
      user,
      loading,
      login,
      register,
      logout,
      refreshToken,
      verifyEmail,
      resendEmailVerification,
      requestPasswordReset,
      confirmPasswordReset,
      changePassword,
      updateProfile,
      extendSession,
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};