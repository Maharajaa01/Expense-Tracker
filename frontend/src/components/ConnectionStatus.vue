<script setup lang="ts">
/** Online/offline and pending-sync indicator, shown above page content when relevant. */
import { computed, ref } from 'vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import SyncSheet from '@/components/SyncSheet.vue'
import { useSyncStore } from '@/stores/sync'

const sync = useSyncStore()
const sheet = ref(false)
const pendingCount = computed(() => sync.pending.length)
const attentionCount = computed(() => sync.attention.length)
const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? '' : 's'}`
</script>

<template>
  <div aria-live="polite">
    <div v-if="!sync.online" class="mb-4 flex items-center gap-3 rounded-tile bg-ink px-4 py-2.5 text-sm text-canvas">
      <AppIcon name="wifi-off" class="size-4 shrink-0" />
      <span class="flex-1">
        You're offline. New entries are kept on this device<template v-if="pendingCount"> ({{ plural(pendingCount, 'change') }} waiting)</template>.
      </span>
      <button v-if="pendingCount || attentionCount" type="button" class="font-semibold underline" @click="sheet = true">View</button>
    </div>
    <div v-else-if="sync.syncing" class="mb-4 flex items-center gap-3 rounded-tile bg-brand-soft px-4 py-2.5 text-sm text-brand-ink">
      <AppIcon name="refresh-cw" class="size-4 shrink-0 animate-spin" />
      Syncing {{ sync.progress.done }} of {{ sync.progress.total }}…
    </div>
    <div v-else-if="attentionCount" class="mb-4 flex items-center gap-3 rounded-tile bg-expense-soft/70 px-4 py-2.5 text-sm text-ink">
      <AppIcon name="triangle-alert" class="size-4 shrink-0 text-expense" />
      <span class="flex-1">{{ plural(attentionCount, 'change') }} from this device need{{ attentionCount === 1 ? 's' : '' }} your attention.</span>
      <button type="button" class="font-semibold text-expense underline" @click="sheet = true">Review</button>
    </div>
    <div v-else-if="pendingCount" class="mb-4 flex items-center gap-3 rounded-tile bg-warn-soft px-4 py-2.5 text-sm text-ink">
      <AppIcon name="cloud-upload" class="size-4 shrink-0 text-warn" />
      <span class="flex-1">{{ plural(pendingCount, 'change') }} waiting to sync.</span>
      <button type="button" class="font-semibold underline" @click="sync.sync()">Sync now</button>
    </div>
    <p v-if="sync.storageError" class="mb-4 rounded-tile bg-warn-soft px-4 py-2.5 text-sm text-ink">{{ sync.storageError }}</p>
    <SyncSheet v-model:open="sheet" />
  </div>
</template>
