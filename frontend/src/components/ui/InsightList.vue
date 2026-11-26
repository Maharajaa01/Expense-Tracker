<script setup lang="ts">
import AppIcon from './AppIcon.vue'
import type { Insight } from '@/types/finance'

defineProps<{ insights: Insight[]; title?: string }>()
</script>

<template>
  <section v-if="insights.length" class="rounded-card bg-card p-4 ring-1 ring-line/60 sm:p-5" aria-label="Insights">
    <h2 class="mb-3 text-[15px] font-semibold text-ink">{{ title ?? 'Insights' }}</h2>
    <ul class="space-y-2.5">
      <li v-for="i in insights" :key="i.kind" class="flex items-start gap-3 text-sm text-ink">
        <span
          class="inline-flex size-8 shrink-0 items-center justify-center rounded-full"
          :class="{ good: 'bg-savings-soft text-savings', warning: 'bg-warn-soft text-warn', neutral: 'bg-accent-soft text-accent' }[i.tone]"
        >
          <AppIcon :name="i.icon" class="size-4" />
        </span>
        <span class="pt-1.5">{{ i.text }}</span>
      </li>
    </ul>
  </section>
</template>
