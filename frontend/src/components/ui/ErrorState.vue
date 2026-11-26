<script setup lang="ts">
import AppIcon from './AppIcon.vue'

defineProps<{ message: string; retrying?: boolean }>()
defineEmits<{ retry: [] }>()
</script>

<template>
  <div role="alert" class="flex items-start gap-3 rounded-tile bg-expense-soft/60 p-4 text-sm">
    <AppIcon name="circle-alert" class="mt-0.5 size-5 text-expense" />
    <div class="flex-1">
      <p class="text-ink">{{ message }}</p>
      <button
        type="button"
        class="mt-2 inline-flex items-center gap-1.5 font-medium text-expense hover:underline disabled:opacity-60"
        :disabled="retrying"
        @click="$emit('retry')"
      >
        <AppIcon name="refresh-cw" class="size-3.5" :class="{ 'animate-spin': retrying }" />
        Try again
      </button>
    </div>
  </div>
</template>
