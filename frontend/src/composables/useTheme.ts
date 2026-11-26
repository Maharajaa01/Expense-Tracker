import { computed } from 'vue'
import { useColorScheme, type ColorScheme } from 'frappe-ui'
import { boot } from '@/services/boot'
import { profileApi } from '@/services/finance'

const TO_SERVER = { light: 'Light', dark: 'Dark', system: 'System' } as const
const FROM_SERVER = { Light: 'light', Dark: 'dark', System: 'system' } as const

/**
 * Light / dark / system. Backed by frappe-ui's colour-scheme state, which sets
 * `data-theme` on <html> (our tokens key off it) and remembers the choice in
 * this browser. The choice is also saved to the user's profile so a new
 * device starts with it.
 */
export function useTheme() {
  const { colorScheme, resolvedColorScheme, setColorScheme } = useColorScheme()
  return {
    scheme: computed(() => colorScheme.value),
    isDark: computed(() => resolvedColorScheme.value === 'dark'),
    setScheme: (s: ColorScheme) => {
      setColorScheme(s)
      profileApi.update({ theme: TO_SERVER[s] }).catch(() => {
        /* preference still applies locally; it syncs next time */
      })
    },
  }
}

/** On a browser with no saved choice, start from the profile's theme. */
export function applyProfileTheme() {
  let stored: string | null = null
  try {
    stored = localStorage.getItem('theme')
  } catch {
    /* storage unavailable */
  }
  const fromProfile = boot.data?.profile?.theme
  if (!stored && fromProfile) useColorScheme().setColorScheme(FROM_SERVER[fromProfile])
}

export const THEME_OPTIONS = [
  { value: 'light' as const, label: 'Light', icon: 'sun' },
  { value: 'dark' as const, label: 'Dark', icon: 'moon' },
  { value: 'system' as const, label: 'Auto', icon: 'monitor' },
]
