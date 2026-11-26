<script setup lang="ts">
import AppIcon from './AppIcon.vue'

defineProps<{ icon: string; title: string; message?: string }>()
</script>

<template>
  <div class="flex flex-col items-center px-6 py-10 text-center">
    <span class="mb-3 inline-flex size-12 items-center justify-center rounded-full bg-brand-soft text-brand-ink">
      <AppIcon :name="icon" class="size-6" />
    </span>
    <h3 class="text-base font-semibold text-ink">{{ title }}</h3>
    <p v-if="message" class="mt-1 max-w-xs text-sm text-ink-muted">{{ message }}</p>
    <div v-if="$slots.default" class="mt-4"><slot /></div>
  </div>
</template>
