<script setup lang="ts">
/**
 * The app's signature typographic element: every amount is set the same way,
 * from list rows to the balance hero. Tabular figures, a raised smaller ₹,
 * and lighter paise.
 */
import { computed } from 'vue'
import { formatMoney, moneyParts } from '@/utils/money'

const props = withDefaults(
  defineProps<{
    value: number
    /** Colour by meaning. `inherit` takes the parent's colour. */
    tone?: 'inherit' | 'income' | 'expense' | 'muted' | 'auto'
    /** `auto`: show "−" for negatives only. `always`: "+"/"−". */
    sign?: 'auto' | 'always' | 'none'
    size?: 'sm' | 'md' | 'lg' | 'xl' | 'hero'
    hideFraction?: boolean
  }>(),
  { tone: 'inherit', sign: 'auto', size: 'md', hideFraction: false },
)

const p = computed(() => moneyParts(props.value))
const signChar = computed(() => {
  if (props.sign === 'none') return ''
  if (p.value.negative) return '−'
  if (props.sign === 'always' && props.value > 0) return '+'
  return ''
})
const toneClass = computed(() => {
  const t = props.tone === 'auto' ? (props.value < 0 ? 'expense' : 'inherit') : props.tone
  return { inherit: '', income: 'text-income', expense: 'text-expense', muted: 'text-ink-muted' }[t]
})
const sizeClass = computed(
  () =>
    ({
      sm: 'text-sm font-medium',
      md: 'text-base font-semibold',
      lg: 'text-xl font-semibold tracking-tight',
      xl: 'text-3xl font-bold tracking-tight',
      hero: 'text-[2.75rem] leading-none font-bold tracking-[-0.03em] sm:text-[3.5rem]',
    })[props.size],
)
const big = computed(() => props.size === 'lg' || props.size === 'xl' || props.size === 'hero')
const label = computed(() => formatMoney(props.value, { signed: props.sign === 'always' }))
</script>

<template>
  <span class="et-money whitespace-nowrap" :class="[toneClass, sizeClass]" :aria-label="label">
    <span aria-hidden="true">{{ signChar }}</span><span
      aria-hidden="true"
      class="et-money-symbol"
      :class="big ? 'et-money-symbol--raised mr-1' : 'mr-px'"
    >{{ p.symbol }}</span><span aria-hidden="true">{{ p.integer }}</span><span
      v-if="!hideFraction"
      aria-hidden="true"
      class="et-money-fraction"
    >.{{ p.fraction }}</span>
  </span>
</template>

<style scoped>
.et-money {
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum', 'cv11';
}
/* Small sizes: symbol stays on the baseline so list amounts stay legible. */
.et-money-symbol {
  font-size: 0.9em;
  font-weight: 500;
  opacity: 0.85;
}
/* Display sizes: smaller, raised ₹ – the app's signature amount setting. */
.et-money-symbol--raised {
  font-size: 0.55em;
  vertical-align: 0.5em;
  opacity: 0.8;
}
.et-money-fraction {
  font-size: 0.62em;
  font-weight: 500;
  opacity: 0.7;
}
</style>
