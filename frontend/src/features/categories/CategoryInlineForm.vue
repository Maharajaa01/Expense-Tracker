<script setup lang="ts">
/** Minimal "new category" form used inside the transaction sheet. */
import { nextTick, onMounted, ref } from 'vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import ColorPicker from '@/components/ui/ColorPicker.vue'
import IconPicker from '@/components/ui/IconPicker.vue'
import { ApiError } from '@/services/api'
import { categoriesApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import type { Category } from '@/types/finance'

const props = defineProps<{ type: 'Expense' | 'Income' }>()
const emit = defineEmits<{ created: [c: Category]; cancel: [] }>()
const finance = useFinanceStore()

const name = ref('')
const icon = ref('tag')
const color = ref(props.type === 'Income' ? '#16a34a' : '#6366f1')
const saving = ref(false)
const error = ref<string | null>(null)
const nameEl = ref<HTMLInputElement>()

onMounted(() => nextTick(() => nameEl.value?.focus()))

async function save() {
  if (saving.value) return
  if (!name.value.trim()) {
    error.value = 'Give the category a name.'
    return
  }
  saving.value = true
  error.value = null
  try {
    const c = await categoriesApi.create({ category_name: name.value.trim(), category_type: props.type, icon: icon.value, color: color.value })
    finance.upsertCategory(c)
    emit('created', c)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Could not create the category.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="rounded-tile bg-ink/[0.03] p-3 ring-1 ring-line/60">
    <div class="mb-3 flex items-center gap-3">
      <CategoryIcon :icon="icon" :color="color" />
      <label class="flex-1">
        <span class="sr-only">Category name</span>
        <input
          ref="nameEl"
          v-model="name"
          maxlength="100"
          :placeholder="`New ${type.toLowerCase()} category`"
          class="h-10 w-full rounded-[10px] border-0 bg-card px-3 text-[15px] text-ink ring-1 ring-line focus:ring-2 focus:ring-brand"
          @keydown.enter.prevent="save"
        />
      </label>
    </div>
    <div class="grid gap-4 sm:grid-cols-2">
      <IconPicker v-model="icon" :color="color" />
      <ColorPicker v-model="color" />
    </div>
    <p v-if="error" role="alert" class="mt-2 text-sm text-expense">{{ error }}</p>
    <div class="mt-3 flex justify-end gap-2">
      <button type="button" class="h-9 rounded-full px-4 text-sm font-medium text-ink-muted hover:bg-ink/[0.05]" @click="emit('cancel')">
        Cancel
      </button>
      <button
        type="button"
        class="inline-flex h-9 items-center gap-1.5 rounded-full bg-brand-solid px-4 text-sm font-semibold text-white disabled:opacity-60"
        :disabled="saving"
        @click="save"
      >
        <AppIcon v-if="saving" name="refresh-cw" class="size-4 animate-spin" />
        Add category
      </button>
    </div>
  </div>
</template>
