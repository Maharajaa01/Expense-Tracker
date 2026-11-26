/**
 * IndexedDB storage for offline use. Everything is keyed by user so a shared
 * device never shows one person's data to another, and logout wipes it.
 *
 * Stores:
 *  - queue: changes made offline, waiting to sync (see stores/sync.ts)
 *  - cache: a small allowlist of read results (see offline/cache.ts)
 */
import { openDB, type DBSchema, type IDBPDatabase } from 'idb'
import type { TransactionInput } from '@/types/finance'

export type QueueStatus = 'queued' | 'syncing' | 'failed' | 'conflict' | 'rejected' | 'auth'

export interface QueueItem {
  id: string // = client_txn_id of the operation
  user: string
  op: 'create' | 'update' | 'delete'
  name?: string // transaction name for update/delete
  data?: Partial<TransactionInput>
  expected_modified?: string
  force?: boolean
  status: QueueStatus
  message?: string
  /** Server version returned with a conflict (null = deleted elsewhere). */
  server?: unknown
  attempts: number
  createdAt: number
  updatedAt: number
}

export interface CacheEntry {
  key: string // `${user}:${name}`
  user: string
  data: unknown
  savedAt: number
}

interface Schema extends DBSchema {
  queue: { key: string; value: QueueItem; indexes: { by_user: string } }
  cache: { key: string; value: CacheEntry; indexes: { by_user: string } }
}

let dbp: Promise<IDBPDatabase<Schema>> | null = null

export function db(): Promise<IDBPDatabase<Schema>> {
  if (!dbp) {
    dbp = openDB<Schema>('expense-tracker', 1, {
      upgrade(d) {
        d.createObjectStore('queue', { keyPath: 'id' }).createIndex('by_user', 'user')
        d.createObjectStore('cache', { keyPath: 'key' }).createIndex('by_user', 'user')
      },
    })
  }
  return dbp
}

export function idbAvailable(): boolean {
  try {
    return typeof indexedDB !== 'undefined'
  } catch {
    return false
  }
}

/** Remove everything stored for other users (shared device after a user switch). */
export async function dropOtherUsers(user: string) {
  const d = await db()
  for (const store of ['queue', 'cache'] as const) {
    const tx = d.transaction(store, 'readwrite')
    let cursor = await tx.store.openCursor()
    while (cursor) {
      if (cursor.value.user !== user && store === 'cache') await cursor.delete()
      cursor = await cursor.continue()
    }
    await tx.done
  }
}

/** Logout: wipe this user's cached data and queue on this device. */
export async function clearUser(user: string) {
  const d = await db()
  for (const store of ['queue', 'cache'] as const) {
    const keys = await d.getAllKeysFromIndex(store, 'by_user', user)
    const tx = d.transaction(store, 'readwrite')
    await Promise.all(keys.map((k) => tx.store.delete(k)))
    await tx.done
  }
}
