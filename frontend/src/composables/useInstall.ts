import { computed, ref } from 'vue'

/**
 * "Install app" state, shared app-wide.
 *
 * - Chrome/Edge/Samsung (Android + desktop) fire `beforeinstallprompt`; we keep
 *   it and show the native prompt when the button is pressed.
 * - iOS/iPadOS Safari has no prompt API: the button shows Add to Home Screen steps.
 * - The button disappears once the app is installed: running standalone, the
 *   `appinstalled` event, or a remembered install on this browser.
 */
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

const INSTALLED_KEY = 'et-installed'
const deferred = ref<BeforeInstallPromptEvent | null>(null)
const installedFlag = ref(readFlag())
const standalone = ref(isStandalone())

function readFlag() {
  try {
    return localStorage.getItem(INSTALLED_KEY) === '1'
  } catch {
    return false
  }
}
function setFlag(v: boolean) {
  installedFlag.value = v
  try {
    v ? localStorage.setItem(INSTALLED_KEY, '1') : localStorage.removeItem(INSTALLED_KEY)
  } catch {
    /* ignore */
  }
}
function isStandalone() {
  if (typeof window === 'undefined') return false
  return window.matchMedia?.('(display-mode: standalone)').matches || (navigator as any).standalone === true
}

export const platform = (() => {
  if (typeof navigator === 'undefined') return 'other'
  const ua = navigator.userAgent
  const iOS = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
  if (iOS) return /CriOS|FxiOS|EdgiOS/.test(ua) ? 'ios-other' : 'ios-safari'
  if (/Android/.test(ua)) return 'android'
  return 'desktop'
})()

/** Call once, as early as possible (main.ts), so the event isn't missed. */
export function listenForInstall() {
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault()
    deferred.value = e as BeforeInstallPromptEvent
    // Chrome only fires this when the app is NOT installed, so clear a stale flag
    // (e.g. the user uninstalled the app).
    if (installedFlag.value) setFlag(false)
  })
  window.addEventListener('appinstalled', () => {
    deferred.value = null
    setFlag(true)
  })
  window.matchMedia?.('(display-mode: standalone)').addEventListener?.('change', (e) => (standalone.value = e.matches))
  if (standalone.value) setFlag(true)
}

export function useInstall() {
  const installed = computed(() => standalone.value || installedFlag.value)
  const canPrompt = computed(() => !!deferred.value)
  /** Show the button until installed. Without a native prompt we show instructions instead. */
  const showButton = computed(() => !installed.value)

  async function promptInstall(): Promise<'accepted' | 'dismissed' | 'unavailable'> {
    const ev = deferred.value
    if (!ev) return 'unavailable'
    await ev.prompt()
    const { outcome } = await ev.userChoice
    deferred.value = null // a prompt event can only be used once
    if (outcome === 'accepted') setFlag(true)
    return outcome
  }

  return { installed, canPrompt, showButton, promptInstall, platform }
}
