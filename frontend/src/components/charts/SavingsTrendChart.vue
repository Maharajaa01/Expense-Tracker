<script setup lang="ts">
/**
 * Monthly savings (income − spending). Polarity encoding: teal above zero
 * (saved), coral below (overspent). The sign and the tooltip carry the same
 * information, so colour is never the only cue.
 */
import { computed } from 'vue'
import type { SavingsPoint } from '@/types/finance'
import { formatMoney } from '@/utils/money'
import ChartPanel from './ChartPanel.vue'
import EChart from './EChart.vue'
import { tooltipBase, type ChartTheme } from './chartTheme'
import { axisLabel, axisMoney, bucketLabel } from './format'

const props = defineProps<{ points: SavingsPoint[] }>()
const empty = computed(() => props.points.every((p) => !p.income && !p.expense))

function option(t: ChartTheme) {
  return {
    animationDuration: 400,
    grid: { left: 4, right: 4, top: 8, bottom: 4, containLabel: true },
    tooltip: {
      ...tooltipBase(t),
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: t.dark ? 'rgba(255,255,255,0.04)' : 'rgba(15,23,42,0.04)' } },
      formatter: (items: any[]) => {
        const p = props.points[items[0].dataIndex]
        const rate = p.rate === null ? 'no income' : `${p.rate}% of income`
        return `<div style="font-weight:600">${bucketLabel(p.period, 'month')}</div><div style="font-variant-numeric:tabular-nums">${p.savings >= 0 ? 'Saved' : 'Overspent'} ${formatMoney(Math.abs(p.savings))} (${rate})</div>`
      },
    },
    xAxis: { type: 'category', data: props.points.map((p) => axisLabel(p.period, 'month')), axisTick: { show: false }, axisLine: { lineStyle: { color: t.grid } }, axisLabel: { color: t.axis, fontSize: 11 } },
    yAxis: { type: 'value', splitNumber: 3, axisLabel: { color: t.axis, fontSize: 11, formatter: axisMoney }, splitLine: { lineStyle: { color: t.grid } } },
    series: [{
      type: 'bar',
      barMaxWidth: 24,
      data: props.points.map((p) => ({
        value: p.savings,
        itemStyle: { color: p.savings >= 0 ? t.savings : t.expense, borderRadius: p.savings >= 0 ? [4, 4, 0, 0] : [0, 0, 4, 4] },
      })),
    }],
  }
}
</script>

<template>
  <ChartPanel title="Savings trend" subtitle="What you kept each month, last 12 months" table-available>
    <template #legend>
      <ul class="mb-2 flex gap-4 text-[13px] text-ink-muted" aria-label="Legend">
        <li class="flex items-center gap-1.5"><span class="size-2.5 rounded-[3px] bg-savings" />Saved</li>
        <li class="flex items-center gap-1.5"><span class="size-2.5 rounded-[3px]" style="background: var(--et-chart-expense)" />Overspent</li>
      </ul>
    </template>
    <p v-if="empty" class="py-16 text-center text-sm text-ink-muted">No income or spending in the last 12 months.</p>
    <EChart v-else :option="option" :height="220" label="Savings per month over the last 12 months, bar chart" />
    <template #table>
      <table class="w-full text-sm">
        <thead class="sticky top-0 bg-card text-left text-ink-muted"><tr><th class="py-1.5 font-medium">Month</th><th class="py-1.5 text-right font-medium">Saved</th><th class="py-1.5 text-right font-medium">Rate</th></tr></thead>
        <tbody class="tabular"><tr v-for="p in points" :key="p.period" class="border-t border-line/60 text-ink"><td class="py-1.5">{{ bucketLabel(p.period, 'month') }}</td><td class="py-1.5 text-right">{{ formatMoney(p.savings) }}</td><td class="py-1.5 text-right">{{ p.rate === null ? '—' : `${p.rate}%` }}</td></tr></tbody>
      </table>
    </template>
  </ChartPanel>
</template>
