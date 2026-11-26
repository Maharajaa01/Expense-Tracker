<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { dialog, toast } from 'frappe-ui'
import AppIcon from '@/components/ui/AppIcon.vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import ResponsiveSheet from '@/components/ui/ResponsiveSheet.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import SkeletonRows from '@/components/ui/SkeletonRows.vue'
import CategoryForm from '@/features/categories/CategoryForm.vue'
import { ApiError } from '@/services/api'
import { categoriesApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import type { Category } from '@/types/finance'

const finance = useFinanceStore()
onMounted(() => finance.load())

const type = ref<'Expense' | 'Income'>('Expense')
const tree = computed(() => finance.categoryTree(type.value))
const archived = computed(() => finance.categories.filter((c) => c.category_type === type.value && c.is_archived))
const showArchived = ref(false)

const formOpen = ref(false)
const editing = ref<Category | null>(null)
const newParent = ref<string | null>(null)
const selected = ref<Category | null>(null)
const actionsOpen = computed({ get: () => !!selected.value, set: (v) => !v && (selected.value = null) })

function openCreate(parent: string | null = null) {
  selected.value = null
  editing.value = null
  newParent.value = parent
  formOpen.value = true
}
function openEdit(c: Category) {
  selected.value = null
  editing.value = c
  formOpen.value = true
}
const uses = (n: number) => (n === 0 ? 'Not used yet' : n === 1 ? '1 transaction' : `${n} transactions`)

async function setArchived(c: Category, value: boolean) {
  selected.value = null
  try {
    await categoriesApi.setArchived(c.name, value)
    await finance.reloadCategories()
    finance.dataVersion++
    toast.success(value ? 'Category archived' : 'Category restored')
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : 'Could not update the category.')
  }
}

function remove(c: Category) {
  selected.value = null
  dialog.danger({
    title: `Delete ${c.category_name}?`,
    message: 'This category has never been used. Deleting it cannot be undone.',
    confirmLabel: 'Delete',
    onConfirm: async () => {
      try {
        await categoriesApi.remove(c.name)
        await finance.reloadCategories()
        toast.success('Category deleted')
      } catch (e) {
        throw new Error(e instanceof ApiError ? e.message : 'Could not delete the category.')
      }
    },
  })
}
const canDelete = (c: Category) => !c.txn_count && !finance.categories.some((x) => x.parent_category === c.name)
</script>

<template>
  <div>
    <PageHeader title="Categories">
      <template #actions>
        <button type="button" class="inline-flex h-10 items-center gap-1.5 rounded-full bg-brand-solid px-4 text-sm font-semibold text-white" @click="openCreate()">
          <AppIcon name="plus" class="size-4" /> Add category
        </button>
      </template>
    </PageHeader>

    <SegmentedControl
      v-model="type"
      label="Category type"
      class="mb-4 max-w-sm"
      :options="[{ value: 'Expense', label: 'Expenses', tone: 'expense' }, { value: 'Income', label: 'Income', tone: 'income' }]"
    />

    <ErrorState v-if="finance.error && !finance.loaded" :message="finance.error" @retry="finance.load(true)" />
    <div v-else-if="!finance.loaded" class="rounded-card bg-card px-3 ring-1 ring-line/60"><SkeletonRows :rows="6" /></div>

    <div v-else class="rounded-card bg-card p-1.5 ring-1 ring-line/60">
      <template v-for="p in tree" :key="p.name">
        <button type="button" class="flex w-full items-center gap-3 rounded-tile px-2 py-2.5 text-left hover:bg-ink/[0.03]" @click="selected = p">
          <CategoryIcon :icon="p.icon" :color="p.color" />
          <span class="min-w-0 flex-1">
            <span class="block truncate text-[15px] font-medium text-ink">{{ p.category_name }}</span>
            <span class="block text-[13px] text-ink-muted">{{ uses(p.txn_count) }}<template v-if="p.children.length">, {{ p.children.length }} subcategories</template></span>
          </span>
          <AppIcon name="ellipsis-vertical" class="size-4 text-ink-faint" />
        </button>
        <button
          v-for="c in p.children"
          :key="c.name"
          type="button"
          class="flex w-full items-center gap-3 rounded-tile py-2 pl-10 pr-2 text-left hover:bg-ink/[0.03]"
          @click="selected = c"
        >
          <CategoryIcon :icon="c.icon" :color="c.color" size="sm" />
          <span class="min-w-0 flex-1">
            <span class="block truncate text-[14.5px] text-ink">{{ c.category_name }}</span>
            <span class="block text-[12.5px] text-ink-muted">{{ uses(c.txn_count) }}</span>
          </span>
          <AppIcon name="ellipsis-vertical" class="size-4 text-ink-faint" />
        </button>
      </template>
    </div>

    <section v-if="archived.length" class="mt-8">
      <button type="button" class="mb-3 inline-flex items-center gap-1 text-sm font-medium text-ink-muted hover:text-ink" :aria-expanded="showArchived" @click="showArchived = !showArchived">
        <AppIcon name="chevron-right" class="size-4 transition-transform" :class="{ 'rotate-90': showArchived }" />
        Archived ({{ archived.length }})
      </button>
      <div v-if="showArchived" class="rounded-card bg-card p-1.5 ring-1 ring-line/60">
        <button v-for="c in archived" :key="c.name" type="button" class="flex w-full items-center gap-3 rounded-tile px-2 py-2.5 text-left opacity-75 hover:bg-ink/[0.03]" @click="selected = c">
          <CategoryIcon :icon="c.icon" :color="c.color" size="sm" />
          <span class="flex-1 text-[15px] text-ink">{{ c.category_name }}</span>
        </button>
      </div>
    </section>

    <ResponsiveSheet v-model:open="actionsOpen" :title="selected?.category_name" size="md">
      <div v-if="selected" class="space-y-1 pb-2">
        <RouterLink :to="{ name: 'transactions', query: { category: selected.name } }" class="flex h-12 items-center gap-3 rounded-tile px-3 text-[15px] text-ink hover:bg-ink/[0.04]" @click="selected = null">
          <AppIcon name="calendar" class="size-5 text-ink-muted" /> View transactions
        </RouterLink>
        <button v-if="!selected.parent_category && !selected.is_archived" type="button" class="flex h-12 w-full items-center gap-3 rounded-tile px-3 text-[15px] text-ink hover:bg-ink/[0.04]" @click="openCreate(selected.name)">
          <AppIcon name="plus" class="size-5 text-ink-muted" /> Add subcategory
        </button>
        <button type="button" class="flex h-12 w-full items-center gap-3 rounded-tile px-3 text-[15px] text-ink hover:bg-ink/[0.04]" @click="openEdit(selected)">
          <AppIcon name="pencil" class="size-5 text-ink-muted" /> Edit
        </button>
        <button type="button" class="flex h-12 w-full items-center gap-3 rounded-tile px-3 text-[15px] text-ink hover:bg-ink/[0.04]" @click="setArchived(selected, !selected.is_archived)">
          <AppIcon :name="selected.is_archived ? 'rotate-ccw' : 'archive'" class="size-5 text-ink-muted" />
          {{ selected.is_archived ? 'Restore' : 'Archive' }}
        </button>
        <button v-if="canDelete(selected)" type="button" class="flex h-12 w-full items-center gap-3 rounded-tile px-3 text-[15px] text-expense hover:bg-expense-soft/40" @click="remove(selected)">
          <AppIcon name="trash-2" class="size-5" /> Delete
        </button>
        <p v-else class="px-3 pt-2 text-[13px] text-ink-muted">Categories that are in use can be archived. Archived categories keep their history but don't appear when adding transactions.</p>
      </div>
    </ResponsiveSheet>

    <ResponsiveSheet v-model:open="formOpen" :title="editing ? 'Edit category' : newParent ? 'Add subcategory' : 'Add category'" size="xl">
      <CategoryForm v-if="formOpen" :category="editing" :type="type" :parent="newParent" @saved="formOpen = false" @cancel="formOpen = false" />
    </ResponsiveSheet>
  </div>
</template>
