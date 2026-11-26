<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUiStore } from '@/stores/ui'
import ConnectionStatus from '@/components/ConnectionStatus.vue'
import BottomNav from './BottomNav.vue'
import SideNav from './SideNav.vue'

const ui = useUiStore()

/** "N" opens Quick Add from anywhere, unless the user is typing. */
function onKey(e: KeyboardEvent) {
  if (e.key !== 'n' && e.key !== 'N') return
  if (e.metaKey || e.ctrlKey || e.altKey) return
  const t = e.target as HTMLElement
  if (t.closest('input, textarea, select, [contenteditable="true"], [role="dialog"]')) return
  e.preventDefault()
  ui.openQuickAdd()
}
const route = useRoute()
const router = useRouter()
onMounted(async () => {
  window.addEventListener('keydown', onKey)
  // Home-screen shortcut ("Add expense") opens /expense/?add=Expense.
  await router.isReady()
  const add = route.query.add
  if (add === 'Expense' || add === 'Income' || add === 'Transfer') {
    ui.openQuickAdd(add)
    const { add: _drop, ...rest } = route.query
    router.replace({ query: rest })
  }
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="min-h-dvh bg-canvas">
    <a
      href="#main"
      class="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded focus:bg-card focus:px-3 focus:py-2"
    >Skip to content</a>
    <SideNav />
    <div class="lg:pl-[248px]">
      <main id="main" class="mx-auto w-full max-w-[1120px] px-4 pb-28 pt-5 sm:px-6 lg:px-10 lg:pb-12 lg:pt-8">
        <ConnectionStatus />
        <slot />
      </main>
    </div>
    <BottomNav />
  </div>
</template>
