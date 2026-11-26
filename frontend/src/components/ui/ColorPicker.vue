<script setup lang="ts">
import AppIcon from './AppIcon.vue'
import { SWATCHES } from './palette'

defineProps<{ label?: string }>()
const model = defineModel<string>({ required: true })
</script>

<template>
  <fieldset>
    <legend class="mb-2 text-sm font-medium text-ink">{{ label ?? 'Colour' }}</legend>
    <div class="grid grid-cols-10 gap-2">
      <button
        v-for="c in SWATCHES"
        :key="c"
        type="button"
        class="flex aspect-square items-center justify-center rounded-full ring-offset-2 ring-offset-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink"
        :class="{ 'ring-2 ring-ink': model === c }"
        :style="{ background: c }"
        :aria-label="`Colour ${c}`"
        :aria-pressed="model === c"
        @click="model = c"
      >
        <AppIcon v-if="model === c" name="check" class="size-4 text-white" />
      </button>
    </div>
  </fieldset>
</template>
