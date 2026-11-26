import { reactive } from 'vue'
import { api } from './api'

export interface BootUser {
  name: string
  full_name: string
  first_name: string
  image: string | null
  time_zone: string
}

export interface BootProfile {
  default_account: string | null
  last_used_account: string | null
  theme: 'System' | 'Light' | 'Dark'
  week_start: 'Monday' | 'Sunday'
}

export interface BootData {
  user: BootUser
  profile: BootProfile | null
  csrf_token: string
  site_name: string
  app_version: string
  currency: string
  server_date: string
}

export const boot = reactive<{ ready: boolean; data: BootData | null }>({
  ready: false,
  data: null,
})

/**
 * In production the server injects boot values into `window` (see
 * www/expense.py). In Vite dev mode they are absent, so fetch them.
 */
export async function loadBoot(refresh = false): Promise<BootData> {
  if (!refresh && window.user && window.csrf_token) {
    boot.data = {
      user: window.user,
      csrf_token: window.csrf_token,
      site_name: window.site_name ?? '',
      app_version: window.app_version ?? '',
      currency: window.currency ?? 'INR',
      profile: window.profile ?? null,
      server_date: window.server_date ?? '',
    }
  } else {
    boot.data = await api.get<BootData>('expense_tracker.api.boot.get_boot')
    // Keep the page-level token in step so later requests use the fresh one.
    window.csrf_token = boot.data.csrf_token
  }
  boot.ready = true
  return boot.data
}

export function csrfToken(): string {
  return boot.data?.csrf_token ?? window.csrf_token ?? ''
}
