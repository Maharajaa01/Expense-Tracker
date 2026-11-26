<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'

const props = withDefaults(
  defineProps<{ icon?: string | null; color?: string | null; size?: 'sm' | 'md' | 'lg' }>(),
  { icon: 'circle', color: '#94a3b8', size: 'md' },
)

const box = computed(() => ({ sm: 'size-8 rounded-[10px]', md: 'size-10 rounded-tile', lg: 'size-12 rounded-tile' })[props.size])
const glyph = computed(() => ({ sm: 'size-4', md: 'size-5', lg: 'size-6' })[props.size])
</script>

<template>
  <span
    class="et-cat-tile inline-flex shrink-0 items-center justify-center"
    :class="box"
    :style="{ '--tile': color || '#94a3b8' }"
  >
    <AppIcon :name="icon || 'circle'" :class="glyph" />
  </span>
</template>

<style scoped>
.et-cat-tile {
  color: var(--tile);
  background: color-mix(in srgb, var(--tile) 14%, transparent);
}
:global([data-theme='dark']) .et-cat-tile {
  color: color-mix(in srgb, var(--tile) 70%, white);
  background: color-mix(in srgb, var(--tile) 22%, transparent);
}
</style>
