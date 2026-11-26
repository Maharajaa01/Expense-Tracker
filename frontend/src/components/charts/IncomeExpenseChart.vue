<script setup lang="ts">
/** Income vs spending per bucket: grouped columns, income always first (left). */
import { computed } from 'vue'
import type { SeriesPoint } from '@/types/finance'
import { formatMoney } from '@/utils/money'
import ChartPanel from './ChartPanel.vue'
import EChart from './EChart.vue'
import type { ChartTheme } from './chartTheme'
import { tooltipBase } from './chartTheme'
import { axisLabel, axisMoney, bucketLabel, swatchRow, type Grain } from './format'

const props = withDefaults(defineProps<{ points: SeriesPoint[]; grain?: Grain; title?: string; subtitle?: string }>(), {
  grain: 'month',
  title: 'Income and spending',
})

const empty = computed(() => props.points.every((p) => !p.income && !p.expense))

function option(t: ChartTheme) {
  const bar = (name: string, key: 'income' | 'expense', color: string) => ({
    name,
    type: 'bar',
    data: props.points.map((p) => p[key]),
    barMaxWidth: 24,
    barGap: '12%',
    itemStyle: { color, borderRadius: [4, 4, 0, 0] },
    emphasis: { focus: 'none' },
  })
  return {
    animationDuration: 400,
    grid: { left: 4, right: 4, top: 8, bottom: 4, containLabel: true },
    tooltip: {
      ...tooltipBase(t),
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: t.dark ? 'rgba(255,255,255,0.04)' : 'rgba(15,23,42,0.04)' } },
      formatter: (items: any[]) => {
        const p = props.points[items[0].dataIndex]
        return `<div style="font-weight:600;margin-bottom:2px">${bucketLabel(p.period, props.grain)}</div>` +
          swatchRow(t.income, 'Income', formatMoney(p.income)) +
          swatchRow(t.expense, 'Spent', formatMoney(p.expense)) +
          `<div style="color:${t.muted};margin-top:2px">Saved ${formatMoney(p.income - p.expense)}</div>`
      },
    },
    xAxis: {
      type: 'category',
      data: props.points.map((p) => axisLabel(p.period, props.grain)),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: t.grid } },
      axisLabel: { color: t.axis, fontSize: 12 },
    },
    yAxis: {
      type: 'value',
      splitNumber: 4,
      axisLabel: { color: t.axis, fontSize: 11, formatter: axisMoney },
      splitLine: { lineStyle: { color: t.grid, width: 1 } },
    },
    series: [bar('Income', 'income', t.income), bar('Spent', 'expense', t.expense)],
  }
}
</script>

<template>
  <ChartPanel :title="title" :subtitle="subtitle" table-available>
    <template #legend>
      <ul class="mb-2 flex gap-4 text-[13px] text-ink-muted" aria-label="Legend">
        <li class="flex items-center gap-1.5"><span class="size-2.5 rounded-[3px]" style="background: var(--et-chart-income)" />Income</li>
        <li class="flex items-center gap-1.5"><span class="size-2.5 rounded-[3px]" style="background: var(--et-chart-expense)" />Spent</li>
      </ul>
    </template>
    <p v-if="empty" class="py-16 text-center text-sm text-ink-muted">No income or spending in this period yet.</p>
    <EChart v-else :option="option" :height="220" :label="`${title}: bar chart comparing income and spending`" />
    <template #table>
      <table class="w-full text-sm">
        <thead class="sticky top-0 bg-card text-left text-ink-muted">
          <tr><th class="py-1.5 font-medium">Period</th><th class="py-1.5 text-right font-medium">Income</th><th class="py-1.5 text-right font-medium">Spent</th><th class="py-1.5 text-right font-medium">Saved</th></tr>
        </thead>
        <tbody class="tabular">
          <tr v-for="p in points" :key="p.period" class="border-t border-line/60 text-ink">
            <td class="py-1.5">{{ bucketLabel(p.period, grain) }}</td>
            <td class="py-1.5 text-right">{{ formatMoney(p.income) }}</td>
            <td class="py-1.5 text-right">{{ formatMoney(p.expense) }}</td>
            <td class="py-1.5 text-right">{{ formatMoney(p.income - p.expense) }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </ChartPanel>
</template>
