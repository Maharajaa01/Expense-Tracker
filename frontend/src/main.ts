import './index.css'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { useColorScheme } from 'frappe-ui'
import router from './router'
import App from './App.vue'
import { loadBoot } from './services/boot'
import { applyProfileTheme } from './composables/useTheme'
import { listenForInstall } from './composables/useInstall'
import { useFinanceStore } from './stores/finance'
import { useSyncStore } from './stores/sync'

// Must be registered before the browser fires it (it can fire very early).
listenForInstall()

async function start() {
  // Apply the saved light/dark preference before first paint.
  useColorScheme()
  const app = createApp(App)
  const pinia = createPinia()
  app.use(pinia)
  app.use(router)
  try {
    await loadBoot()
  } catch {
    // Not logged in (dev mode) – send to Frappe login and come back.
    window.location.href = `/login?redirect-to=${encodeURIComponent(window.location.pathname)}`
    return
  }
  applyProfileTheme()
  app.mount('#app')
  // Load (and cache for offline) accounts and categories up front, so Quick Add
  // works even if the connection drops before any other screen is opened.
  useFinanceStore(pinia).load()
  useSyncStore(pinia).init()
  warmOfflineCache()
  registerServiceWorker()
}

/**
 * Shortly after start-up, fetch the screens people most need offline (recent
 * transactions, this month's budgets) so they're available even if those
 * pages were never opened online. Only the allowlisted cache keys are written.
 */
function warmOfflineCache() {
  setTimeout(async () => {
    if (!navigator.onLine) return
    const [{ readThrough }, { transactionsApi, budgetsApi }] = await Promise.all([import('./offline/cache'), import('./services/finance')])
    readThrough('transactions:recent', () => transactionsApi.list({}, 1, 50, 'date_desc')).catch(() => {})
    readThrough('budgets:current', () => budgetsApi.list(undefined, true)).catch(() => {})
  }, 4000)
}

function registerServiceWorker() {
  if (!import.meta.env.PROD || !('serviceWorker' in navigator)) return
  // Wait until the page has loaded and settled: precaching downloads the whole
  // app for offline use and must not compete with the first screen on slow networks.
  const start = () => setTimeout(doRegister, 2000)
  document.readyState === 'complete' ? start() : window.addEventListener('load', start, { once: true })
}

function doRegister() {
  // Scope without a trailing slash: login and links land on the bare /expense URL.
  navigator.serviceWorker
    .register('/expense/sw.js', { scope: '/expense' })
    .then(async () => {
      const reg = await navigator.serviceWorker.ready
      if (navigator.onLine) reg.active?.postMessage({ type: 'refresh-shell' })
    })
    .catch((e) => {
      // Not fatal: the app works online without it. Logged for diagnosis.
      console.warn('Service worker registration failed', e)
    })
}

// After a deploy, an open tab may request a lazy chunk that no longer exists.
// Reload once to pick up the new build instead of showing a broken page.
router.onError((err, to) => {
  if (/Failed to fetch dynamically imported module|Importing a module script failed|error loading dynamically imported module/i.test(String(err?.message))) {
    const key = 'et-chunk-reload'
    if (sessionStorage.getItem(key) !== to.fullPath) {
      sessionStorage.setItem(key, to.fullPath)
      window.location.assign(`/expense${to.fullPath}`)
    }
  }
})

start()
