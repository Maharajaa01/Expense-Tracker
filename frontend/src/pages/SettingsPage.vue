<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { dialog, toast } from 'frappe-ui'
import InstallAppButton from '@/components/InstallAppButton.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import ResponsiveSheet from '@/components/ui/ResponsiveSheet.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import SelectField from '@/components/ui/SelectField.vue'
import BankAlertsSettings from '@/features/settings/BankAlertsSettings.vue'
import ImportWizard from '@/features/settings/ImportWizard.vue'
import { THEME_OPTIONS, useTheme } from '@/composables/useTheme'
import { ApiError } from '@/services/api'
import { boot } from '@/services/boot'
import { ioApi, profileApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import { useSyncStore } from '@/stores/sync'

const finance = useFinanceStore()
const sync = useSyncStore()
const { scheme, setScheme } = useTheme()
onMounted(() => finance.load())

const weekStart = ref<'Monday' | 'Sunday'>(boot.data?.profile?.week_start ?? 'Monday')
const defaultAccount = ref(finance.defaultAccount ?? '')
const accountOptions = computed(() => finance.activeAccounts.map((a) => ({ value: a.name, label: a.account_name })))
const importOpen = ref(false)

async function save(field: 'week_start' | 'default_account', value: string) {
  try {
    await profileApi.update({ [field]: value })
    if (boot.data?.profile) (boot.data.profile as any)[field] = value
    if (field === 'default_account') finance.defaultAccount = value
    else finance.dataVersion++ // week boundaries changed
    toast.success('Saved')
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : 'Could not save.')
  }
}

function clearDevice() {
  const n = sync.items.length
  dialog.danger({
    title: 'Clear offline data on this device?',
    message: n
      ? `${n} unsynced ${n === 1 ? 'change' : 'changes'} will be lost. Your account data is not affected.`
      : 'Saved screens for offline use are removed from this device. Your account data is not affected.',
    confirmLabel: 'Clear',
    onConfirm: async () => {
      await sync.clearForLogout()
      toast.success('Offline data cleared')
    },
  })
}
const version = boot.data?.app_version
</script>

<template>
  <div class="mx-auto max-w-2xl">
    <PageHeader title="Settings" />

    <section class="mb-6 rounded-card bg-card p-4 ring-1 ring-line/60 sm:p-5" aria-labelledby="pref-h">
      <h2 id="pref-h" class="mb-4 text-[15px] font-semibold text-ink">Preferences</h2>
      <div class="space-y-4">
        <div>
          <span class="mb-1.5 block text-sm font-medium text-ink">Appearance</span>
          <SegmentedControl :model-value="scheme" :options="THEME_OPTIONS" label="Appearance" @update:model-value="setScheme" />
        </div>
        <div>
          <span class="mb-1.5 block text-sm font-medium text-ink">Week starts on</span>
          <SegmentedControl v-model="weekStart" label="Week starts on" :options="[{ value: 'Monday', label: 'Monday' }, { value: 'Sunday', label: 'Sunday' }]" @update:model-value="(v) => save('week_start', v)" />
        </div>
        <SelectField v-model="defaultAccount" label="Default account for new entries" :options="accountOptions" @update:model-value="(v) => v && save('default_account', v)" />
        <p class="-mt-2 text-[13px] text-ink-muted">Quick Add uses the account you used last; this is the fallback.</p>
      </div>
    </section>

    <BankAlertsSettings />

    <section class="mb-6 overflow-hidden rounded-card bg-card ring-1 ring-line/60" aria-labelledby="data-h">
      <h2 id="data-h" class="px-4 pt-4 text-[15px] font-semibold text-ink sm:px-5">Your data</h2>
      <a :href="ioApi.exportUrl()" class="flex h-14 items-center gap-3 border-b border-line/60 px-4 text-[15px] text-ink hover:bg-ink/[0.03] sm:px-5" download>
        <AppIcon name="download" class="size-5 text-ink-muted" />
        <span class="flex-1">Export all transactions (CSV)</span>
      </a>
      <button type="button" class="flex h-14 w-full items-center gap-3 px-4 text-left text-[15px] text-ink hover:bg-ink/[0.03] sm:px-5" @click="importOpen = true">
        <AppIcon name="upload" class="size-5 text-ink-muted" />
        <span class="flex-1">Import transactions from CSV</span>
        <AppIcon name="chevron-right" class="size-4 text-ink-faint" />
      </button>
    </section>

    <section class="mb-6 rounded-card bg-card p-4 ring-1 ring-line/60 sm:p-5" aria-labelledby="device-h">
      <h2 id="device-h" class="mb-2 text-[15px] font-semibold text-ink">This device</h2>
      <p class="text-sm text-ink-muted">
        <template v-if="sync.storageError">{{ sync.storageError }}</template>
        <template v-else-if="sync.items.length">{{ sync.items.length }} {{ sync.items.length === 1 ? 'change' : 'changes' }} waiting to sync.</template>
        <template v-else>Everything is synced.</template>
        <template v-if="sync.lastSyncAt"> Last synced {{ new Date(sync.lastSyncAt).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' }) }}.</template>
      </p>
      <div class="mt-3 flex flex-wrap gap-2">
        <button type="button" class="h-9 rounded-full px-4 text-sm font-medium text-ink ring-1 ring-line disabled:opacity-50" :disabled="!sync.online || !sync.items.length" @click="sync.sync()">Sync now</button>
        <button type="button" class="h-9 rounded-full px-4 text-sm font-medium text-expense ring-1 ring-line" @click="clearDevice">Clear offline data</button>
      </div>
      <div class="mt-4 overflow-hidden rounded-tile ring-1 ring-line/60"><InstallAppButton variant="row" /></div>
    </section>

    <p class="text-center text-xs text-ink-faint">Expense Tracker {{ version }}. Amounts in Indian rupees (₹).</p>

    <ResponsiveSheet v-model:open="importOpen" title="Import transactions" size="2xl">
      <ImportWizard v-if="importOpen" @done="importOpen = false" />
    </ResponsiveSheet>
  </div>
</template>
