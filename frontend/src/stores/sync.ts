/**
 * Offline change queue and sync engine.
 *
 * Changes made while offline are stored in IndexedDB with their client
 * transaction ID and replayed through /api/method/expense_tracker.api.sync.push.
 * The server is idempotent for creates (unique client ID) and deletes, and
 * detects edit conflicts, so replaying is always safe.
 *
 * Sync runs: on start, when the browser goes online, when the tab becomes
 * visible, every 30 s while anything is pending, on Background Sync (Chromium,
 * via the service worker) and on "Sync now". Foreground sync is the reliable
 * path; Background Sync is only a bonus where supported.
 */
import { defineStore } from 'pinia'
import { ApiError } from '@/services/api'
import { boot, loadBoot } from '@/services/boot'
import { syncApi, type SyncOpPayload } from '@/services/sync'
import type { TransactionInput } from '@/types/finance'
import { uuid } from '@/utils/id'
import { clearUser, db, dropOtherUsers, idbAvailable, type QueueItem } from '@/offline/db'
import { useFinanceStore } from './finance'

const BATCH = 25
const DEVICE_KEY = 'et-device-id'

function deviceId(): string {
  try {
    let id = localStorage.getItem(DEVICE_KEY)
    if (!id) {
      id = uuid()
      localStorage.setItem(DEVICE_KEY, id)
    }
    return id
  } catch {
    return 'unknown'
  }
}

export const useSyncStore = defineStore('sync', {
  state: () => ({
    online: typeof navigator === 'undefined' ? true : navigator.onLine,
    items: [] as QueueItem[],
    syncing: false,
    progress: { done: 0, total: 0 },
    lastSyncAt: null as number | null,
    storageError: null as string | null,
  }),
  getters: {
    pending: (s) => s.items.filter((i) => i.status === 'queued' || i.status === 'syncing' || i.status === 'failed'),
    attention: (s) => s.items.filter((i) => i.status === 'conflict' || i.status === 'rejected' || i.status === 'auth'),
    pendingCreates: (s) => s.items.filter((i) => i.op === 'create'),
    /** Transaction names with a queued delete (hidden from lists until synced). */
    pendingDeletes: (s) => new Set(s.items.filter((i) => i.op === 'delete' && i.name).map((i) => i.name!)),
    pendingUpdates: (s) => new Map(s.items.filter((i) => i.op === 'update' && i.name).map((i) => [i.name!, i])),
  },
  actions: {
    user() {
      return boot.data?.user.name ?? ''
    },

    async init() {
      if (!idbAvailable()) {
        this.storageError = 'This browser blocks offline storage, so changes can only be saved while online.'
        return
      }
      try {
        await dropOtherUsers(this.user())
        await this.reload()
      } catch {
        this.storageError = 'Offline storage is unavailable (private browsing?). Changes can only be saved online.'
        return
      }
      window.addEventListener('online', () => {
        this.online = true
        this.sync()
      })
      window.addEventListener('offline', () => (this.online = false))
      // Real request outcomes override navigator.onLine (which can claim online when it isn't).
      window.addEventListener('et-connectivity', (e) => {
        const online = (e as CustomEvent<boolean>).detail
        const recovered = online && !this.online
        this.online = online
        if (recovered) this.sync()
      })
      document.addEventListener('visibilitychange', () => document.visibilityState === 'visible' && this.sync())
      navigator.serviceWorker?.addEventListener('message', (e) => e.data?.type === 'sync' && this.sync())
      setInterval(() => {
        if (!this.online) this.probe()
        else if (this.pending.length) this.sync()
      }, 30_000)
      // Items left "syncing" by a closed tab are retried.
      for (const i of this.items.filter((x) => x.status === 'syncing')) await this.save({ ...i, status: 'queued' })
      this.sync()
    },

    /** Lightweight reachability check while offline (no 'online' event comes after lie-fi). */
    async probe() {
      try {
        const res = await fetch('/api/method/ping', { credentials: 'same-origin', cache: 'no-store' })
        if (res.ok) window.dispatchEvent(new CustomEvent('et-connectivity', { detail: true }))
      } catch {
        /* still offline */
      }
    },

    async reload() {
      const all = await (await db()).getAllFromIndex('queue', 'by_user', this.user())
      this.items = all.sort((a, b) => a.createdAt - b.createdAt)
    },

    async save(item: QueueItem) {
      // Store a plain copy: items read back from this store are reactive proxies,
      // which IndexedDB's structured clone rejects (DataCloneError).
      item = JSON.parse(JSON.stringify(item)) as QueueItem
      await (await db()).put('queue', item)
      const i = this.items.findIndex((x) => x.id === item.id)
      i === -1 ? this.items.push(item) : this.items.splice(i, 1, item)
    },

    async remove(id: string) {
      await (await db()).delete('queue', id)
      this.items = this.items.filter((x) => x.id !== id)
    },

    /** Queue a change made while offline. Returns false if storage is unavailable. */
    async enqueue(op: QueueItem['op'], args: { id?: string; name?: string; data?: Partial<TransactionInput>; expected_modified?: string }) {
      if (this.storageError) return false
      // Editing or deleting something that was itself created offline: fold into the queued create.
      const queuedCreate = args.name ? this.items.find((i) => i.op === 'create' && i.id === args.name) : undefined
      if (queuedCreate) {
        if (op === 'delete') await this.remove(queuedCreate.id)
        else await this.save({ ...queuedCreate, data: { ...queuedCreate.data, ...args.data }, updatedAt: Date.now() })
        return true
      }
      const now = Date.now()
      await this.save({
        id: args.id ?? uuid(), user: this.user(), op, name: args.name, data: args.data,
        expected_modified: args.expected_modified, status: 'queued', attempts: 0, createdAt: now, updatedAt: now,
      })
      try {
        const reg = await navigator.serviceWorker?.ready
        await (reg as any)?.sync?.register('et-sync')
      } catch {
        /* Background Sync unsupported: foreground sync covers it */
      }
      return true
    },

    async sync() {
      if (this.syncing || !this.online || this.storageError) return
      const ready = this.items.filter((i) => i.status === 'queued' || i.status === 'failed')
      if (!ready.length) return
      this.syncing = true
      this.progress = { done: 0, total: ready.length }
      let anyApplied = false
      let refreshedSession = false
      try {
        for (let start = 0; start < ready.length; start += BATCH) {
          const batch = ready.slice(start, start + BATCH)
          for (const i of batch) await this.save({ ...i, status: 'syncing' })
          const payload: SyncOpPayload[] = batch.map((i) => ({
            op: i.op, client_txn_id: i.id, name: i.name, data: i.data as Record<string, unknown>,
            expected_modified: i.expected_modified, force: i.force,
          }))
          let results
          try {
            results = await syncApi.push(payload, deviceId())
          } catch (e) {
            if (e instanceof ApiError && e.kind === 'auth' && !refreshedSession) {
              // A stale CSRF token after a long offline period: refresh it once and retry.
              refreshedSession = true
              try {
                await loadBoot(true)
                results = await syncApi.push(payload, deviceId())
              } catch (e2) {
                await this.failBatch(batch, e2)
                break
              }
            } else {
              await this.failBatch(batch, e)
              break
            }
          }
          for (const r of results) {
            const item = batch.find((b) => b.id === r.client_txn_id)
            if (!item) continue
            if (r.status === 'applied' || r.status === 'duplicate') {
              await this.remove(item.id)
              anyApplied = true
            } else if (r.status === 'conflict') {
              await this.save({ ...item, status: 'conflict', message: r.message, server: r.transaction ?? null, updatedAt: Date.now() })
            } else if (r.status === 'rejected') {
              await this.save({ ...item, status: 'rejected', message: r.message, updatedAt: Date.now() })
            } else {
              await this.save({ ...item, status: 'failed', message: r.message, attempts: item.attempts + 1, updatedAt: Date.now() })
            }
            this.progress.done++
          }
        }
        this.lastSyncAt = Date.now()
      } finally {
        this.syncing = false
        if (anyApplied) await useFinanceStore().changed()
      }
    },

    async failBatch(batch: QueueItem[], e: unknown) {
      const err = e instanceof ApiError ? e : null
      const status = err?.kind === 'auth' ? 'auth' : 'failed'
      if (err?.kind === 'network') this.online = navigator.onLine
      const message =
        status === 'auth' ? 'Your session has expired. Log in again to sync these changes.'
          : err?.kind === 'network' ? 'Waiting for a connection.'
            : err?.message ?? 'Sync failed. It will be retried.'
      for (const i of batch) await this.save({ ...i, status, message, attempts: i.attempts + 1, updatedAt: Date.now() })
    },

    async retry(id: string) {
      const i = this.items.find((x) => x.id === id)
      if (i) await this.save({ ...i, status: 'queued', message: undefined })
      await this.sync()
    },

    /** Conflict: keep my version (overwrite) or keep the other device's version (drop mine). */
    async resolve(id: string, choice: 'mine' | 'theirs') {
      const i = this.items.find((x) => x.id === id)
      if (!i) return
      if (choice === 'theirs' || (i.op === 'update' && i.server === null)) {
        await this.remove(id)
        await useFinanceStore().changed()
        return
      }
      await this.save({ ...i, status: 'queued', force: true, message: undefined })
      await this.sync()
    },

    async discard(id: string) {
      await this.remove(id)
    },

    async clearForLogout() {
      try {
        await clearUser(this.user())
      } catch {
        /* nothing stored */
      }
      this.items = []
      navigator.serviceWorker?.controller?.postMessage({ type: 'clear-user-data' })
    },
  },
})
