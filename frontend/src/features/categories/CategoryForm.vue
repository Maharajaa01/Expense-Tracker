<script setup lang="ts">
import { computed, ref } from 'vue'
import { toast } from 'frappe-ui'
import AppIcon from '@/components/ui/AppIcon.vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import ColorPicker from '@/components/ui/ColorPicker.vue'
import IconPicker from '@/components/ui/IconPicker.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import SelectField from '@/components/ui/SelectField.vue'
import { ApiError } from '@/services/api'
import { categoriesApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import type { Category } from '@/types/finance'

const props = defineProps<{ category?: Category | null; type: 'Expense' | 'Income'; parent?: string | null }>()
const emit = defineEmits<{ saved: [c: Category]; cancel: [] }>()
const finance = useFinanceStore()
const c = props.category

const name = ref(c?.category_name ?? '')
const type = ref<'Expense' | 'Income'>(c?.category_type ?? props.type)
const parent = ref(c?.parent_category ?? props.parent ?? '')
const parentColor = computed(() => (parent.value ? finance.categoryMap.get(parent.value)?.color : null))
const icon = ref(c?.icon ?? 'tag')
const color = ref(c?.color ?? parentColor.value ?? (props.type === 'Income' ? '#16a34a' : '#6366f1'))
const saving = ref(false)
const error = ref<string | null>(null)

const hasChildren = computed(() => !!c && finance.categories.some((x) => x.parent_category === c.name && !x.is_archived))
const parentOptions = computed(() =>
  finance
    .categoryTree(type.value)
    .filter((p) => p.name !== c?.name)
    .map((p) => ({ value: p.name, label: p.category_name })),
)

async function save() {
  if (saving.value) return
  if (!name.value.trim()) {
    error.value = 'Give the category a name.'
    return
  }
  saving.value = true
  error.value = null
  try {
    const data = { category_name: name.value.trim(), category_type: type.value, parent_category: parent.value || null, icon: icon.value, color: color.value }
    const saved = c ? await categoriesApi.update(c.name, data) : await categoriesApi.create(data)
    finance.upsertCategory(saved)
    finance.dataVersion++
    toast.success(c ? 'Category updated' : 'Category added')
    emit('saved', saved)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Could not save the category.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <form class="space-y-5 pt-1" novalidate @submit.prevent="save">
    <div class="flex items-center gap-3">
      <CategoryIcon :icon="icon" :color="color" size="lg" />
      <label class="flex-1">
        <span class="mb-1.5 block text-sm font-medium text-ink">Name</span>
        <input v-model="name" maxlength="100" placeholder="e.g. Pet care" class="h-11 w-full rounded-tile border-0 bg-card px-3 text-[15px] text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" />
      </label>
    </div>

    <SegmentedControl
      v-if="!c || !c.txn_count"
      v-model="type"
      label="Category type"
      :options="[{ value: 'Expense', label: 'Expense', tone: 'expense' }, { value: 'Income', label: 'Income', tone: 'income' }]"
      @update:model-value="parent = ''"
    />

    <div v-if="!hasChildren">
      <SelectField v-model="parent" label="Inside" :options="parentOptions" placeholder="Nothing (top-level category)" />
      <p class="mt-1 text-[13px] text-ink-muted">Subcategories add detail. Their spending also counts toward the parent.</p>
    </div>

    <div class="grid gap-5 sm:grid-cols-2">
      <IconPicker v-model="icon" :color="color" />
      <ColorPicker v-model="color" />
    </div>

    <p v-if="error" role="alert" class="rounded-tile bg-expense-soft/60 p-3 text-sm text-ink">{{ error }}</p>

    <div class="flex gap-2">
      <button type="button" class="h-12 rounded-full px-5 font-medium text-ink-muted hover:bg-ink/[0.05]" @click="emit('cancel')">Cancel</button>
      <button type="submit" class="flex h-12 flex-1 items-center justify-center gap-2 rounded-full bg-brand-solid font-semibold text-white disabled:opacity-70" :disabled="saving">
        <AppIcon v-if="saving" name="refresh-cw" class="size-5 animate-spin" />
        {{ c ? 'Save changes' : 'Add category' }}
      </button>
    </div>
  </form>
</template>
