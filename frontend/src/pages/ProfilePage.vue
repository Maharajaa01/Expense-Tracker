<script setup lang="ts">
import InstallAppButton from '@/components/InstallAppButton.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import { PROFILE_LINKS } from '@/components/layout/navigation'
import { THEME_OPTIONS, useTheme } from '@/composables/useTheme'
import { logout } from '@/services/auth'
import { boot } from '@/services/boot'

const { scheme, setScheme } = useTheme()
</script>

<template>
  <div class="mx-auto max-w-lg">
    <PageHeader title="Profile" />
    <section class="mb-4 flex items-center gap-3 rounded-card bg-card p-4 ring-1 ring-line/60">
      <img v-if="boot.data?.user.image" :src="boot.data.user.image" alt="" class="size-12 rounded-full object-cover" />
      <span v-else class="inline-flex size-12 items-center justify-center rounded-full bg-accent-soft text-lg font-semibold text-accent">
        {{ boot.data?.user.first_name?.[0]?.toUpperCase() }}
      </span>
      <div class="min-w-0">
        <p class="truncate font-semibold text-ink">{{ boot.data?.user.full_name }}</p>
        <p class="truncate text-sm text-ink-muted">{{ boot.data?.user.name }}</p>
      </div>
    </section>

    <nav aria-label="More" class="mb-4 overflow-hidden rounded-card bg-card ring-1 ring-line/60">
      <InstallAppButton variant="row" class="border-b border-line/60" />
      <RouterLink
        v-for="item in PROFILE_LINKS"
        :key="item.name"
        :to="{ name: item.name }"
        class="flex h-14 items-center gap-3 border-b border-line/60 px-4 text-[15px] text-ink last:border-0 hover:bg-ink/[0.03]"
      >
        <AppIcon :name="item.icon" class="size-5 text-ink-muted" />
        <span class="flex-1">{{ item.label }}</span>
        <AppIcon name="chevron-right" class="size-4 text-ink-faint" />
      </RouterLink>
    </nav>

    <section class="mb-4 rounded-card bg-card p-4 ring-1 ring-line/60">
      <h2 class="mb-3 text-sm font-medium text-ink">Appearance</h2>
      <SegmentedControl :model-value="scheme" :options="THEME_OPTIONS" label="Appearance" @update:model-value="setScheme" />
    </section>

    <button
      type="button"
      class="flex h-12 w-full items-center justify-center gap-2 rounded-card bg-card font-medium text-expense ring-1 ring-line/60 hover:bg-expense-soft/40"
      @click="logout"
    >
      <AppIcon name="log-out" class="size-5" />
      Log out
    </button>
  </div>
</template>
