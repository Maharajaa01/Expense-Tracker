<script setup lang="ts">
import AppIcon from './AppIcon.vue'
import { ICONS } from './palette'

const props = withDefaults(defineProps<{ set?: 'category' | 'account' | 'goal'; color?: string; label?: string }>(), {
  set: 'category',
  color: '#10b981',
})
const model = defineModel<string>({ required: true })
</script>

<template>
  <fieldset>
    <legend class="mb-2 text-sm font-medium text-ink">{{ label ?? 'Icon' }}</legend>
    <div class="grid max-h-48 grid-cols-7 gap-1.5 overflow-y-auto pr-1 sm:grid-cols-9">
      <button
        v-for="name in ICONS[props.set]"
        :key="name"
        type="button"
        class="flex aspect-square items-center justify-center rounded-[10px] transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
        :class="model === name ? 'text-white' : 'text-ink-muted hover:bg-ink/[0.06]'"
        :style="model === name ? { background: color } : undefined"
        :aria-label="`${name.replace(/-/g, ' ')} icon`"
        :aria-pressed="model === name"
        @click="model = name"
      >
        <AppIcon :name="name" class="size-5" />
      </button>
    </div>
  </fieldset>
</template>
