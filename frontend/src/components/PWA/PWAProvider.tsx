import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import pwaService from '../../services/pwa.service';

interface PWAContextType {
  isOnline: boolean;
  isStandalone: boolean;
  isInstallPromptAvailable: boolean;
  showInstallPrompt: () => Promise<boolean>;
  requestNotificationPermission: () => Promise<NotificationPermission>;
  showNotification: (title: string, options?: NotificationOptions) => void;
  shareApp: (shareData?: ShareData) => Promise<boolean>;
  clearCache: () => Promise<boolean>;
}

const PWAContext = createContext<PWAContextType | undefined>(undefined);

interface PWAProviderProps {
  children: ReactNode;
}

export const PWAProvider: React.FC<PWAProviderProps> = ({ children }) => {
  const [isOnline, setIsOnline] = useState(pwaService.getOnlineStatus());
  const [isStandalone] = useState(pwaService.isStandalone());
  const [isInstallPromptAvailable, setIsInstallPromptAvailable] = useState(false);

  useEffect(() => {
    // オンライン状態の監視
    const unsubscribeOnline = pwaService.onOnlineStatusChange(setIsOnline);

    // インストールプロンプトの監視
    const checkInstallPrompt = () => {
      setIsInstallPromptAvailable(pwaService.isInstallPromptAvailable());
    };
    
    checkInstallPrompt();
    const installCheckInterval = setInterval(checkInstallPrompt, 1000);

    return () => {
      unsubscribeOnline();
      clearInterval(installCheckInterval);
    };
  }, []);

  const showInstallPrompt = async (): Promise<boolean> => {
    const result = await pwaService.showInstallPrompt();
    setIsInstallPromptAvailable(pwaService.isInstallPromptAvailable());
    return result;
  };

  const requestNotificationPermission = async (): Promise<NotificationPermission> => {
    return await pwaService.requestNotificationPermission();
  };

  const showNotification = (title: string, options?: NotificationOptions) => {
    pwaService.showNotification(title, options);
  };

  const shareApp = async (shareData?: ShareData): Promise<boolean> => {
    return await pwaService.shareApp(shareData);
  };

  const clearCache = async (): Promise<boolean> => {
    return await pwaService.clearCache();
  };

  const contextValue: PWAContextType = {
    isOnline,
    isStandalone,
    isInstallPromptAvailable,
    showInstallPrompt,
    requestNotificationPermission,
    showNotification,
    shareApp,
    clearCache
  };

  return (
    <PWAContext.Provider value={contextValue}>
      {children}
    </PWAContext.Provider>
  );
};

export const usePWA = (): PWAContextType => {
  const context = useContext(PWAContext);
  if (context === undefined) {
    throw new Error('usePWA must be used within a PWAProvider');
  }
  return context;
};

export default PWAProvider;