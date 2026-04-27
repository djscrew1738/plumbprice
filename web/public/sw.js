/* global self, caches, fetch, Response, URL */
// PlumbPrice service worker — v2 (PWA shell, runtime caching).
// On every release, bump SW_VERSION to force-refresh clients.

const SW_VERSION = '2.1.1-rc1';
const SHELL_CACHE = `plumbprice-shell-${SW_VERSION}`;
const STATIC_CACHE = `plumbprice-static-${SW_VERSION}`;
const RUNTIME_CACHE = `plumbprice-runtime-${SW_VERSION}`;
const API_CACHE = `plumbprice-api-${SW_VERSION}`;

// App shell — small set of HTML routes the field tech reaches first.
// We don't precache full pages (Next emits hashed JS chunks) — we precache
// the offline fallback and let runtime caching handle the rest.
const SHELL_URLS = ['/offline', '/manifest.json', '/icon-192.png', '/icon-512.png'];

// API GETs we're willing to serve stale-while-revalidate so the estimator
// loads instantly even on bad LTE. Limited to read-only reference data.
const SWR_API_PATHS = [
  '/api/v1/templates',
  '/api/v1/markups',
  '/api/v1/suppliers',
  '/api/v1/admin/items',
];

// API endpoints that must always hit network (auth, mutations, fresh AI calls).
const NEVER_CACHE_API = [
  '/api/v1/auth',
  '/api/v1/voice',
  '/api/v1/quote',
  '/api/v1/public-agent',
  '/api/v1/photos',
  '/api/v1/blueprints',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL_URLS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      const valid = new Set([SHELL_CACHE, STATIC_CACHE, RUNTIME_CACHE, API_CACHE]);
      await Promise.all(keys.filter((k) => !valid.has(k)).map((k) => caches.delete(k)));
      await self.clients.claim();
    })()
  );
});

// Allow the page to ask us to skip waiting (used for the "update available" UX).
self.addEventListener('message', (event) => {
  if (event.data === 'SKIP_WAITING') self.skipWaiting();
});

function isStaticAsset(url) {
  return (
    url.pathname.startsWith('/_next/static/') ||
    url.pathname.startsWith('/icon') ||
    url.pathname === '/favicon.ico' ||
    url.pathname === '/manifest.json'
  );
}

function isImageAsset(url) {
  return url.pathname.startsWith('/_next/image') ||
         /\.(png|jpe?g|webp|avif|svg|gif)$/i.test(url.pathname);
}

function isSwrApi(url) {
  return SWR_API_PATHS.some((p) => url.pathname.startsWith(p));
}

function isNeverCacheApi(url) {
  return NEVER_CACHE_API.some((p) => url.pathname.startsWith(p));
}

// --- Strategies -----------------------------------------------------------

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) return cached;
  const resp = await fetch(request);
  if (resp.ok) cache.put(request, resp.clone());
  return resp;
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const resp = await fetch(request);
    if (resp.ok) cache.put(request, resp.clone());
    return resp;
  } catch {
    const cached = await cache.match(request);
    if (cached) return cached;
    throw new Error('offline and no cache');
  }
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  const fetchPromise = fetch(request)
    .then((resp) => {
      if (resp.ok) cache.put(request, resp.clone());
      return resp;
    })
    .catch(() => null);
  return cached || (await fetchPromise) || new Response(JSON.stringify({ error: 'offline' }), {
    status: 503,
    headers: { 'Content-Type': 'application/json' },
  });
}

// --- Fetch routing --------------------------------------------------------

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // Cross-origin: let the browser handle it.
  if (url.origin !== self.location.origin) return;

  // Navigations: network-first, fallback to /offline shell.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(async () => {
        const shell = await caches.open(SHELL_CACHE);
        return (await shell.match('/offline')) ||
               new Response('offline', { status: 503 });
      })
    );
    return;
  }

  // Hashed Next.js static assets are immutable — cache-first forever.
  if (isStaticAsset(url)) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // Images — stale-while-revalidate (works well for /_next/image hashes).
  if (isImageAsset(url)) {
    event.respondWith(staleWhileRevalidate(request, RUNTIME_CACHE));
    return;
  }

  // API: opt-in caching of reference data only. Mutations + AI never cached.
  if (url.pathname.startsWith('/api/')) {
    if (isNeverCacheApi(url)) return; // default network
    if (isSwrApi(url)) {
      event.respondWith(staleWhileRevalidate(request, API_CACHE));
      return;
    }
    return;
  }

  // Everything else (e.g., third-party fonts already CDN-cached): default.
});
