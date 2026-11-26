<script setup lang="ts">
import InstallAppButton from '@/components/InstallAppButton.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import { THEME_OPTIONS, useTheme } from '@/composables/useTheme'
import { logout } from '@/services/auth'
import { boot } from '@/services/boot'
import { useUiStore } from '@/stores/ui'
import { SIDEBAR } from './navigation'

const ui = useUiStore()
const { scheme, setScheme } = useTheme()
</script>

<template>
  <aside class="fixed inset-y-0 left-0 z-30 hidden w-[248px] flex-col border-r border-line/70 bg-card lg:flex">
    <div class="flex items-center gap-2.5 px-5 pb-4 pt-6">
      <span class="inline-flex size-9 items-center justify-center rounded-[11px] bg-brand-solid text-white">
        <AppIcon name="wallet" class="size-5" />
      </span>
      <span class="text-[17px] font-bold tracking-tight text-ink">Expense Tracker</span>
    </div>

    <div class="px-4 pb-3">
      <button
        type="button"
        class="flex h-11 w-full items-center justify-center gap-2 rounded-full bg-brand-solid font-semibold text-white shadow-lift transition-transform hover:bg-[#065f46] active:scale-[0.98] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
        aria-keyshortcuts="N"
        @click="ui.openQuickAdd()"
      >
        <AppIcon name="plus" class="size-5" />
        Add transaction
        <kbd class="ml-1 rounded bg-white/15 px-1.5 text-[11px] font-medium">N</kbd>
      </button>
    </div>

    <nav aria-label="Main" class="flex-1 overflow-y-auto px-3">
      <RouterLink
        v-for="item in SIDEBAR"
        :key="item.name"
        :to="{ name: item.name }"
        class="et-nav-link mb-0.5 flex h-10 items-center gap-3 rounded-[10px] px-3 text-[14.5px] text-ink-muted transition-colors hover:bg-ink/[0.04] hover:text-ink"
        exact-active-class="et-nav-active"
      >
        <AppIcon :name="item.icon" class="size-[18px]" />
        {{ item.label }}
      </RouterLink>
    </nav>

    <div class="space-y-3 border-t border-line/70 p-4">
      <InstallAppButton variant="sidebar" />
      <SegmentedControl
        :model-value="scheme"
        :options="THEME_OPTIONS"
        label="Appearance"
        size="sm"
        @update:model-value="setScheme"
      />
      <div class="flex items-center gap-3">
        <img v-if="boot.data?.user.image" :src="boot.data.user.image" alt="" class="size-8 rounded-full object-cover" />
        <span v-else class="inline-flex size-8 items-center justify-center rounded-full bg-accent-soft text-sm font-semibold text-accent">
          {{ boot.data?.user.first_name?.[0]?.toUpperCase() }}
        </span>
        <span class="min-w-0 flex-1 truncate text-sm font-medium text-ink">{{ boot.data?.user.full_name }}</span>
        <button type="button" class="text-ink-faint hover:text-ink" aria-label="Log out" @click="logout">
          <AppIcon name="log-out" class="size-[18px]" />
        </button>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.et-nav-active {
  background: rgb(var(--et-primary-soft));
  color: rgb(var(--et-primary-ink));
  font-weight: 600;
}
</style>
