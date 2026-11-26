<script setup lang="ts">
/** "Install app" button, visible until the app is installed. */
import { ref } from 'vue'
import { toast } from 'frappe-ui'
import AppIcon from '@/components/ui/AppIcon.vue'
import ResponsiveSheet from '@/components/ui/ResponsiveSheet.vue'
import { useInstall } from '@/composables/useInstall'

withDefaults(defineProps<{ variant?: 'sidebar' | 'banner' | 'row' }>(), { variant: 'row' })
const { showButton, canPrompt, promptInstall, platform } = useInstall()
const helpOpen = ref(false)
// Served by Frappe, not bundled: keep it a plain URL (a literal src would be treated as an import).
const APP_ICON = '/assets/expense_tracker/icons/icon-192.png'

async function install() {
  if (canPrompt.value) {
    const outcome = await promptInstall()
    if (outcome === 'accepted') toast.success('Expense Tracker is installed')
    return
  }
  helpOpen.value = true
}
</script>

<template>
  <!-- Single root so classes passed by the parent (e.g. lg:hidden) apply. -->
  <div v-if="showButton">
    <!-- Mobile dashboard banner -->
    <div v-if="variant === 'banner'" class="flex items-center gap-3 rounded-card bg-card p-3 ring-1 ring-line/60">
      <img :src="APP_ICON" alt="" class="size-11 rounded-[12px]" />
      <div class="min-w-0 flex-1">
        <p class="text-sm font-semibold text-ink">Install the app</p>
        <p class="text-[13px] text-ink-muted">Open it from your home screen, even offline.</p>
      </div>
      <button type="button" class="h-9 shrink-0 rounded-full bg-brand-solid px-4 text-sm font-semibold text-white" @click="install">Install</button>
    </div>

    <!-- Desktop sidebar -->
    <button
      v-else-if="variant === 'sidebar'"
      type="button"
      class="flex h-10 w-full items-center gap-3 rounded-[10px] px-3 text-[14.5px] text-ink-muted ring-1 ring-line/70 transition-colors hover:bg-ink/[0.04] hover:text-ink"
      @click="install"
    >
      <AppIcon name="download" class="size-[18px]" />
      Install app
    </button>

    <!-- Profile list row -->
    <button v-else type="button" class="flex h-14 w-full items-center gap-3 px-4 text-left text-[15px] text-ink hover:bg-ink/[0.03]" @click="install">
      <AppIcon name="download" class="size-5 text-brand-ink" />
      <span class="flex-1">Install app</span>
      <AppIcon name="chevron-right" class="size-4 text-ink-faint" />
    </button>

  <ResponsiveSheet v-model:open="helpOpen" title="Install Expense Tracker" size="md">
    <div class="space-y-4 pb-2 text-[15px] text-ink">
      <template v-if="platform === 'ios-safari'">
        <ol class="space-y-3">
          <li class="flex gap-3"><span class="font-semibold">1.</span><span>Tap the <b>Share</b> button <AppIcon name="upload" class="inline-block size-4 align-[-2px]" /> in Safari's toolbar.</span></li>
          <li class="flex gap-3"><span class="font-semibold">2.</span><span>Scroll down and tap <b>Add to Home Screen</b>.</span></li>
          <li class="flex gap-3"><span class="font-semibold">3.</span><span>Tap <b>Add</b>. The app opens from your home screen like any other app.</span></li>
        </ol>
      </template>
      <p v-else-if="platform === 'ios-other'">On iPhone and iPad, apps can only be installed from <b>Safari</b>. Open this page in Safari, then tap Share and <b>Add to Home Screen</b>.</p>
      <template v-else-if="platform === 'android'">
        <ol class="space-y-3">
          <li class="flex gap-3"><span class="font-semibold">1.</span><span>Open your browser's menu <AppIcon name="ellipsis-vertical" class="inline-block size-4 align-[-2px]" />.</span></li>
          <li class="flex gap-3"><span class="font-semibold">2.</span><span>Tap <b>Install app</b> or <b>Add to Home screen</b>.</span></li>
        </ol>
        <p class="text-sm text-ink-muted">If you don't see it, open this page in Chrome.</p>
      </template>
      <template v-else>
        <p>Use your browser's install option: in Chrome or Edge, click the install icon in the address bar, or open the menu and choose <b>Install Expense Tracker</b>.</p>
        <p class="text-sm text-ink-muted">Firefox and Safari on Mac don't support installing this kind of app. You can still bookmark it.</p>
      </template>
    </div>
  </ResponsiveSheet>
  </div>
</template>
