<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/components/ui/AppIcon.vue'
import ResponsiveSheet from '@/components/ui/ResponsiveSheet.vue'
import { notificationsApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import type { FinanceNotification } from '@/types/finance'

const finance = useFinanceStore()
const router = useRouter()
const open = ref(false)
const items = ref<FinanceNotification[]>([])
const unread = ref(0)
const error = ref<string | null>(null)

async function refresh() {
  try {
    const res = await notificationsApi.list(false, 30)
    items.value = res.items
    unread.value = res.unread
    error.value = null
  } catch {
    error.value = 'Could not load notifications.'
  }
}
onMounted(refresh)
watch(() => finance.dataVersion, refresh)

async function markAll() {
  try {
    unread.value = (await notificationsApi.markRead()).unread
    items.value = items.value.map((n) => ({ ...n, is_read: 1 }))
  } catch {
    error.value = 'Could not update notifications.'
  }
}
const ROUTES: Record<string, string> = { 'Finance Budget': 'budgets', 'Recurring Transaction': 'recurring', 'Savings Goal': 'goals' }
async function openItem(n: FinanceNotification) {
  if (!n.is_read) {
    notificationsApi.markRead(n.name).then((r) => (unread.value = r.unread)).catch(() => {})
    n.is_read = 1
  }
  const route = n.reference_doctype ? ROUTES[n.reference_doctype] : null
  open.value = false
  if (route) router.push({ name: route })
}
const ago = (iso: string) => {
  const mins = Math.round((Date.now() - new Date(iso.replace(' ', 'T')).getTime()) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  if (mins < 1440) return `${Math.round(mins / 60)} h ago`
  return `${Math.round(mins / 1440)} d ago`
}
</script>

<template>
  <button
    type="button"
    class="relative inline-flex size-10 items-center justify-center rounded-full bg-card text-ink ring-1 ring-line hover:bg-ink/[0.03]"
    :aria-label="unread ? `Notifications, ${unread} unread` : 'Notifications'"
    @click="open = true; refresh()"
  >
    <AppIcon name="bell" class="size-5" />
    <span v-if="unread" class="absolute -right-0.5 -top-0.5 min-w-[18px] rounded-full bg-expense-solid px-1 text-center text-[11px] font-semibold leading-[18px] text-white">{{ unread > 9 ? '9+' : unread }}</span>
  </button>
  <ResponsiveSheet v-model:open="open" title="Notifications" size="md">
    <div class="pb-2">
      <div v-if="unread" class="mb-2 flex justify-end">
        <button type="button" class="text-sm font-medium text-brand-ink hover:underline" @click="markAll">Mark all as read</button>
      </div>
      <p v-if="error" role="alert" class="text-sm text-expense">{{ error }}</p>
      <p v-else-if="!items.length" class="py-10 text-center text-sm text-ink-muted">You're all caught up. Budget alerts and payment reminders appear here.</p>
      <ul class="divide-y divide-line/60">
        <li v-for="n in items" :key="n.name">
          <button type="button" class="flex w-full gap-3 px-1 py-3 text-left" @click="openItem(n)">
            <span class="mt-1.5 size-2 shrink-0 rounded-full" :class="n.is_read ? 'bg-transparent' : n.severity === 'Danger' ? 'bg-expense' : n.severity === 'Warning' ? 'bg-warn' : 'bg-brand'" aria-hidden="true" />
            <span class="min-w-0 flex-1">
              <span class="block text-sm text-ink" :class="{ 'font-semibold': !n.is_read }">{{ n.title }}</span>
              <span v-if="n.message" class="block text-[13px] text-ink-muted">{{ n.message }}</span>
              <span class="block text-xs text-ink-faint">{{ ago(n.creation) }}<span v-if="!n.is_read" class="sr-only">, unread</span></span>
            </span>
          </button>
        </li>
      </ul>
    </div>
  </ResponsiveSheet>
</template>
