<script setup lang="ts">
/**
 * Hosts the transaction sheet, opened from the sidebar button, the mobile Add
 * tab, the "N" shortcut, or Edit on a transaction. Each opening mounts a fresh
 * form (and a fresh client transaction ID).
 */
import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import ResponsiveSheet from '@/components/ui/ResponsiveSheet.vue'
import TransactionForm from '@/features/transactions/TransactionForm.vue'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
const { quickAddOpen, quickAddType, quickAddAccount, editing } = storeToRefs(ui)
const session = ref(0)
watch(quickAddOpen, (open) => open && session.value++)
const title = computed(() => (editing.value ? 'Edit transaction' : 'Add transaction'))
</script>

<template>
  <ResponsiveSheet v-model:open="quickAddOpen" :title="title" size="xl">
    <TransactionForm
      v-if="quickAddOpen"
      :key="session"
      :editing="editing"
      :default-type="quickAddType"
      :default-account="quickAddAccount"
      @saved="ui.closeQuickAdd()"
      @cancel="ui.closeQuickAdd()"
    />
  </ResponsiveSheet>
</template>
