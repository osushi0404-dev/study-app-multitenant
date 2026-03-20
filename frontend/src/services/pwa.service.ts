/**
 * PWA (Progressive Web App) サービス
 * 
 * Service Worker、オフライン機能、アプリインストールを管理
 */

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

class PWAService {
  private deferredPrompt: BeforeInstallPromptEvent | null = null;
  private isOnline = navigator.onLine;
  private onlineListeners: Array<(online: boolean) => void> = [];
  private updateListeners: Array<() => void> = [];

  constructor() {
    this.init();
  }

  private init() {
    // Service Worker の登録
    this.registerServiceWorker();
    
    // オンライン/オフライン状態の監視
    this.setupOnlineListeners();
    
    // アプリインストール関連の設定
    this.setupInstallPrompt();
    
    // Service Worker 更新の監視
    this.setupUpdateListener();
  }

  /**
   * Service Worker を登録
   */
  private async registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js');
        
        console.log('Service Worker registered successfully:', registration);
        
        // 更新チェック
        registration.addEventListener('updatefound', () => {
          console.log('Service Worker update found');
          this.notifyUpdateListeners();
        });
        
        // アクティブになったときの処理
        if (registration.active) {
          console.log('Service Worker is active');
        }
        
        return registration;
      } catch (error) {
        console.error('Service Worker registration failed:', error);
      }
    } else {
      console.log('Service Worker is not supported');
    }
  }

  /**
   * オンライン/オフライン状態の監視設定
   */
  private setupOnlineListeners() {
    const handleOnline = () => {
      this.isOnline = true;
      console.log('Online');
      this.notifyOnlineListeners(true);
    };

    const handleOffline = () => {
      this.isOnline = false;
      console.log('Offline');
      this.notifyOnlineListeners(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
  }

  /**
   * アプリインストールプロンプトの設定
   */
  private setupInstallPrompt() {
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      this.deferredPrompt = e as BeforeInstallPromptEvent;
      console.log('Install prompt available');
    });

    window.addEventListener('appinstalled', () => {
      console.log('App installed');
      this.deferredPrompt = null;
    });
  }

  /**
   * Service Worker 更新リスナーの設定
   */
  private setupUpdateListener() {
    navigator.serviceWorker?.addEventListener('controllerchange', () => {
      console.log('Service Worker controller changed');
      this.notifyUpdateListeners();
    });
  }

  /**
   * オンライン状態の取得
   */
  public getOnlineStatus(): boolean {
    return this.isOnline;
  }

  /**
   * オンライン状態変更の監視
   */
  public onOnlineStatusChange(callback: (online: boolean) => void) {
    this.onlineListeners.push(callback);
    
    // 購読解除関数を返す
    return () => {
      const index = this.onlineListeners.indexOf(callback);
      if (index > -1) {
        this.onlineListeners.splice(index, 1);
      }
    };
  }

  /**
   * Service Worker 更新の監視
   */
  public onUpdate(callback: () => void) {
    this.updateListeners.push(callback);
    
    return () => {
      const index = this.updateListeners.indexOf(callback);
      if (index > -1) {
        this.updateListeners.splice(index, 1);
      }
    };
  }

  /**
   * アプリのインストールプロンプト表示
   */
  public async showInstallPrompt(): Promise<boolean> {
    if (!this.deferredPrompt) {
      console.log('Install prompt not available');
      return false;
    }

    try {
      await this.deferredPrompt.prompt();
      const choiceResult = await this.deferredPrompt.userChoice;
      
      console.log('Install prompt result:', choiceResult.outcome);
      
      this.deferredPrompt = null;
      return choiceResult.outcome === 'accepted';
    } catch (error) {
      console.error('Install prompt error:', error);
      return false;
    }
  }

  /**
   * インストールプロンプトが利用可能かどうか
   */
  public isInstallPromptAvailable(): boolean {
    return this.deferredPrompt !== null;
  }

  /**
   * アプリがスタンドアロンモードで実行されているかどうか
   */
  public isStandalone(): boolean {
    return window.matchMedia('(display-mode: standalone)').matches ||
           (window.navigator as any).standalone === true;
  }

  /**
   * プッシュ通知の許可を要求
   */
  public async requestNotificationPermission(): Promise<NotificationPermission> {
    if (!('Notification' in window)) {
      console.log('This browser does not support notifications');
      return 'denied';
    }

    if (Notification.permission === 'granted') {
      return 'granted';
    }

    if (Notification.permission !== 'denied') {
      const permission = await Notification.requestPermission();
      return permission;
    }

    return Notification.permission;
  }

  /**
   * ローカル通知を表示
   */
  public showNotification(title: string, options?: NotificationOptions) {
    if (Notification.permission === 'granted') {
      new Notification(title, {
        icon: '/icon-192x192.png',
        badge: '/badge-72x72.png',
        ...options
      });
    }
  }

  /**
   * バックグラウンド同期を登録
   */
  public async registerBackgroundSync(tag: string): Promise<boolean> {
    if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
      try {
        const registration = await navigator.serviceWorker.ready;
        await (registration as any).sync.register(tag);
        console.log('Background sync registered:', tag);
        return true;
      } catch (error) {
        console.error('Background sync registration failed:', error);
        return false;
      }
    }
    return false;
  }

  /**
   * キャッシュをクリア
   */
  public async clearCache(): Promise<boolean> {
    try {
      if ('serviceWorker' in navigator) {
        const registration = await navigator.serviceWorker.ready;
        
        return new Promise((resolve) => {
          const messageChannel = new MessageChannel();
          messageChannel.port1.onmessage = (event) => {
            resolve(event.data.success || false);
          };
          
          registration.active?.postMessage(
            { type: 'CACHE_CLEAR' },
            [messageChannel.port2]
          );
        });
      }
      return false;
    } catch (error) {
      console.error('Cache clear failed:', error);
      return false;
    }
  }

  /**
   * Service Worker を手動更新
   */
  public async updateServiceWorker(): Promise<boolean> {
    try {
      if ('serviceWorker' in navigator) {
        const registration = await navigator.serviceWorker.ready;
        
        if (registration.waiting) {
          registration.waiting.postMessage({ type: 'SKIP_WAITING' });
          return true;
        }
        
        await registration.update();
        return true;
      }
      return false;
    } catch (error) {
      console.error('Service Worker update failed:', error);
      return false;
    }
  }

  /**
   * アプリの共有
   */
  public async shareApp(shareData?: ShareData): Promise<boolean> {
    const defaultShareData: ShareData = {
      title: '学習アプリ',
      text: '効率的な学習を支援するアプリです',
      url: window.location.href
    };

    const dataToShare = { ...defaultShareData, ...shareData };

    if (navigator.share) {
      try {
        await navigator.share(dataToShare);
        return true;
      } catch (error) {
        console.error('Share failed:', error);
        return false;
      }
    } else {
      // フォールバック: クリップボードにコピー
      try {
        await navigator.clipboard.writeText(dataToShare.url || window.location.href);
        return true;
      } catch (error) {
        console.error('Clipboard write failed:', error);
        return false;
      }
    }
  }

  private notifyOnlineListeners(online: boolean) {
    this.onlineListeners.forEach(callback => callback(online));
  }

  private notifyUpdateListeners() {
    this.updateListeners.forEach(callback => callback());
  }
}

// シングルトンインスタンス
export const pwaService = new PWAService();
export default pwaService;