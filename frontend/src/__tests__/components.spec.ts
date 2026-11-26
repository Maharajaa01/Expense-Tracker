import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AmountInput from '@/components/ui/AmountInput.vue'
import Money from '@/components/ui/Money.vue'
import ProgressRing from '@/components/ui/ProgressRing.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import TransactionRow from '@/components/ui/TransactionRow.vue'
import { clampPercent, toneForUtilisation } from '@/components/ui/progress'
import type { TransactionRowData } from '@/types/finance'

const row = (over: Partial<TransactionRowData>): TransactionRowData => ({
  name: 't1', transaction_type: 'Expense', transaction_date: '2026-11-23', amount: 420, is_refund: 0,
  title: 'Lunch', account: 'a', account_name: 'Bank', category_name: 'Food', category_icon: 'utensils',
  category_color: '#f97316', ...over,
})

describe('Money', () => {
  it('has an accessible full label and tone class', () => {
    const w = mount(Money, { props: { value: -1500.5, tone: 'auto' } })
    expect(w.attributes('aria-label')).toBe('−₹1,500.50')
    expect(w.classes()).toContain('text-expense')
  })
  it('can hide paise', () => {
    const w = mount(Money, { props: { value: 99.99, hideFraction: true } })
    expect(w.text()).not.toContain('.99')
  })
})

describe('TransactionRow', () => {
  it('shows spending in the expense colour with a minus', () => {
    const money = mount(TransactionRow, { props: { txn: row({}) } }).findComponent(Money)
    expect(money.props('value')).toBe(-420)
    expect(money.classes()).toContain('text-expense')
  })
  it('shows income and refunds as green inflows', () => {
    for (const txn of [row({ transaction_type: 'Income' }), row({ is_refund: 1 })]) {
      const money = mount(TransactionRow, { props: { txn } }).findComponent(Money)
      expect(money.props('value')).toBe(420)
      expect(money.classes()).toContain('text-income')
    }
  })
  it('describes transfers neutrally', () => {
    const w = mount(TransactionRow, {
      props: { txn: row({ transaction_type: 'Transfer', to_account_name: 'Card', category_name: null }) },
    })
    expect(w.text()).toContain('Bank to Card')
    expect(w.findComponent(Money).classes()).toContain('text-ink-muted')
  })
  it('emits select on click', async () => {
    const w = mount(TransactionRow, { props: { txn: row({}) } })
    await w.trigger('click')
    expect(w.emitted('select')?.[0][0]).toMatchObject({ name: 't1' })
  })
})

describe('SegmentedControl', () => {
  const options = [
    { value: 'Expense', label: 'Expense' },
    { value: 'Income', label: 'Income' },
    { value: 'Transfer', label: 'Transfer' },
  ]
  it('selects on click and arrows wrap around', async () => {
    const w = mount(SegmentedControl, {
      props: { options, label: 'Type', modelValue: 'Expense', 'onUpdate:modelValue': (v: string) => w.setProps({ modelValue: v }) },
      attachTo: document.body,
    })
    const radios = w.findAll('[role="radio"]')
    expect(radios[0].attributes('aria-checked')).toBe('true')
    await radios[1].trigger('click')
    expect(w.props('modelValue')).toBe('Income')
    await w.findAll('[role="radio"]')[1].trigger('keydown', { key: 'ArrowRight' })
    expect(w.props('modelValue')).toBe('Transfer')
    await w.findAll('[role="radio"]')[2].trigger('keydown', { key: 'ArrowRight' })
    expect(w.props('modelValue')).toBe('Expense')
    w.unmount()
  })
})

describe('AmountInput', () => {
  it('sanitises typed input', async () => {
    let value = ''
    const w = mount(AmountInput, { props: { modelValue: '', 'onUpdate:modelValue': (v: string) => (value = v) } })
    const input = w.find('input')
    await input.setValue('12a3.456')
    expect(value).toBe('123.45')
    expect(input.attributes('inputmode')).toBe('decimal')
  })
  it('announces errors', () => {
    const w = mount(AmountInput, { props: { modelValue: '', error: 'Enter an amount' } })
    expect(w.find('[role="alert"]').text()).toBe('Enter an amount')
    expect(w.find('input').attributes('aria-invalid')).toBe('true')
  })
})

describe('progress helpers', () => {
  it('maps utilisation to alert tones', () => {
    expect(toneForUtilisation(49)).toBe('brand')
    expect(toneForUtilisation(80)).toBe('warn')
    expect(toneForUtilisation(100)).toBe('expense')
    expect(clampPercent(140)).toBe(100)
    expect(clampPercent(null)).toBe(0)
  })
  it('ring reports the real value even when over 100%', () => {
    const w = mount(ProgressRing, { props: { percent: 112, label: 'Fuel' } })
    expect(w.attributes('aria-valuenow')).toBe('112')
    expect(w.text()).toContain('112%')
  })
})
