/**
 * Read-through cache for a short ALLOWLIST of screens, so the app still shows
 * something useful offline. Only these keys are ever stored; nothing else from
 * the API is written to the device.
 */
import { ApiError } from '@/services/api'
import { boot } from '@/services/boot'
import { db, idbAvailable } from './db'

export const CACHEABLE = ['accounts', 'categories', 'dashboard:this_month', 'transactions:recent', 'budgets:current'] as const
export type CacheKey = (typeof CACHEABLE)[number]

export interface Cached<T> {
  data: T
  /** Set when the network failed and this came from the device. */
  savedAt: number | null
}

function user() {
  return boot.data?.user.name ?? ''
}

export async function readThrough<T>(key: CacheKey, fetcher: () => Promise<T>): Promise<Cached<T>> {
  try {
    const data = await fetcher()
    if (idbAvailable() && user()) {
      db().then((d) => d.put('cache', { key: `${user()}:${key}`, user: user(), data, savedAt: Date.now() })).catch(() => {})
    }
    return { data, savedAt: null }
  } catch (e) {
    // Only fall back for connectivity problems; real errors (permission,
    // validation, server) must surface instead of showing stale data.
    if (!(e instanceof ApiError && e.kind === 'network') || !idbAvailable()) throw e
    const entry = await (await db()).get('cache', `${user()}:${key}`).catch(() => undefined)
    if (!entry) throw e
    return { data: entry.data as T, savedAt: entry.savedAt }
  }
}
