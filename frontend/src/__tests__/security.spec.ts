import { describe, expect, it } from 'vitest'
import { esc, swatchRow } from '@/components/charts/format'

describe('chart tooltip HTML escaping', () => {
  it('escapes user-controlled names', () => {
    const evil = '<img src=x onerror="alert(1)">'
    expect(esc(evil)).toBe('&lt;img src=x onerror=&quot;alert(1)&quot;&gt;')
    const html = swatchRow('#fff', evil, '₹1')
    expect(html).not.toContain('<img')
    const div = document.createElement('div')
    div.innerHTML = html
    expect(div.querySelector('img')).toBeNull()
  })
})
