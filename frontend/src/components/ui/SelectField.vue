<script setup lang="ts">
/** Native <select> (best on mobile) styled to match the app. */
import AppIcon from './AppIcon.vue'

defineProps<{ label: string; options: { value: string; label: string; group?: string }[]; hideLabel?: boolean; placeholder?: string }>()
const model = defineModel<string>({ required: true })
</script>

<template>
  <label class="block">
    <span :class="hideLabel ? 'sr-only' : 'mb-1.5 block text-sm font-medium text-ink'">{{ label }}</span>
    <span class="relative block">
      <select
        v-model="model"
        class="h-10 w-full appearance-none rounded-[10px] border-0 bg-card pl-3 pr-9 text-sm text-ink ring-1 ring-line focus:ring-2 focus:ring-brand"
      >
        <option v-if="placeholder !== undefined" value="">{{ placeholder }}</option>
        <option v-for="o in options" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
      <AppIcon name="chevron-down" class="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-ink-faint" />
    </span>
  </label>
</template>
