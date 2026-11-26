<script setup lang="ts">
/**
 * Spending by category: donut + labelled list. Identity never relies on
 * colour alone (each slice has a named, iconed row). Beyond 6 categories the
 * tail folds into "Other" rather than inventing more colours.
 */
import { computed } from 'vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import Money from '@/components/ui/Money.vue'
import type { CategoryTotal } from '@/types/finance'
import { formatMoney } from '@/utils/money'
import ChartPanel from './ChartPanel.vue'
import EChart from './EChart.vue'
import { tooltipBase, type ChartTheme } from './chartTheme'
import { esc } from './format'

const props = withDefaults(defineProps<{ categories: CategoryTotal[]; total: number; subtitle?: string; max?: number }>(), { max: 6 })
const emit = defineEmits<{ select: [category: string] }>()

const positive = computed(() => props.categories.filter((c) => c.amount > 0))
const slices = computed(() => {
  const list = positive.value
  if (list.length <= props.max) return list.map((c) => ({ ...c, other: false }))
  const head = list.slice(0, props.max - 1)
  const tail = list.slice(props.max - 1)
  const amount = tail.reduce((s, c) => s + c.amount, 0)
  return [
    ...head.map((c) => ({ ...c, other: false })),
    {
      category: '__other__', category_name: `Other (${tail.length})`, icon: 'circle-ellipsis', color: '',
      amount, count: tail.reduce((s, c) => s + c.count, 0),
      share: tail.reduce((s, c) => s + (c.share ?? 0), 0), other: true,
    },
  ]
})

function option(t: ChartTheme) {
  return {
    animationDuration: 400,
    tooltip: {
      ...tooltipBase(t),
      trigger: 'item',
      // Category names are user data: escape before putting them in tooltip HTML.
      formatter: (p: any) => `<b>${esc(String(p.name))}</b><br/><span style="font-variant-numeric:tabular-nums">${formatMoney(p.value)}</span> (${p.percent}%)`,
    },
    series: [
      {
        type: 'pie',
        radius: ['62%', '92%'],
        avoidLabelOverlap: true,
        label: { show: false },
        itemStyle: { borderColor: t.surface, borderWidth: 2, borderRadius: 4 },
        emphasis: { scale: true, scaleSize: 4 },
        data: slices.value.map((s) => ({ name: s.category_name, value: s.amount, itemStyle: { color: s.other ? t.other : s.color } })),
      },
    ],
  }
}
</script>

<template>
  <ChartPanel title="Spending by category" :subtitle="subtitle">
    <p v-if="!positive.length" class="py-16 text-center text-sm text-ink-muted">No spending in this period yet.</p>
    <div v-else class="flex flex-col items-center gap-4">
      <div class="relative w-44 shrink-0">
        <EChart :option="option" :height="176" label="Spending by category, donut chart" />
        <div class="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span class="text-xs text-ink-muted">Spent</span>
          <Money :value="total" size="md" hide-fraction class="text-ink" />
        </div>
      </div>
      <ul class="w-full min-w-0 flex-1 space-y-1">
        <li v-for="s in slices" :key="s.category">
          <button
            type="button"
            class="flex w-full items-center gap-3 rounded-tile px-1.5 py-1.5 text-left hover:bg-ink/[0.03] disabled:cursor-default disabled:hover:bg-transparent"
            :disabled="s.other"
            @click="emit('select', s.category)"
          >
            <CategoryIcon :icon="s.icon" :color="s.other ? 'var(--et-chart-other)' : s.color" size="sm" />
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm font-medium text-ink">{{ s.category_name }}</span>
              <span class="block text-xs text-ink-muted">{{ s.share !== null ? `${Math.round(s.share)}% of spending, ` : '' }}{{ s.count }} {{ s.count === 1 ? 'entry' : 'entries' }}</span>
            </span>
            <Money :value="s.amount" size="sm" class="text-ink" />
          </button>
        </li>
      </ul>
    </div>
  </ChartPanel>
</template>
