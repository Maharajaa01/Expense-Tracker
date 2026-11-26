<script setup lang="ts">
/** Card around a chart with an accessible "Show as table" alternative. */
import { ref } from 'vue'
import AppIcon from '@/components/ui/AppIcon.vue'

defineProps<{ title: string; subtitle?: string; tableAvailable?: boolean }>()
const showTable = ref(false)
</script>

<template>
  <section class="min-w-0 rounded-card bg-card p-4 ring-1 ring-line/60 sm:p-5">
    <header class="mb-3 flex items-start justify-between gap-3">
      <div>
        <h2 class="text-[15px] font-semibold text-ink">{{ title }}</h2>
        <p v-if="subtitle" class="mt-0.5 text-[13px] text-ink-muted">{{ subtitle }}</p>
      </div>
      <button
        v-if="tableAvailable"
        type="button"
        class="inline-flex shrink-0 items-center gap-1 rounded-full px-2.5 py-1 text-[12.5px] font-medium text-ink-muted ring-1 ring-line hover:text-ink"
        :aria-pressed="showTable"
        @click="showTable = !showTable"
      >
        <AppIcon :name="showTable ? 'chart-column' : 'inbox'" class="size-3.5" />
        {{ showTable ? 'Chart' : 'Table' }}
      </button>
    </header>
    <slot name="legend" />
    <div v-if="showTable" class="max-h-72 overflow-auto"><slot name="table" /></div>
    <slot v-else />
  </section>
</template>
