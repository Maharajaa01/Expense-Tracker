<script setup lang="ts">
/** Spending per month as a line (single series: no legend box). */
import { computed } from 'vue'
import type { SeriesPoint } from '@/types/finance'
import { formatMoney } from '@/utils/money'
import ChartPanel from './ChartPanel.vue'
import EChart from './EChart.vue'
import { tooltipBase, type ChartTheme } from './chartTheme'
import { axisLabel, axisMoney, bucketLabel } from './format'

const props = defineProps<{ points: SeriesPoint[] }>()
const empty = computed(() => props.points.every((p) => !p.expense))
const last = computed(() => props.points.length - 1)

function option(t: ChartTheme) {
  return {
    animationDuration: 400,
    grid: { left: 4, right: 12, top: 22, bottom: 4, containLabel: true },
    tooltip: {
      ...tooltipBase(t),
      trigger: 'axis',
      axisPointer: { type: 'line', lineStyle: { color: t.grid } },
      formatter: (items: any[]) => {
        const p = props.points[items[0].dataIndex]
        return `<div style="font-weight:600">${bucketLabel(p.period, 'month')}</div><div style="font-variant-numeric:tabular-nums">${formatMoney(p.expense)} spent</div>`
      },
    },
    xAxis: { type: 'category', boundaryGap: false, data: props.points.map((p) => axisLabel(p.period, 'month')), axisTick: { show: false }, axisLine: { lineStyle: { color: t.grid } }, axisLabel: { color: t.axis, fontSize: 11 } },
    yAxis: { type: 'value', splitNumber: 3, axisLabel: { color: t.axis, fontSize: 11, formatter: axisMoney }, splitLine: { lineStyle: { color: t.grid } } },
    series: [{
      type: 'line',
      data: props.points.map((p, i) => ({
        value: p.expense,
        label: i === last.value ? { show: true, position: 'top', color: t.muted, fontSize: 11, formatter: () => formatMoney(p.expense, { compact: true }) } : undefined,
      })),
      lineStyle: { width: 2, color: t.expense, cap: 'round', join: 'round' },
      itemStyle: { color: t.expense, borderColor: t.surface, borderWidth: 2 },
      symbol: 'circle',
      symbolSize: 8,
      areaStyle: { color: t.expense, opacity: 0.1 },
    }],
  }
}
</script>

<template>
  <ChartPanel title="Monthly spending" subtitle="Last 12 months" table-available>
    <p v-if="empty" class="py-16 text-center text-sm text-ink-muted">No spending recorded in the last 12 months.</p>
    <EChart v-else :option="option" :height="220" label="Monthly spending over the last 12 months, line chart" />
    <template #table>
      <table class="w-full text-sm">
        <thead class="sticky top-0 bg-card text-left text-ink-muted"><tr><th class="py-1.5 font-medium">Month</th><th class="py-1.5 text-right font-medium">Spent</th></tr></thead>
        <tbody class="tabular"><tr v-for="p in points" :key="p.period" class="border-t border-line/60 text-ink"><td class="py-1.5">{{ bucketLabel(p.period, 'month') }}</td><td class="py-1.5 text-right">{{ formatMoney(p.expense) }}</td></tr></tbody>
      </table>
    </template>
  </ChartPanel>
</template>
