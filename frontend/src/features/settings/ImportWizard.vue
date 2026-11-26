<script setup lang="ts">
/** CSV import: choose file → options → preview (nothing saved) → import. */
import { computed, ref } from 'vue'
import { toast } from 'frappe-ui'
import AppIcon from '@/components/ui/AppIcon.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import SelectField from '@/components/ui/SelectField.vue'
import { ApiError } from '@/services/api'
import { ioApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import type { ImportPreview, ImportRow } from '@/types/finance'
import { formatMoney } from '@/utils/money'

const emit = defineEmits<{ done: [] }>()
const finance = useFinanceStore()
const MAX_MB = 2

const fileName = ref('')
const text = ref('')
const defaultAccount = ref(finance.defaultAccount ?? '')
const defaultType = ref<'Expense' | 'Income'>('Expense')
const createMissing = ref(false)
const includeDupes = ref(false)
const preview = ref<ImportPreview | null>(null)
const result = ref<{ imported: number; skipped: number; failed: number } | null>(null)
const busy = ref(false)
const error = ref<string | null>(null)
const filter = ref<'all' | 'error' | 'duplicate'>('all')

const accountOptions = computed(() => finance.activeAccounts.map((a) => ({ value: a.name, label: a.account_name })))
const options = computed(() => ({
  default_account: defaultAccount.value || undefined,
  default_type: defaultType.value,
  create_missing_categories: (createMissing.value ? 1 : 0) as 0 | 1,
  include_duplicates: (includeDupes.value ? 1 : 0) as 0 | 1,
}))
const shown = computed(() => (preview.value?.rows ?? []).filter((r) => filter.value === 'all' || r.status === filter.value).slice(0, 200))
const toImport = computed(() => (preview.value ? preview.value.summary.ok + (includeDupes.value ? preview.value.summary.duplicate : 0) : 0))

async function onFile(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  preview.value = null
  result.value = null
  error.value = null
  if (f.size > MAX_MB * 1024 * 1024) {
    error.value = `The file is larger than ${MAX_MB} MB. Split it into smaller files.`
    return
  }
  fileName.value = f.name
  text.value = await f.text()
}

async function runPreview() {
  if (!text.value || busy.value) return
  busy.value = true
  error.value = null
  try {
    preview.value = await ioApi.preview(text.value, options.value)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Could not read the file.'
  } finally {
    busy.value = false
  }
}

async function runImport() {
  if (!preview.value || busy.value) return
  busy.value = true
  error.value = null
  try {
    const res = await ioApi.commit(text.value, options.value)
    result.value = res
    preview.value = { ...preview.value, rows: res.rows }
    toast.success(`${res.imported} ${res.imported === 1 ? 'transaction' : 'transactions'} imported`)
    await finance.changed()
    await finance.reloadCategories()
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Import failed. Nothing was imported.'
  } finally {
    busy.value = false
  }
}

const statusLabel: Record<ImportRow['status'], string> = { ok: 'Ready', error: 'Error', duplicate: 'Possible duplicate', imported: 'Imported' }
const statusClass: Record<ImportRow['status'], string> = {
  ok: 'bg-brand-soft text-brand-ink', error: 'bg-expense-soft text-expense', duplicate: 'bg-warn-soft text-warn', imported: 'bg-ink/[0.06] text-ink-muted',
}
</script>

<template>
  <div class="space-y-5 pb-2">
    <section>
      <p class="text-sm text-ink-muted">
        Columns are matched by name: <b>Date</b> and <b>Amount</b> (or Debit/Credit) are required; Type, Category, Subcategory,
        Account, To Account, Description and Notes are optional. Dates are read day first (DD/MM/YYYY) or as YYYY-MM-DD.
        Up to 1,000 rows per file. Nothing is saved until you press Import.
      </p>
      <label class="mt-3 flex cursor-pointer items-center gap-3 rounded-tile border border-dashed border-line px-4 py-3 hover:bg-ink/[0.03]">
        <AppIcon name="upload" class="size-5 text-brand-ink" />
        <span class="flex-1 text-sm text-ink">{{ fileName || 'Choose a CSV file' }}</span>
        <input type="file" accept=".csv,text/csv" class="sr-only" @change="onFile" />
      </label>
    </section>

    <section v-if="text" class="grid gap-3 sm:grid-cols-2">
      <SelectField v-model="defaultAccount" label="Account for rows without one" :options="accountOptions" placeholder="None (rows must name an account)" />
      <div>
        <span class="mb-1.5 block text-sm font-medium text-ink">Amounts without a sign or type are</span>
        <SegmentedControl v-model="defaultType" label="Default type" size="sm" :options="[{ value: 'Expense', label: 'Expenses' }, { value: 'Income', label: 'Income' }]" />
      </div>
      <label class="flex items-start gap-3 text-sm text-ink sm:col-span-2">
        <input v-model="createMissing" type="checkbox" class="mt-0.5 size-4 rounded text-brand-solid focus:ring-brand" />
        <span>Create categories that don't exist yet<span class="block text-ink-muted">Otherwise rows with unknown categories are skipped.</span></span>
      </label>
    </section>

    <p v-if="error" role="alert" class="rounded-tile bg-expense-soft/60 p-3 text-sm text-ink">{{ error }}</p>

    <button v-if="text && !preview" type="button" class="flex h-11 w-full items-center justify-center gap-2 rounded-full bg-brand-solid font-semibold text-white disabled:opacity-60" :disabled="busy" @click="runPreview">
      <AppIcon v-if="busy" name="refresh-cw" class="size-4 animate-spin" /> Check file
    </button>

    <section v-if="preview">
      <div class="mb-3 flex flex-wrap gap-2 text-[13px]">
        <span class="rounded-full bg-brand-soft px-3 py-1 font-medium text-brand-ink">{{ preview.summary.ok }} ready</span>
        <span v-if="preview.summary.error" class="rounded-full bg-expense-soft px-3 py-1 font-medium text-expense">{{ preview.summary.error }} with errors</span>
        <span v-if="preview.summary.duplicate" class="rounded-full bg-warn-soft px-3 py-1 font-medium text-warn">{{ preview.summary.duplicate }} possible duplicates</span>
        <span v-if="preview.summary.imported" class="rounded-full bg-ink/[0.06] px-3 py-1 font-medium text-ink-muted">{{ preview.summary.imported }} already imported</span>
      </div>
      <p v-if="preview.new_categories.length" class="mb-3 text-[13px] text-ink-muted">
        Will create: {{ preview.new_categories.map((c) => `${c.name} (${c.type.toLowerCase()})`).join(', ') }}.
      </p>
      <label v-if="preview.summary.duplicate && !result" class="mb-3 flex items-start gap-3 text-sm text-ink">
        <input v-model="includeDupes" type="checkbox" class="mt-0.5 size-4 rounded text-brand-solid focus:ring-brand" />
        <span>Import possible duplicates too<span class="block text-ink-muted">They match an existing transaction's date, amount and account.</span></span>
      </label>
      <SegmentedControl v-model="filter" label="Show rows" size="sm" class="mb-2" :options="[{ value: 'all', label: 'All rows' }, { value: 'error', label: 'Errors' }, { value: 'duplicate', label: 'Duplicates' }]" />
      <ul class="max-h-80 divide-y divide-line/60 overflow-y-auto rounded-tile ring-1 ring-line/60">
        <li v-for="r in shown" :key="r.row" class="px-3 py-2 text-sm">
          <div class="flex items-center gap-2">
            <span class="w-10 shrink-0 text-xs tabular text-ink-faint">#{{ r.row }}</span>
            <span class="min-w-0 flex-1 truncate text-ink">{{ r.title || r.transaction_type }}<span class="text-ink-muted">, {{ r.transaction_date }}</span></span>
            <span class="tabular text-ink">{{ r.amount !== null ? formatMoney(r.amount) : '' }}</span>
            <span class="shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold" :class="statusClass[r.status]">{{ statusLabel[r.status] }}</span>
          </div>
          <p v-for="e in r.errors" :key="e" class="ml-12 mt-0.5 text-[13px] text-expense">{{ e }}</p>
        </li>
      </ul>
      <p v-if="(preview.rows.length ?? 0) > shown.length" class="mt-1 text-xs text-ink-faint">Showing the first {{ shown.length }} rows.</p>

      <div v-if="result" class="mt-4 rounded-tile bg-brand-soft/60 p-3 text-sm text-ink">
        Imported {{ result.imported }}. Skipped {{ result.skipped }}<template v-if="result.failed">, {{ result.failed }} failed</template>.
        <button type="button" class="ml-2 font-semibold text-brand-ink underline" @click="emit('done')">Done</button>
      </div>
      <button v-else type="button" class="mt-4 flex h-11 w-full items-center justify-center gap-2 rounded-full bg-brand-solid font-semibold text-white disabled:opacity-60" :disabled="busy || !toImport" @click="runImport">
        <AppIcon v-if="busy" name="refresh-cw" class="size-4 animate-spin" />
        {{ toImport ? `Import ${toImport} ${toImport === 1 ? 'transaction' : 'transactions'}` : 'Nothing to import' }}
      </button>
    </section>
  </div>
</template>
