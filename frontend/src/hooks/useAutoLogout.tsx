import { useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'react-hot-toast';

interface UseAutoLogoutOptions {
  timeoutMinutes?: number;
  warningMinutes?: number;
  enableWarning?: boolean;
}

export const useAutoLogout = ({
  timeoutMinutes = 30,
  warningMinutes = 5,
  enableWarning = true
}: UseAutoLogoutOptions = {}) => {
  const { user, logout } = useAuth();
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const warningTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const warningShownRef = useRef(false);

  const resetTimer = useCallback(() => {
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

    const timeoutMs = timeoutMinutes * 60 * 1000;
    const warningMs = (timeoutMinutes - warningMinutes) * 60 * 1000;

    // Set warning timer if enabled
    if (enableWarning && warningMs > 0) {
      warningTimeoutRef.current = setTimeout(() => {
        if (!warningShownRef.current && user) {
          warningShownRef.current = true;
          toast.custom((t) => (
            <div style={{
              background: 'white',
              padding: '16px',
              borderRadius: '8px',
              boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
              maxWidth: '350px'
            }}>
              <strong>セッション期限警告</strong>
              <br />
              {warningMinutes}分後に自動ログアウトします
              <br />
              <button
                onClick={() => {
                  toast.dismiss(t.id);
                  resetTimer(); // Reset timer on user interaction
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
            duration: warningMinutes * 60 * 1000, // Show warning for remaining time
            icon: '⚠️',
          });
        }
      }, warningMs);
    }

    // Set logout timer
    timeoutRef.current = setTimeout(async () => {
      if (user) {
        toast.error('セッションがタイムアウトしました。再度ログインしてください。');
        await logout();
      }
    }, timeoutMs);
  }, [logout, user, timeoutMinutes, warningMinutes, enableWarning]);

  const extendSession = useCallback(() => {
    resetTimer();
    toast.success('セッションを延長しました');
  }, [resetTimer]);

  useEffect(() => {
    if (!user) return;

    // Reset timer when user becomes active
    resetTimer();

    // Activity event listeners
    const events = [
      'mousedown',
      'mousemove',
      'keypress',
      'scroll',
      'touchstart',
      'click'
    ];

    const resetOnActivity = () => {
      resetTimer();
    };

    // Add event listeners for user activity
    events.forEach(event => {
      document.addEventListener(event, resetOnActivity);
    });

    // Cleanup function
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      if (warningTimeoutRef.current) {
        clearTimeout(warningTimeoutRef.current);
      }

      events.forEach(event => {
        document.removeEventListener(event, resetOnActivity);
      });
    };
  }, [user, resetTimer]);

  // Handle page visibility change
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden && user) {
        // Reset timer when page becomes visible again
        resetTimer();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [user, resetTimer]);

  // Handle window focus
  useEffect(() => {
    const handleWindowFocus = () => {
      if (user) {
        resetTimer();
      }
    };

    window.addEventListener('focus', handleWindowFocus);

    return () => {
      window.removeEventListener('focus', handleWindowFocus);
    };
  }, [user, resetTimer]);

  return {
    extendSession,
    resetTimer,
  };
};
