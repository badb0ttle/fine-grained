// AI 情报站 · Service Worker (Phase 5)
// Cache-first for static assets, network-first for data files

const CACHE_NAME = 'ai-intel-v3';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/dashboard.html',
  '/leaderboard.html',
  '/timeline.html',
  '/clusters.html',
  '/manifest.json',
  '/assets/style.css',
  '/assets/icon.svg',
  // AI助手已暂时关闭: '/assets/ai-assistant.css', '/assets/ai-assistant.js',
];

// Install — cache static assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(STATIC_ASSETS).catch(err => {
        console.warn('SW install: partial cache', err);
      });
    })
  );
  self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

// Handle SKIP_WAITING message from client
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// Fetch — network-first for data, network-first for HTML, cache-first for static
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Network-first for data files (they update daily)
  if (url.pathname.startsWith('/data/')) {
    event.respondWith(networkFirst(event.request));
    return;
  }

  // Network-first for HTML pages (always get latest version)
  if (event.request.mode === 'navigate' ||
      url.pathname.endsWith('.html') ||
      url.pathname === '/') {
    event.respondWith(networkFirst(event.request));
    return;
  }

  // Cache-first for versioned static assets
  if (url.pathname.startsWith('/assets/')) {
    event.respondWith(cacheFirst(event.request));
    return;
  }

  // Default: network-first
  event.respondWith(networkFirst(event.request));
});

// Cache-first strategy
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    const cache = await caches.open(CACHE_NAME);
    cache.put(request, response.clone());
    return response;
  } catch (err) {
    return new Response('Offline — resource not available', { status: 503 });
  }
}

// Network-first strategy (with cache fallback)
async function networkFirst(request) {
  try {
    const response = await fetch(request);
    const cache = await caches.open(CACHE_NAME);
    cache.put(request, response.clone());
    return response;
  } catch (err) {
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response('Offline — please check your connection', {
      status: 503,
      headers: { 'Content-Type': 'text/html; charset=utf-8' }
    });
  }
}
