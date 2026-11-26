<script setup lang="ts">
withDefaults(defineProps<{ rows?: number }>(), { rows: 4 })
</script>

<template>
  <div aria-busy="true" aria-label="Loading" class="divide-y divide-line/60">
    <div v-for="i in rows" :key="i" class="flex items-center gap-3 py-3">
      <div class="size-10 animate-pulse rounded-tile bg-ink/[0.07]" />
      <div class="flex-1 space-y-2">
        <div class="h-3.5 w-1/3 animate-pulse rounded bg-ink/[0.07]" />
        <div class="h-3 w-1/4 animate-pulse rounded bg-ink/[0.05]" />
      </div>
      <div class="h-4 w-16 animate-pulse rounded bg-ink/[0.07]" />
    </div>
  </div>
</template>
