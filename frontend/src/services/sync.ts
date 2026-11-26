import { api } from './api'
import type { TransactionRowData } from '@/types/finance'

export interface SyncOpPayload {
  op: 'create' | 'update' | 'delete'
  client_txn_id: string
  name?: string
  data?: Record<string, unknown>
  expected_modified?: string
  force?: boolean
}

export interface SyncResult {
  client_txn_id: string
  op: string
  status: 'applied' | 'duplicate' | 'conflict' | 'rejected' | 'error'
  reason?: 'changed' | 'deleted'
  message?: string
  transaction?: TransactionRowData | null
}

export const syncApi = {
  push: (ops: SyncOpPayload[], deviceId: string) =>
    api.post<SyncResult[]>('expense_tracker.api.sync.push', { ops, device_id: deviceId }),
}
