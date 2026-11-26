import { describe, expect, it } from 'vitest'
import { dayLabel, greeting } from '@/utils/date'

describe('dayLabel', () => {
  it('names today and yesterday', () => {
    expect(dayLabel('2026-11-23', '2026-11-23')).toBe('Today')
    expect(dayLabel('2026-11-22', '2026-11-23')).toBe('Yesterday')
    expect(dayLabel('2026-03-01', '2026-03-02')).toBe('Yesterday')
  })
  it('adds the year only for other years', () => {
    expect(dayLabel('2026-11-16', '2026-11-23')).not.toMatch(/2026/)
    expect(dayLabel('2025-12-31', '2026-01-02')).toMatch(/2025/)
  })
})

describe('greeting', () => {
  it('follows the time of day', () => {
    expect(greeting(8)).toBe('Good morning')
    expect(greeting(14)).toBe('Good afternoon')
    expect(greeting(20)).toBe('Good evening')
  })
})
