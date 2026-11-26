<script setup lang="ts">
/** Lucide icon by name (CSS-mask class from frappe-ui's Tailwind plugin). Tint with text-*. */
defineProps<{ name: string; label?: string }>()
</script>

<template>
  <span
    :class="`lucide-${name}`"
    class="inline-block shrink-0"
    :role="label ? 'img' : undefined"
    :aria-label="label"
    :aria-hidden="label ? undefined : 'true'"
  />
</template>
