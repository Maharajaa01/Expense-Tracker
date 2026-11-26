<script setup lang="ts">
import AppIcon from '@/components/ui/AppIcon.vue'
import { useUiStore } from '@/stores/ui'
import { BOTTOM_LEFT, BOTTOM_RIGHT } from './navigation'

const ui = useUiStore()
</script>

<template>
  <nav
    aria-label="Main"
    class="fixed inset-x-0 bottom-0 z-30 border-t border-line/70 bg-card/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden"
  >
    <div class="mx-auto grid h-16 max-w-md grid-cols-5 items-center">
      <RouterLink
        v-for="item in BOTTOM_LEFT"
        :key="item.name"
        :to="{ name: item.name }"
        class="et-tab flex flex-col items-center gap-0.5 text-[11px] font-medium text-ink-faint"
        exact-active-class="et-tab-active"
      >
        <AppIcon :name="item.icon" class="size-[22px]" />
        {{ item.label }}
      </RouterLink>

      <div class="flex justify-center">
        <button
          type="button"
          class="-mt-7 inline-flex size-[60px] items-center justify-center rounded-full bg-brand-solid text-white shadow-lift ring-[5px] ring-canvas transition-transform active:scale-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand"
          aria-label="Add transaction"
          @click="ui.openQuickAdd()"
        >
          <AppIcon name="plus" class="size-7" />
        </button>
      </div>

      <RouterLink
        v-for="item in BOTTOM_RIGHT"
        :key="item.name"
        :to="{ name: item.name }"
        class="et-tab flex flex-col items-center gap-0.5 text-[11px] font-medium text-ink-faint"
        exact-active-class="et-tab-active"
      >
        <AppIcon :name="item.icon" class="size-[22px]" />
        {{ item.label }}
      </RouterLink>
    </div>
  </nav>
</template>

<style scoped>
.et-tab-active {
  color: rgb(var(--et-primary-ink));
}
</style>
