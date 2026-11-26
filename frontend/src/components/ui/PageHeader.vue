<script setup lang="ts">
defineProps<{ title: string; subtitle?: string }>()
</script>

<template>
  <header class="mb-5 flex flex-wrap items-end justify-between gap-3">
    <div class="min-w-0">
      <h1 class="text-2xl font-bold tracking-tight text-ink">{{ title }}</h1>
      <p v-if="subtitle" class="mt-0.5 text-sm text-ink-muted">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.actions" class="flex items-center gap-2"><slot name="actions" /></div>
  </header>
</template>
