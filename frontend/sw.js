// ==========================================================================
// 日語雲端學習助手 - PWA 離線快取 Service Worker (sw.js)
// Version 3.1.0: 最佳化一般瀏覽器（Normal Browser Mode）體驗，導入 Network-First
// 策略防止靜態 HTML 快取僵死，同時支援離線平穩回退
// ==========================================================================

const CACHE_NAME = "nihongo-pwa-v3.1.0"; // 升級至 3.1.0 版本快取
const STATIC_ASSETS = [                 // 核心靜態快取資產列表
  "/",
  "/manifest.json",
  "/static/style.css?v=3.1.0",
  "/static/script.js?v=3.1.0",
  "/static/icon-192.png",
  "/static/icon-512.png"
];

// 安裝生命週期事件：預先下載並快取靜態核心資產
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("[Service Worker 3.1.0] 預快取靜態資源完畢");
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting(); // 強制跳過等待，立即啟用新版本
});

// 啟動生命週期事件：徹底清理所有舊版本快取
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log("[Service Worker 3.1.0] 清除舊版本過期快取:", key);
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim(); // 立即接管所有開啟中的客戶端視窗
});

// 網路請求攔截處理：
// 1. API 與動態資料：網路優先 (Network First)
// 2. 首頁導航 (HTML Navigate)：網路優先 (Network First with Offline Fallback)，徹底解決非無痕瀏覽器快取殘留問題
// 3. 靜態資源 (CSS/JS/Images)：Stale-While-Revalidate 兼顧極速載入與背景自動更新
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // 1. API 請求或非 GET 請求：一律採 Network First
  if (url.pathname.startsWith("/api/") || event.request.method !== "GET") {
    event.respondWith(
      fetch(event.request).catch(() => {
        return new Response(JSON.stringify({ error: "目前處於離線狀態，無法同步雲端資料庫" }), {
          headers: { "Content-Type": "application/json" }
        });
      })
    );
    return;
  }

  // 2. HTML 首頁導航請求：Network First 確保一般模式下始終加載最新頁面
  if (event.request.mode === "navigate" || url.pathname === "/") {
    event.respondWith(
      fetch(event.request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const copy = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          }
          return networkResponse;
        })
        .catch(() => caches.match("/") || caches.match(event.request))
    );
    return;
  }

  // 3. 靜態資源 (Stale-While-Revalidate)：有快取先用快取顯示，背景非同步抓最新版並更新快取
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      const fetchPromise = fetch(event.request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const copy = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        }
        return networkResponse;
      }).catch(() => cachedResponse);

      return cachedResponse || fetchPromise;
    })
  );
});
