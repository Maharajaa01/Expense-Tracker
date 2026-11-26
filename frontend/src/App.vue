<script setup lang="ts">
import { FrappeUIProvider } from 'frappe-ui'
import AppShell from '@/components/layout/AppShell.vue'
import QuickAddHost from '@/components/QuickAddHost.vue'
</script>

<template>
  <FrappeUIProvider>
    <AppShell>
      <RouterView />
    </AppShell>
    <QuickAddHost />
  </FrappeUIProvider>
</template>
