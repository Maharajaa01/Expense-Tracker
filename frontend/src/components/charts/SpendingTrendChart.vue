<script setup lang="ts">
/** Spending per day/week/month for the chosen period. Single series: no legend box. */
import { computed } from 'vue'
import type { SeriesPoint } from '@/types/finance'
import { formatMoney } from '@/utils/money'
import ChartPanel from './ChartPanel.vue'
import EChart from './EChart.vue'
import { tooltipBase, type ChartTheme } from './chartTheme'
import { axisLabel, axisMoney, bucketLabel, type Grain } from './format'

const props = defineProps<{ points: SeriesPoint[]; grain: Grain; subtitle?: string }>()
const empty = computed(() => props.points.every((p) => !p.expense))
const title = computed(() => ({ day: 'Daily spending', week: 'Weekly spending', month: 'Monthly spending' })[props.grain])
const peak = computed(() => props.points.reduce((m, p, i, a) => (p.expense > a[m].expense ? i : m), 0))

function option(t: ChartTheme) {
  return {
    animationDuration: 400,
    grid: { left: 4, right: 4, top: 22, bottom: 4, containLabel: true },
    tooltip: {
      ...tooltipBase(t),
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: t.dark ? 'rgba(255,255,255,0.04)' : 'rgba(15,23,42,0.04)' } },
      formatter: (items: any[]) => {
        const p = props.points[items[0].dataIndex]
        return `<div style="font-weight:600">${bucketLabel(p.period, props.grain)}</div><div style="font-variant-numeric:tabular-nums">${formatMoney(p.expense)} spent</div>`
      },
    },
    xAxis: {
      type: 'category',
      data: props.points.map((p) => axisLabel(p.period, props.grain)),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: t.grid } },
      axisLabel: { color: t.axis, fontSize: 11, hideOverlap: true },
    },
    yAxis: {
      type: 'value',
      splitNumber: 3,
      axisLabel: { color: t.axis, fontSize: 11, formatter: axisMoney },
      splitLine: { lineStyle: { color: t.grid, width: 1 } },
    },
    series: [
      {
        name: 'Spent',
        type: 'bar',
        barMaxWidth: 24,
        data: props.points.map((p, i) => ({
          value: p.expense,
          // Label only the peak (selective labelling).
          label: i === peak.value && p.expense > 0
            ? { show: true, position: 'top', color: t.muted, fontSize: 11, formatter: () => formatMoney(p.expense, { compact: true }) }
            : undefined,
        })),
        itemStyle: { color: t.expense, borderRadius: [4, 4, 0, 0] },
      },
    ],
  }
}
</script>

<template>
  <ChartPanel :title="title" :subtitle="subtitle" table-available>
    <p v-if="empty" class="py-16 text-center text-sm text-ink-muted">No spending in this period yet.</p>
    <EChart v-else :option="option" :height="220" :label="`${title}, bar chart`" />
    <template #table>
      <table class="w-full text-sm">
        <thead class="sticky top-0 bg-card text-left text-ink-muted">
          <tr><th class="py-1.5 font-medium">Period</th><th class="py-1.5 text-right font-medium">Spent</th></tr>
        </thead>
        <tbody class="tabular">
          <tr v-for="p in points" :key="p.period" class="border-t border-line/60 text-ink">
            <td class="py-1.5">{{ bucketLabel(p.period, grain) }}</td>
            <td class="py-1.5 text-right">{{ formatMoney(p.expense) }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </ChartPanel>
</template>
