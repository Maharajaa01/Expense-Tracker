<script setup lang="ts">
/** Receipts on a transaction: view, add (camera or files), remove. Online only. */
import { onMounted, ref } from 'vue'
import { dialog, toast } from 'frappe-ui'
import AppIcon from '@/components/ui/AppIcon.vue'
import { ApiError } from '@/services/api'
import { attachmentsApi, MAX_RECEIPT_MB } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import { useSyncStore } from '@/stores/sync'
import type { Receipt } from '@/types/finance'

const props = defineProps<{ transaction: string; pending?: boolean }>()
const sync = useSyncStore()
const finance = useFinanceStore()
const receipts = ref<Receipt[]>([])
const loading = ref(false)
const uploading = ref(0)
const error = ref<string | null>(null)
const input = ref<HTMLInputElement>()

async function load() {
  if (props.pending || !sync.online) return
  loading.value = true
  try {
    receipts.value = await attachmentsApi.list(props.transaction)
    error.value = null
  } catch (e) {
    error.value = e instanceof ApiError && e.kind === 'network' ? null : 'Could not load receipts.'
  } finally {
    loading.value = false
  }
}
onMounted(load)

async function onFiles(e: Event) {
  const files = [...((e.target as HTMLInputElement).files ?? [])]
  ;(e.target as HTMLInputElement).value = ''
  for (const f of files) {
    uploading.value++
    try {
      receipts.value.push(await attachmentsApi.upload(props.transaction, f))
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : `Could not upload ${f.name}.`)
    } finally {
      uploading.value--
    }
  }
  if (files.length) finance.dataVersion++ // refresh the paperclip marker in lists
}

function remove(r: Receipt) {
  dialog.danger({
    title: 'Remove this receipt?',
    message: `${r.file_name} will be deleted. The transaction stays.`,
    confirmLabel: 'Remove',
    onConfirm: async () => {
      try {
        await attachmentsApi.remove(r.name)
        receipts.value = receipts.value.filter((x) => x.name !== r.name)
        finance.dataVersion++
      } catch (e) {
        throw new Error(e instanceof ApiError ? e.message : 'Could not remove the receipt.')
      }
    },
  })
}
const isImage = (r: Receipt) => r.mime_type.startsWith('image/') && r.mime_type !== 'image/heic'
const size = (b: number) => (b > 1024 * 1024 ? `${(b / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1024))} KB`)
</script>

<template>
  <section class="mt-4" aria-labelledby="receipts-h">
    <div class="mb-2 flex items-center justify-between">
      <h3 id="receipts-h" class="text-sm font-medium text-ink">Receipts</h3>
      <button
        v-if="!pending && sync.online"
        type="button"
        class="inline-flex items-center gap-1 text-sm font-medium text-brand-ink hover:underline disabled:opacity-60"
        :disabled="uploading > 0"
        @click="input?.click()"
      >
        <AppIcon :name="uploading ? 'refresh-cw' : 'paperclip'" class="size-4" :class="{ 'animate-spin': uploading }" />
        {{ uploading ? 'Uploading…' : 'Add receipt' }}
      </button>
      <input ref="input" type="file" accept="image/*,application/pdf" multiple class="hidden" @change="onFiles" />
    </div>
    <p v-if="pending" class="text-[13px] text-ink-muted">Receipts can be added after this entry syncs.</p>
    <p v-else-if="!sync.online" class="text-[13px] text-ink-muted">Receipts are available when you're online.</p>
    <p v-else-if="error" class="text-[13px] text-expense">{{ error }}</p>
    <p v-else-if="!loading && !receipts.length" class="text-[13px] text-ink-muted">No receipt yet. Photos or PDFs up to {{ MAX_RECEIPT_MB }} MB, kept private to you.</p>
    <ul v-if="receipts.length" class="grid grid-cols-3 gap-2 sm:grid-cols-4">
      <li v-for="r in receipts" :key="r.name" class="group relative overflow-hidden rounded-tile ring-1 ring-line/60">
        <a :href="r.file_url" target="_blank" rel="noopener" class="block aspect-square bg-ink/[0.03]" :aria-label="`Open ${r.file_name}`">
          <img v-if="isImage(r)" :src="r.file_url" alt="" loading="lazy" class="size-full object-cover" />
          <span v-else class="flex size-full flex-col items-center justify-center gap-1 text-ink-muted">
            <AppIcon name="receipt" class="size-7" />
            <span class="px-1 text-center text-[11px]">{{ r.mime_type === 'application/pdf' ? 'PDF' : 'Photo' }}, {{ size(r.file_size) }}</span>
          </span>
        </a>
        <button type="button" class="absolute right-1 top-1 inline-flex size-7 items-center justify-center rounded-full bg-card/90 text-ink shadow ring-1 ring-line" :aria-label="`Remove ${r.file_name}`" @click="remove(r)">
          <AppIcon name="x" class="size-3.5" />
        </button>
      </li>
    </ul>
  </section>
</template>
