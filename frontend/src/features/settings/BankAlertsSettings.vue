<script setup lang="ts">
/** Bank alert emails: setup guide, mailbox settings, test, check now, recent log. */
import { computed, onMounted, ref } from 'vue'
import { toast } from 'frappe-ui'
import AppIcon from '@/components/ui/AppIcon.vue'
import Money from '@/components/ui/Money.vue'
import { ApiError } from '@/services/api'
import { alertsApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import type { AlertLogRow, AlertSettings } from '@/types/finance'
import { todayISO } from '@/utils/date'

const finance = useFinanceStore()
const settings = ref<AlertSettings | null>(null)
const log = ref<AlertLogRow[]>([])
const email = ref('')
const password = ref('')
const since = ref(todayISO())
const busy = ref<'save' | 'test' | 'check' | null>(null)
const message = ref<{ ok: boolean; text: string } | null>(null)
const showGuide = ref(false)
const loadError = ref<string | null>(null)

async function load() {
  try {
    settings.value = await alertsApi.settings()
    email.value = settings.value.email ?? ''
    since.value = settings.value.since ?? todayISO()
    showGuide.value = !settings.value.email
    log.value = await alertsApi.log(30)
  } catch (e) {
    loadError.value = e instanceof ApiError ? e.message : 'Could not load bank alert settings.'
  }
}
onMounted(load)

async function run<T>(kind: 'save' | 'test' | 'check', fn: () => Promise<T>) {
  if (busy.value) return
  busy.value = kind
  message.value = null
  try {
    return await fn()
  } catch (e) {
    message.value = { ok: false, text: e instanceof ApiError ? e.message : 'Something went wrong.' }
  } finally {
    busy.value = null
  }
}

async function save(enabled?: boolean) {
  await run('save', async () => {
    settings.value = await alertsApi.save({
      email: email.value.trim(),
      ...(password.value ? { app_password: password.value } : {}),
      since: since.value,
      ...(enabled !== undefined ? { enabled: enabled ? 1 : 0 } : {}),
    })
    password.value = ''
    toast.success(enabled === undefined ? 'Saved' : enabled ? 'Bank alert emails turned on' : 'Bank alert emails turned off')
  })
}

async function test() {
  await run('test', async () => {
    if (password.value || email.value !== (settings.value?.email ?? '')) await save()
    const r = await alertsApi.test()
    message.value = r.ok
      ? { ok: true, text: `Connected. ${r.messages} ${r.messages === 1 ? 'email' : 'emails'} since ${since.value}, ${r.bank_messages} from your banks.` }
      : { ok: false, text: r.error ?? 'Could not connect.' }
  })
}

async function checkNow() {
  await run('check', async () => {
    const r = await alertsApi.checkNow()
    if (!r.ok) {
      message.value = { ok: false, text: r.error ?? 'Could not read the mailbox.' }
    } else {
      const res = r.results ?? {}
      const parts = [`${res.Posted ?? 0} added`, res['Needs Account'] ? `${res['Needs Account']} need an account` : '', res.Unrecognised ? `${res.Unrecognised} not understood` : '']
      message.value = { ok: true, text: `Checked ${r.checked} new ${r.checked === 1 ? 'email' : 'emails'}: ${parts.filter(Boolean).join(', ')}.` }
      if (res.Posted) await finance.changed()
    }
    settings.value = await alertsApi.settings()
    log.value = await alertsApi.log(30)
  })
}

const canEnable = computed(() => !!settings.value?.email && !!settings.value?.has_password)
const statusClass: Record<string, string> = {
  Posted: 'bg-brand-soft text-brand-ink', Duplicate: 'bg-ink/[0.06] text-ink-muted', Ignored: 'bg-ink/[0.06] text-ink-muted',
  'Needs Account': 'bg-warn-soft text-warn', Unrecognised: 'bg-warn-soft text-warn', Failed: 'bg-expense-soft text-expense',
}
const statusLabel: Record<string, string> = { Posted: 'Added', Duplicate: 'Already added', Ignored: 'Not a payment', 'Needs Account': 'Needs account', Unrecognised: 'Not understood', Failed: 'Failed' }
const when = (s: string | null) => (s ? new Date(s.replace(' ', 'T')).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' }) : '')
</script>

<template>
  <section class="mb-6 rounded-card bg-card p-4 ring-1 ring-line/60 sm:p-5" aria-labelledby="alerts-h">
    <div class="mb-1 flex items-center justify-between gap-3">
      <h2 id="alerts-h" class="text-[15px] font-semibold text-ink">Bank alert emails</h2>
      <span v-if="settings?.enabled" class="rounded-full bg-brand-soft px-2.5 py-0.5 text-xs font-semibold text-brand-ink">On</span>
    </div>
    <p class="text-sm text-ink-muted">
      Payments from your Karnataka Bank and Axis Bank alert emails are added automatically, so balances stay up to date.
      You only choose the category.
    </p>
    <p v-if="loadError" role="alert" class="mt-3 text-sm text-expense">{{ loadError }}</p>

    <template v-if="settings">
      <button type="button" class="mt-3 inline-flex items-center gap-1 text-sm font-medium text-brand-ink" :aria-expanded="showGuide" @click="showGuide = !showGuide">
        <AppIcon name="chevron-right" class="size-4 transition-transform" :class="{ 'rotate-90': showGuide }" /> How to set it up (10 minutes)
      </button>
      <ol v-if="showGuide" class="mt-3 list-decimal space-y-2 pl-5 text-sm text-ink">
        <li>Create a <b>new free Gmail</b> just for alerts, e.g. <i>yourname.bankalerts@gmail.com</i>. Only bank emails will ever reach it.</li>
        <li>In that new Gmail, turn on <b>2-Step Verification</b>, then create an <b>App password</b> at <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener" class="text-brand-ink underline">myaccount.google.com/apppasswords</a>. Copy the 16 letters.</li>
        <li>In your <b>personal Gmail</b>: Settings → <i>Forwarding and POP/IMAP</i> → <i>Add a forwarding address</i> → the new Gmail. Open the new Gmail and confirm the code. Keep "Disable forwarding" selected there (nothing is forwarded yet).</li>
        <li>Still in your personal Gmail, create a filter: <b>From:</b> <code class="rounded bg-ink/[0.06] px-1">axisbank.com OR ktkbank.com OR karnatakabank.com</code> → <i>Forward it to</i> the new Gmail. Only these emails are forwarded.</li>
        <li>Below, enter the new Gmail and the App password, then <b>Test connection</b> and turn it on.</li>
        <li>In <RouterLink :to="{ name: 'accounts' }" class="text-brand-ink underline">Accounts</RouterLink>, edit your Karnataka Bank and Axis Bank accounts and add the <b>last 4 digits</b> of each account number.</li>
      </ol>

      <div class="mt-4 grid gap-3 sm:grid-cols-2">
        <label class="block text-sm">
          <span class="mb-1.5 block font-medium text-ink">Alerts Gmail address</span>
          <input v-model="email" type="email" autocomplete="off" placeholder="yourname.bankalerts@gmail.com" class="h-10 w-full rounded-[10px] border-0 bg-card px-3 text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" />
        </label>
        <label class="block text-sm">
          <span class="mb-1.5 block font-medium text-ink">Google App password</span>
          <input v-model="password" type="password" autocomplete="new-password" :placeholder="settings.has_password ? 'Saved (enter a new one to replace it)' : '16 letters'" class="h-10 w-full rounded-[10px] border-0 bg-card px-3 text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" />
        </label>
        <label class="block text-sm">
          <span class="mb-1.5 block font-medium text-ink">Read emails from</span>
          <input v-model="since" type="date" class="h-10 w-full rounded-[10px] border-0 bg-card px-3 text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" />
          <span class="mt-1 block text-[13px] text-ink-muted">Earlier emails are ignored, so old payments aren't added twice.</span>
        </label>
      </div>

      <p v-if="settings.accounts_without_digits.length" class="mt-3 rounded-tile bg-warn-soft/70 p-3 text-[13px] text-ink">
        Add the last 4 digits to: {{ settings.accounts_without_digits.join(', ') }}. Alerts for accounts without them are listed below but not added.
      </p>

      <div class="mt-4 flex flex-wrap gap-2">
        <button type="button" class="h-10 rounded-full px-4 text-sm font-medium text-ink ring-1 ring-line disabled:opacity-50" :disabled="!!busy" @click="save()">
          <AppIcon v-if="busy === 'save'" name="refresh-cw" class="mr-1 inline size-4 animate-spin" />Save
        </button>
        <button type="button" class="h-10 rounded-full px-4 text-sm font-medium text-ink ring-1 ring-line disabled:opacity-50" :disabled="!!busy || !email || (!password && !settings.has_password)" @click="test">
          <AppIcon v-if="busy === 'test'" name="refresh-cw" class="mr-1 inline size-4 animate-spin" />Test connection
        </button>
        <button v-if="!settings.enabled" type="button" class="h-10 rounded-full bg-brand-solid px-4 text-sm font-semibold text-white disabled:opacity-50" :disabled="!!busy || !canEnable" @click="save(true)">Turn on</button>
        <template v-else>
          <button type="button" class="h-10 rounded-full bg-brand-solid px-4 text-sm font-semibold text-white disabled:opacity-50" :disabled="!!busy" @click="checkNow">
            <AppIcon v-if="busy === 'check'" name="refresh-cw" class="mr-1 inline size-4 animate-spin" />Check now
          </button>
          <button type="button" class="h-10 rounded-full px-4 text-sm font-medium text-expense ring-1 ring-line disabled:opacity-50" :disabled="!!busy" @click="save(false)">Turn off</button>
        </template>
      </div>
      <p v-if="message" role="status" class="mt-3 rounded-tile p-3 text-sm" :class="message.ok ? 'bg-brand-soft/60 text-ink' : 'bg-expense-soft/60 text-ink'">{{ message.text }}</p>
      <p class="mt-3 text-[13px] text-ink-muted">
        <template v-if="settings.enabled">Checked automatically every 10 minutes.</template>
        <template v-if="settings.last_checked"> Last checked {{ when(settings.last_checked) }}.</template>
        <span v-if="settings.last_error" class="block text-expense">{{ settings.last_error }}</span>
      </p>
      <p class="mt-1 text-[13px] text-ink-muted">The app only reads this mailbox (nothing is deleted or marked read) and keeps only the payment details, never your emails.</p>

      <div v-if="log.length" class="mt-5">
        <h3 class="mb-2 text-sm font-medium text-ink">Recent alerts</h3>
        <ul class="divide-y divide-line/60 rounded-tile ring-1 ring-line/60">
          <li v-for="r in log" :key="r.name" class="px-3 py-2.5 text-sm">
            <div class="flex items-center gap-2">
              <span class="shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold" :class="statusClass[r.status]">{{ statusLabel[r.status] }}</span>
              <span class="min-w-0 flex-1 truncate text-ink">{{ r.merchant || r.bank || 'Email' }}</span>
              <Money v-if="r.amount" :value="r.transaction_type === 'Income' ? r.amount : -r.amount" :sign="r.transaction_type === 'Income' ? 'always' : 'auto'" size="sm" class="text-ink" />
            </div>
            <p class="mt-0.5 text-xs text-ink-faint">{{ when(r.received_on) }}<template v-if="r.account_last4">, A/c ending {{ r.account_last4 }}</template></p>
            <p v-if="r.note" class="mt-0.5 text-[13px] text-ink-muted">{{ r.note }}</p>
            <p v-if="r.snippet" class="mt-1 rounded bg-ink/[0.04] p-2 text-xs text-ink-muted">{{ r.snippet }}</p>
          </li>
        </ul>
      </div>
    </template>
  </section>
</template>
