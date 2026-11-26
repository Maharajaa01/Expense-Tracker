<script setup lang="ts">
/**
 * Large amount entry. Mobile gets the decimal keypad (inputmode=decimal);
 * input is sanitised as typed (digits, one point, two decimals).
 */
import { computed, nextTick, onMounted, ref } from 'vue'
import { sanitizeAmountInput } from '@/utils/money'

const props = withDefaults(
  defineProps<{ tone?: 'expense' | 'income' | 'brand'; autofocus?: boolean; error?: string | null; label?: string }>(),
  { tone: 'expense', autofocus: false, error: null, label: 'Amount' },
)
const model = defineModel<string>({ required: true })
const el = ref<HTMLInputElement>()

function onInput(e: Event) {
  const input = e.target as HTMLInputElement
  const clean = sanitizeAmountInput(input.value)
  model.value = clean
  if (input.value !== clean) input.value = clean
}

// Indian grouping preview while typing, e.g. 123456.5 → 1,23,456.5
const grouped = computed(() => {
  if (!model.value) return ''
  const [i, f] = model.value.split('.')
  const int = Number(i || 0).toLocaleString('en-IN')
  return f !== undefined ? `${int}.${f}` : int
})

onMounted(() => {
  if (props.autofocus) nextTick(() => el.value?.focus())
})
defineExpose({ focus: () => el.value?.focus() })
</script>

<template>
  <div>
    <label class="relative flex items-baseline justify-center gap-1" :class="{
      expense: 'text-expense', income: 'text-income', brand: 'text-brand-ink',
    }[tone]">
      <span class="sr-only">{{ label }}</span>
      <span class="text-3xl font-medium opacity-70" aria-hidden="true">₹</span>
      <span class="relative inline-grid">
        <!-- Mirror sizes the input to its content. -->
        <span class="invisible col-start-1 row-start-1 whitespace-pre px-1 text-5xl font-bold tracking-tight tabular" aria-hidden="true">{{ grouped || '0' }}</span>
        <input
          ref="el"
          size="1"
          :value="model"
          inputmode="decimal"
          autocomplete="off"
          enterkeyhint="done"
          placeholder="0"
          :aria-invalid="!!error"
          :aria-describedby="error ? 'amount-error' : undefined"
          class="col-start-1 row-start-1 w-full min-w-[1ch] border-0 bg-transparent p-0 px-1 text-left text-5xl font-bold tracking-tight tabular text-transparent caret-current outline-none placeholder:text-ink-faint/60 focus:ring-0"
          @input="onInput"
        />
        <span class="pointer-events-none col-start-1 row-start-1 whitespace-pre px-1 text-left text-5xl font-bold tracking-tight tabular" aria-hidden="true">{{ grouped }}</span>
      </span>
    </label>
    <p v-if="error" id="amount-error" class="mt-2 text-center text-sm text-expense" role="alert">{{ error }}</p>
  </div>
</template>
