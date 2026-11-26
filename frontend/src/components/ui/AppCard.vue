<script setup lang="ts">
withDefaults(
  defineProps<{
    /** `plain`: white card. `brand`: the one solid-colour surface (balance). `sunken`: grouped background. */
    variant?: 'plain' | 'brand' | 'sunken'
    padding?: 'none' | 'sm' | 'md' | 'lg'
    as?: string
  }>(),
  { variant: 'plain', padding: 'md', as: 'section' },
)
</script>

<template>
  <component
    :is="as"
    class="rounded-card"
    :class="[
      {
        plain: 'bg-card shadow-card ring-1 ring-line/60',
        brand: 'bg-brand-solid text-white shadow-lift',
        sunken: 'bg-ink/[0.03] ring-1 ring-line/60',
      }[variant],
      { none: '', sm: 'p-3', md: 'p-4 sm:p-5', lg: 'p-5 sm:p-6' }[padding],
    ]"
  >
    <slot />
  </component>
</template>
