<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import Money from '@/components/ui/Money.vue'
import ResponsiveSheet from '@/components/ui/ResponsiveSheet.vue'
import { useFinanceStore } from '@/stores/finance'
import { useSyncStore } from '@/stores/sync'
import type { QueueItem } from '@/offline/db'
import type { TransactionRowData } from '@/types/finance'

const open = defineModel<boolean>('open', { required: true })
const sync = useSyncStore()
const finance = useFinanceStore()

const items = computed(() => [...sync.attention, ...sync.pending])
const opLabel = { create: 'New', update: 'Edit', delete: 'Delete' }
function describe(i: QueueItem) {
  const d = i.data ?? {}
  const cat = d.category ? finance.categoryMap.get(d.category)?.category_name : null
  return d.title || cat || (i.op === 'delete' ? 'Transaction' : d.transaction_type ?? 'Transaction')
}
const statusText: Record<string, string> = {
  queued: 'Waiting to sync', syncing: 'Syncing…', failed: 'Will retry', conflict: 'Changed on another device',
  rejected: 'Not accepted', auth: 'Log in again to sync',
}
function login() {
  window.location.href = `/login?redirect-to=${encodeURIComponent(window.location.pathname)}`
}
const server = (i: QueueItem) => i.server as TransactionRowData | null | undefined
</script>

<template>
  <ResponsiveSheet v-model:open="open" title="Changes on this device" size="md">
    <div class="pb-2">
      <p class="mb-3 text-sm text-ink-muted">
        These changes were made while offline. They're saved on this device and sent to your account when you're online.
        Balances update once they sync.
      </p>
      <p v-if="!items.length" class="py-8 text-center text-sm text-ink-muted">Everything is synced.</p>
      <ul class="divide-y divide-line/60 rounded-tile ring-1 ring-line/60">
        <li v-for="i in items" :key="i.id" class="px-3 py-3">
          <div class="flex items-start gap-3">
            <span class="mt-0.5 rounded-full bg-ink/[0.06] px-2 py-0.5 text-[11px] font-semibold text-ink-muted">{{ opLabel[i.op] }}</span>
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-ink">{{ describe(i) }}</p>
              <p class="text-[13px]" :class="['conflict', 'rejected', 'auth'].includes(i.status) ? 'text-expense' : 'text-ink-muted'">
                {{ i.message && i.status !== 'queued' ? i.message : statusText[i.status] }}
              </p>
            </div>
            <Money v-if="i.data?.amount" :value="Number(i.data.amount)" size="sm" class="text-ink" />
          </div>

          <div v-if="i.status === 'conflict'" class="mt-2 space-y-2 pl-1">
            <p v-if="server(i)" class="text-[13px] text-ink-muted">
              The other device has: {{ server(i)!.title }}, <Money :value="server(i)!.amount" size="sm" />.
            </p>
            <div class="flex flex-wrap gap-2">
              <button v-if="server(i) !== null" type="button" class="h-8 rounded-full bg-brand-solid px-3 text-[13px] font-semibold text-white" @click="sync.resolve(i.id, 'mine')">Keep my version</button>
              <button type="button" class="h-8 rounded-full px-3 text-[13px] font-medium text-ink ring-1 ring-line" @click="sync.resolve(i.id, 'theirs')">
                {{ server(i) === null ? 'OK, discard my edit' : 'Keep the other version' }}
              </button>
            </div>
          </div>
          <div v-else-if="i.status === 'rejected'" class="mt-2 flex gap-2 pl-1">
            <button type="button" class="h-8 rounded-full px-3 text-[13px] font-medium text-expense ring-1 ring-line" @click="sync.discard(i.id)">Discard</button>
          </div>
          <div v-else-if="i.status === 'auth'" class="mt-2 pl-1">
            <button type="button" class="h-8 rounded-full bg-brand-solid px-3 text-[13px] font-semibold text-white" @click="login">Log in</button>
          </div>
          <div v-else-if="i.status === 'failed'" class="mt-2 pl-1">
            <button type="button" class="h-8 rounded-full px-3 text-[13px] font-medium text-ink ring-1 ring-line" :disabled="!sync.online" @click="sync.retry(i.id)">Retry now</button>
          </div>
        </li>
      </ul>
      <p v-if="sync.lastSyncAt" class="mt-3 text-xs text-ink-faint">Last synced {{ new Date(sync.lastSyncAt).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' }) }}</p>
    </div>
  </ResponsiveSheet>
</template>
