<script setup lang="ts">
import { computed, ref } from 'vue'
import { toast } from 'frappe-ui'
import AmountInput from '@/components/ui/AmountInput.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import ColorPicker from '@/components/ui/ColorPicker.vue'
import IconPicker from '@/components/ui/IconPicker.vue'
import SelectField from '@/components/ui/SelectField.vue'
import { ApiError } from '@/services/api'
import { goalsApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import type { Goal } from '@/types/finance'
import { todayISO } from '@/utils/date'
import { parseAmount } from '@/utils/money'

const props = defineProps<{ goal?: Goal | null }>()
const emit = defineEmits<{ saved: [g: Goal]; cancel: [] }>()
const finance = useFinanceStore()
const g = props.goal

const name = ref(g?.goal_name ?? '')
const target = ref(g ? String(g.target_amount) : '')
const targetDate = ref(g?.target_date ?? '')
const linked = ref(g?.linked_account ?? '')
const icon = ref(g?.icon ?? 'piggy-bank')
const color = ref(g?.color ?? '#0d9488')
const saving = ref(false)
const error = ref<string | null>(null)
const lockedAccount = computed(() => !!g?.contributions.some((c) => c.transaction))
const accountOptions = computed(() => finance.activeAccounts.map((a) => ({ value: a.name, label: a.account_name })))
const suggestions = ['Emergency fund', 'New bike', 'Vacation', 'New laptop', 'House']

async function save() {
  if (saving.value) return
  const value = parseAmount(target.value)
  if (!name.value.trim() || value === null) {
    error.value = !name.value.trim() ? 'Give the goal a name.' : 'Enter how much you want to save.'
    return
  }
  saving.value = true
  error.value = null
  try {
    const data: Partial<Goal> = {
      goal_name: name.value.trim(), target_amount: value, target_date: targetDate.value || null,
      linked_account: linked.value || null, icon: icon.value, color: color.value,
      ...(g ? {} : { start_date: todayISO() }),
    }
    const saved = g ? await goalsApi.update(g.name, data) : await goalsApi.create(data)
    toast.success(g ? 'Goal updated' : 'Goal created')
    finance.dataVersion++
    emit('saved', saved)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Could not save the goal.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <form class="space-y-5 pt-1" novalidate @submit.prevent="save">
    <div class="flex items-center gap-3">
      <CategoryIcon :icon="icon" :color="color" size="lg" />
      <label class="flex-1">
        <span class="mb-1.5 block text-sm font-medium text-ink">What are you saving for?</span>
        <input v-model="name" maxlength="100" placeholder="e.g. New bike" class="h-11 w-full rounded-tile border-0 bg-card px-3 text-[15px] text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" />
      </label>
    </div>
    <div v-if="!g && !name" class="-mt-2 flex flex-wrap gap-1.5">
      <button v-for="s in suggestions" :key="s" type="button" class="h-8 rounded-full px-3 text-[13px] text-ink-muted ring-1 ring-line hover:text-ink" @click="name = s">{{ s }}</button>
    </div>
    <section class="rounded-tile bg-ink/[0.03] p-4 ring-1 ring-line/60">
      <h3 class="text-center text-sm font-medium text-ink">Target amount</h3>
      <AmountInput v-model="target" tone="brand" label="Target amount" class="py-2" />
    </section>
    <label class="block text-sm">
      <span class="mb-1.5 block font-medium text-ink">Target date <span class="font-normal text-ink-faint">(optional)</span></span>
      <input v-model="targetDate" type="date" :min="todayISO()" class="h-10 w-full rounded-[10px] border-0 bg-card px-3 text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" />
    </label>
    <div>
      <SelectField v-model="linked" label="Keep the money in" :options="accountOptions" placeholder="No specific account (just track it)" />
      <p class="mt-1 text-[13px] text-ink-muted">
        <template v-if="lockedAccount">This goal already has transfers, so its account can't change.</template>
        <template v-else>With an account, adding money moves it there as a transfer. Without one, contributions are only tracked.</template>
      </p>
    </div>
    <div class="grid gap-5 sm:grid-cols-2">
      <IconPicker v-model="icon" set="goal" :color="color" />
      <ColorPicker v-model="color" />
    </div>
    <p v-if="error" role="alert" class="rounded-tile bg-expense-soft/60 p-3 text-sm text-ink">{{ error }}</p>
    <div class="flex gap-2">
      <button type="button" class="h-12 rounded-full px-5 font-medium text-ink-muted hover:bg-ink/[0.05]" @click="emit('cancel')">Cancel</button>
      <button type="submit" class="flex h-12 flex-1 items-center justify-center gap-2 rounded-full bg-brand-solid font-semibold text-white disabled:opacity-70" :disabled="saving">
        <AppIcon v-if="saving" name="refresh-cw" class="size-5 animate-spin" /> {{ g ? 'Save changes' : 'Create goal' }}
      </button>
    </div>
  </form>
</template>
