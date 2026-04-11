import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { userActionLogger } from '../utils/userActionLogger';

/**
 * React Routerのナビゲーションを追跡するコンポーネント
 */
export const NavigationLogger = () => {
  const location = useLocation();

  useEffect(() => {
    // 初回レンダリング時は記録しない
    let isFirstRender = true;
    let previousPath = location.pathname;

    return () => {
      if (!isFirstRender) {
        userActionLogger.logNavigation(previousPath, location.pathname);
      }
      isFirstRender = false;
    };
  }, [location.pathname]);

  // 何もレンダリングしない
  return null;
};

export default NavigationLogger;
