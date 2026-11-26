<script setup lang="ts">
/**
 * One API for modal forms: a bottom sheet on phones, a dialog on desktop.
 */
import { BottomSheet, Dialog } from 'frappe-ui'
import { useIsDesktop } from '@/composables/useBreakpoint'

withDefaults(defineProps<{ title?: string; size?: 'md' | 'lg' | 'xl' | '2xl'; dismissible?: boolean }>(), {
  size: 'lg',
  dismissible: true,
})
const open = defineModel<boolean>('open', { required: true })
const isDesktop = useIsDesktop()
</script>

<template>
  <Dialog v-if="isDesktop" v-model:open="open" :title="title" :size="size" :dismissible="dismissible">
    <template #default="{ close }"><slot :close="close" /></template>
  </Dialog>
  <BottomSheet v-else v-model:open="open" :title="title" :dismissible="dismissible">
    <div class="px-4 pb-[max(1rem,env(safe-area-inset-bottom))]">
      <slot :close="() => (open = false)" />
    </div>
  </BottomSheet>
</template>
