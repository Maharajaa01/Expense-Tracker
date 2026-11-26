import { describe, expect, it } from 'vitest'
import { formatMoney, moneyParts, parseAmount, sanitizeAmountInput } from '@/utils/money'

describe('moneyParts', () => {
  it('uses Indian digit grouping', () => {
    expect(moneyParts(1234567.5)).toMatchObject({ integer: '12,34,567', fraction: '50', negative: false })
  })
  it('flags negatives but not negative zero', () => {
    expect(moneyParts(-42).negative).toBe(true)
    expect(moneyParts(-0.001).negative).toBe(false)
  })
  it('treats non-finite values as zero', () => {
    expect(moneyParts(Number.NaN)).toMatchObject({ integer: '0', fraction: '00' })
  })
})

describe('formatMoney', () => {
  it('formats with sign options', () => {
    expect(formatMoney(1500)).toBe('₹1,500.00')
    expect(formatMoney(-1500)).toBe('−₹1,500.00')
    expect(formatMoney(1500, { signed: true })).toBe('+₹1,500.00')
  })
})

describe('sanitizeAmountInput', () => {
  it.each([
    ['1,250', '1250'],
    ['12.345', '12.34'],
    ['1.2.3', '1.23'],
    ['abc12', '12'],
    ['007', '7'],
    ['.5', '0.5'],
    ['0', '0'],
    ['1234567890123', '123456789012'],
    ['₹ 99', '99'],
  ])('%s → %s', (input, out) => {
    expect(sanitizeAmountInput(input)).toBe(out)
  })
})

describe('parseAmount', () => {
  it('rejects empty, zero and too large', () => {
    expect(parseAmount('')).toBeNull()
    expect(parseAmount('.')).toBeNull()
    expect(parseAmount('0')).toBeNull()
    expect(parseAmount('0.00')).toBeNull()
    expect(parseAmount('1000000000000')).toBeNull()
  })
  it('rounds to paise', () => {
    expect(parseAmount('12.5')).toBe(12.5)
    expect(parseAmount('0.1')).toBe(0.1)
  })
})
