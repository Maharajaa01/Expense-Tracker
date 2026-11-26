/* Expense Tracker service worker.
 *
 * Served from /expense/sw.js with scope "/expense" (see expense_tracker/pwa.py) so it covers
 * the app. Built by the `et-service-worker` Vite plugin, which replaces
 * __VERSION__ and __PRECACHE__ with the build's hashed asset list.
 *
 * What is cached:
 *   - Hashed build assets (JS/CSS/fonts/icons): cache-first. Safe: content-addressed.
 *   - The app page (/expense/...): network-first; the last good copy is the
 *     offline fallback. Redirects (e.g. to /login) and errors are never cached.
 * What is NOT cached here:
 *   - /api/* responses. The app keeps a small, per-user allowlist of reads in
 *     IndexedDB itself, so financial data is never cached indiscriminately.
 */
const VERSION = '__VERSION__'
const PRECACHE = __PRECACHE__
const ASSET_PREFIX = '/assets/expense_tracker/'
const STATIC_CACHE = `et-static-${VERSION}`
const SHELL_CACHE = 'et-shell'
// Canonical app URL: Frappe redirects /expense/ to /expense (a redirect is never cached).
const SHELL_KEY = '/expense'

const OFFLINE_HTML = `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Offline - Expense Tracker</title><body style="font-family:system-ui,sans-serif;background:#faf8f5;color:#171721;display:grid;place-items:center;min-height:100vh;margin:0;padding:24px;text-align:center">
<div><h1 style="font-size:20px">You're offline</h1><p style="color:#626270;max-width:320px">Expense Tracker needs to be opened online once on this device before it can work offline.</p>
<button onclick="location.reload()" style="margin-top:12px;height:44px;padding:0 20px;border:0;border-radius:999px;background:#047857;color:#fff;font-weight:600">Try again</button></div></body></html>`

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => cache.addAll(PRECACHE))
      // The first visit happens before this worker exists, so store the page now;
      // otherwise "open once, then go offline" would show the offline screen.
      .then(() => refreshShell())
      .then(() => self.skipWaiting()),
  )
})

/** Fetch the app page and keep it, but only a real logged-in page (not a login redirect). */
async function refreshShell() {
  try {
    const res = await fetch(SHELL_KEY, { credentials: 'same-origin', cache: 'no-store' })
    if (res.ok && !res.redirected && (res.headers.get('content-type') || '').includes('text/html')) {
      await (await caches.open(SHELL_CACHE)).put(SHELL_KEY, res)
    }
  } catch {
    /* offline during install: the next navigation will store it */
  }
}

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith('et-static-') && k !== STATIC_CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const req = event.request
  if (req.method !== 'GET') return
  const url = new URL(req.url)
  if (url.origin !== self.location.origin) return

  if (req.mode === 'navigate' && (url.pathname === '/expense' || url.pathname.startsWith('/expense/'))) {
    event.respondWith(networkFirstShell(req))
    return
  }
  if (url.pathname.startsWith(ASSET_PREFIX)) {
    event.respondWith(cacheFirst(req))
  }
  // Everything else (including /api/*) goes straight to the network.
})

async function networkFirstShell(req) {
  try {
    const res = await fetch(req)
    // Only a real app page is stored: never login redirects or error pages.
    if (res.ok && !res.redirected && (res.headers.get('content-type') || '').includes('text/html')) {
      const cache = await caches.open(SHELL_CACHE)
      await cache.put(SHELL_KEY, res.clone())
    }
    return res
  } catch {
    const cached = await caches.match(SHELL_KEY, { cacheName: SHELL_CACHE })
    return cached || new Response(OFFLINE_HTML, { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } })
  }
}

async function cacheFirst(req) {
  const cached = await caches.match(req)
  if (cached) return cached
  const res = await fetch(req)
  if (res.ok) {
    const cache = await caches.open(STATIC_CACHE)
    cache.put(req, res.clone())
  }
  return res
}

self.addEventListener('message', (event) => {
  const msg = event.data || {}
  if (msg.type === 'refresh-shell') {
    // Sent by the app on each load so the stored page (and its session token) stays current.
    event.waitUntil(refreshShell())
  }
  if (msg.type === 'clear-user-data') {
    // Logout: drop the cached page (it contains the user's name and session token).
    event.waitUntil(caches.delete(SHELL_CACHE))
  }
})

// Background Sync (Chromium only): wake an open tab to flush the offline queue.
// Other browsers rely on the app's foreground sync (online/visibility/timer).
self.addEventListener('sync', (event) => {
  if (event.tag === 'et-sync') {
    event.waitUntil(
      self.clients.matchAll({ type: 'window' }).then((clients) => clients.forEach((c) => c.postMessage({ type: 'sync' }))),
    )
  }
})
