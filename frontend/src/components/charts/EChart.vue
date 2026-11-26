<script setup lang="ts">
/**
 * Minimal ECharts host. Registers only the modules this app draws (bar, line,
 * pie, grid, tooltip) with the SVG renderer, so the chart chunk stays small on
 * slow mobile connections. The option builder receives the resolved theme so
 * the chart repaints when light/dark changes.
 */
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useResolvedColorScheme } from 'frappe-ui'
import { init, use, type ECharts, type EChartsCoreOption } from 'echarts/core'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { SVGRenderer } from 'echarts/renderers'
import { readChartTheme, type ChartTheme } from './chartTheme'

use([BarChart, LineChart, PieChart, GridComponent, TooltipComponent, SVGRenderer])

const props = withDefaults(
  defineProps<{ option: (t: ChartTheme) => EChartsCoreOption; height?: number; label: string }>(),
  { height: 240 },
)

const container = ref<HTMLElement>()
const chart = shallowRef<ECharts>()
const scheme = useResolvedColorScheme()
const theme = computed(() => readChartTheme(scheme.value === 'dark'))
const reducedMotion = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

function render() {
  if (!chart.value) return
  const opt = props.option(theme.value) as Record<string, unknown>
  chart.value.setOption(reducedMotion ? { ...opt, animation: false } : opt, { notMerge: true })
}

let observer: ResizeObserver | undefined
onMounted(async () => {
  // Measure labels with the real web font, not the fallback.
  await Promise.race([document.fonts?.ready, new Promise((r) => setTimeout(r, 1500))])
  if (!container.value) return
  chart.value = init(container.value, undefined, { renderer: 'svg' })
  render()
  observer = new ResizeObserver(() => chart.value?.resize({ animation: { duration: reducedMotion ? 0 : 200 } }))
  observer.observe(container.value)
})
watch([theme, () => props.option], render)
onBeforeUnmount(() => {
  observer?.disconnect()
  chart.value?.dispose()
})
</script>

<template>
  <div ref="container" role="img" class="w-full min-w-0 overflow-hidden" :aria-label="label" :style="{ height: `${height}px` }" />
</template>
