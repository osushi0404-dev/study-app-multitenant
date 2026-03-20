// PWA Service Worker
// オフライン機能とキャッシュ管理

const CACHE_NAME = 'learning-app-v1';
const API_CACHE_NAME = 'learning-app-api-v1';

// キャッシュする静的ファイル
const STATIC_CACHE_URLS = [
  '/',
  '/static/js/bundle.js',
  '/static/css/main.css',
  '/manifest.json',
  '/favicon.ico'
];

// キャッシュするAPIエンドポイント
const API_CACHE_PATTERNS = [
  /\/api\/subjects\//,
  /\/api\/problems\//,
  /\/api\/studylogs\/statistics\//
];

// インストールイベント
self.addEventListener('install', (event) => {
  console.log('Service Worker installing...');
  
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('Caching static assets');
      return cache.addAll(STATIC_CACHE_URLS);
    })
  );
  
  // 新しいサービスワーカーを即座にアクティブ化
  self.skipWaiting();
});

// アクティベーションイベント
self.addEventListener('activate', (event) => {
  console.log('Service Worker activating...');
  
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME && cacheName !== API_CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      // すべてのクライアントでサービスワーカーを制御
      return self.clients.claim();
    })
  );
});

// フェッチイベント（リクエストインターセプト）
self.addEventListener('fetch', (event) => {
  const { request } = event;
  
  // GET リクエストのみキャッシュ
  if (request.method !== 'GET') {
    return;
  }
  
  // API リクエストの処理
  if (request.url.includes('/api/')) {
    event.respondWith(handleApiRequest(request));
    return;
  }
  
  // 静的ファイルの処理
  event.respondWith(handleStaticRequest(request));
});

// API リクエストの処理（Network First戦略）
async function handleApiRequest(request) {
  const url = new URL(request.url);
  
  // キャッシュ対象のAPIかチェック
  const shouldCache = API_CACHE_PATTERNS.some(pattern => pattern.test(url.pathname));
  
  if (!shouldCache) {
    // キャッシュしない場合はネットワークから直接取得
    return fetch(request);
  }
  
  try {
    // まずネットワークから取得を試みる
    const networkResponse = await fetch(request);
    
    // 成功した場合はキャッシュに保存
    if (networkResponse.status === 200) {
      const cache = await caches.open(API_CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.log('Network request failed, trying cache...', error);
    
    // ネットワークエラーの場合はキャッシュから取得
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // キャッシュにもない場合はオフライン応答
    return new Response(
      JSON.stringify({
        error: 'オフラインです。インターネット接続を確認してください。',
        offline: true
      }),
      {
        status: 503,
        statusText: 'Service Unavailable',
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

// 静的ファイルの処理（Cache First戦略）
async function handleStaticRequest(request) {
  try {
    // Chrome拡張機能のURLはキャッシュしない
    const url = new URL(request.url);
    if (url.protocol === 'chrome-extension:') {
      return fetch(request);
    }
    
    // まずキャッシュから探す
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // キャッシュにない場合はネットワークから取得
    const networkResponse = await fetch(request);
    
    // 成功した場合はキャッシュに保存（chrome-extension以外）
    if (networkResponse.status === 200 && url.protocol !== 'chrome-extension:') {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.log('Failed to fetch resource:', request.url, error);
    
    // オフライン用のフォールバックページ
    if (request.destination === 'document') {
      return caches.match('/');
    }
    
    // その他のリソースの場合はエラーを返す
    return new Response('リソースが利用できません', {
      status: 503,
      statusText: 'Service Unavailable'
    });
  }
}

// バックグラウンド同期
self.addEventListener('sync', (event) => {
  console.log('Background sync:', event.tag);
  
  if (event.tag === 'background-sync') {
    event.waitUntil(syncData());
  }
});

// データの同期処理
async function syncData() {
  try {
    // IndexedDBから未同期のデータを取得
    const unsyncedData = await getUnsyncedData();
    
    for (const data of unsyncedData) {
      try {
        await syncToServer(data);
        await markAsSynced(data.id);
      } catch (error) {
        console.error('Failed to sync data:', error);
      }
    }
  } catch (error) {
    console.error('Background sync failed:', error);
  }
}

// プッシュ通知
self.addEventListener('push', (event) => {
  console.log('Push notification received:', event);
  
  if (event.data) {
    const data = event.data.json();
    
    const options = {
      body: data.body || '新しい通知があります',
      icon: '/icon-192x192.png',
      badge: '/badge-72x72.png',
      vibrate: [100, 50, 100],
      data: {
        url: data.url || '/'
      },
      actions: [
        {
          action: 'open',
          title: '開く',
          icon: '/icon-192x192.png'
        },
        {
          action: 'close',
          title: '閉じる'
        }
      ]
    };
    
    event.waitUntil(
      self.registration.showNotification(data.title || '学習アプリ', options)
    );
  }
});

// 通知クリック処理
self.addEventListener('notificationclick', (event) => {
  console.log('Notification click:', event);
  
  event.notification.close();
  
  if (event.action === 'close') {
    return;
  }
  
  const url = event.notification.data?.url || '/';
  
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((clientList) => {
      // すでに開いているタブがあるかチェック
      for (const client of clientList) {
        if (client.url === url && 'focus' in client) {
          return client.focus();
        }
      }
      
      // 新しいタブを開く
      if (clients.openWindow) {
        return clients.openWindow(url);
      }
    })
  );
});

// IndexedDB操作のヘルパー関数
async function getUnsyncedData() {
  // 実装は後で追加
  return [];
}

async function syncToServer(data) {
  // 実装は後で追加
}

async function markAsSynced(id) {
  // 実装は後で追加
}

// キャッシュ管理ユーティリティ
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CACHE_CLEAR') {
    event.waitUntil(
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => caches.delete(cacheName))
        );
      }).then(() => {
        event.ports[0].postMessage({ success: true });
      })
    );
  }
});