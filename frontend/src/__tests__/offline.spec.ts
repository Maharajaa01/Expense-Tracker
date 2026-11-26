import 'fake-indexeddb/auto'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ApiError } from '@/services/api'
import { boot } from '@/services/boot'

vi.mock('@/services/sync', () => ({ syncApi: { push: vi.fn() } }))
vi.mock('@/services/finance', () => ({
  accountsApi: { list: vi.fn().mockResolvedValue({ accounts: [], totals: { net_worth: 0, assets: 0, liabilities: 0 } }) },
  categoriesApi: { list: vi.fn().mockResolvedValue([]) },
}))

import { syncApi } from '@/services/sync'
import { useSyncStore } from '@/stores/sync'
import { readThrough } from '@/offline/cache'
import { clearUser, db } from '@/offline/db'

const push = syncApi.push as unknown as ReturnType<typeof vi.fn>
const data = { transaction_type: 'Expense' as const, amount: 120, account: 'acc1', category: 'food', transaction_date: '2026-11-24' }

beforeEach(async () => {
  setActivePinia(createPinia())
  boot.data = { user: { name: 'a@example.com' } } as any
  await clearUser('a@example.com')
  await clearUser('b@example.com')
  push.mockReset()
})

describe('offline queue', () => {
  it('queues a create with its client ID and removes it once applied', async () => {
    const s = useSyncStore()
    await s.enqueue('create', { id: 'cid-1', data })
    expect(s.pending.map((i) => i.id)).toEqual(['cid-1'])
    expect(await (await db()).get('queue', 'cid-1')).toBeTruthy() // persisted in IndexedDB

    push.mockResolvedValue([{ client_txn_id: 'cid-1', op: 'create', status: 'applied' }])
    await s.sync()
    expect(push).toHaveBeenCalledWith([expect.objectContaining({ op: 'create', client_txn_id: 'cid-1', data })], expect.any(String))
    expect(s.items).toEqual([])
  })

  it('treats a duplicate as synced (request reached the server before)', async () => {
    const s = useSyncStore()
    await s.enqueue('create', { id: 'cid-2', data })
    push.mockResolvedValue([{ client_txn_id: 'cid-2', op: 'create', status: 'duplicate' }])
    await s.sync()
    expect(s.items).toEqual([])
  })

  it('keeps items when the network fails, and marks them for retry', async () => {
    const s = useSyncStore()
    await s.enqueue('create', { id: 'cid-3', data })
    push.mockRejectedValue(new ApiError('network', 'offline'))
    await s.sync()
    expect(s.items[0]).toMatchObject({ id: 'cid-3', status: 'failed', attempts: 1 })
    expect(s.pending).toHaveLength(1)
  })

  it('surfaces conflicts and rejections, and resolves "keep mine" with force', async () => {
    const s = useSyncStore()
    await s.enqueue('update', { id: 'u1', name: 'FTX-1', data: { amount: 90 }, expected_modified: 't0' })
    await s.enqueue('create', { id: 'bad', data: { ...data, amount: 0 } })
    push.mockResolvedValue([
      { client_txn_id: 'u1', op: 'update', status: 'conflict', reason: 'changed', message: 'Changed elsewhere', transaction: { name: 'FTX-1', amount: 120 } },
      { client_txn_id: 'bad', op: 'create', status: 'rejected', message: 'Amount must be greater than zero.' },
    ])
    await s.sync()
    expect(s.attention.map((i) => [i.id, i.status])).toEqual([['u1', 'conflict'], ['bad', 'rejected']])

    push.mockResolvedValue([{ client_txn_id: 'u1', op: 'update', status: 'applied' }])
    await s.resolve('u1', 'mine')
    expect(push).toHaveBeenLastCalledWith([expect.objectContaining({ client_txn_id: 'u1', force: true })], expect.any(String))
    expect(s.items.map((i) => i.id)).toEqual(['bad'])
  })

  it('folds edits and deletes of an unsynced entry into the queued create', async () => {
    const s = useSyncStore()
    await s.enqueue('create', { id: 'c9', data })
    await s.enqueue('update', { name: 'c9', data: { amount: 300 } })
    expect(s.items).toHaveLength(1)
    expect(s.items[0].data?.amount).toBe(300)
    await s.enqueue('delete', { name: 'c9' })
    expect(s.items).toEqual([])
  })

  it('refreshes an expired CSRF token once, then marks items as needing login', async () => {
    const s = useSyncStore()
    await s.enqueue('create', { id: 'auth1', data })
    window.user = undefined as any
    globalThis.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ message: { ok: true, data: { user: { name: 'a@example.com' }, csrf_token: 'new' } } }), { status: 200 })) as any
    push.mockRejectedValue(new ApiError('auth', 'CSRF', 400, 'CSRFTokenError'))
    await s.sync()
    expect(push).toHaveBeenCalledTimes(2)
    expect(s.items[0].status).toBe('auth')
  })

  it('keeps each user’s queue separate', async () => {
    const s = useSyncStore()
    await s.enqueue('create', { id: 'mine', data })
    boot.data = { user: { name: 'b@example.com' } } as any
    await s.reload()
    expect(s.items).toEqual([])
  })
})

describe('read cache', () => {
  it('stores allowlisted reads and serves them only on network failure', async () => {
    const fresh = await readThrough('budgets:current', async () => [{ name: 'b1' }])
    expect(fresh.savedAt).toBeNull()
    await new Promise((r) => setTimeout(r, 20)) // write is fire-and-forget
    const offline = await readThrough('budgets:current', async () => {
      throw new ApiError('network', 'offline')
    })
    expect(offline.data).toEqual([{ name: 'b1' }])
    expect(offline.savedAt).toBeTypeOf('number')
  })

  it('does not hide real errors behind cached data', async () => {
    await readThrough('accounts', async () => ['x'])
    await new Promise((r) => setTimeout(r, 20))
    await expect(readThrough('accounts', async () => {
      throw new ApiError('permission', 'nope', 403)
    })).rejects.toThrow('nope')
  })
})
