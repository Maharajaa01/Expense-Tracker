import preset, { content } from 'frappe-ui/tailwind'
import { readFileSync } from 'node:fs'

/**
 * Brand tokens are CSS variables (see src/theme/tokens.css) so light/dark
 * switch by changing variables, not class names.
 */
const v = (name) => `rgb(var(--et-${name}) / <alpha-value>)`

// Icons chosen at runtime (category/account/goal icons stored in the DB) are
// not visible to Tailwind's scanner, so the curated set is safelisted.
const iconSet = JSON.parse(readFileSync(new URL('./src/theme/icon-set.json', import.meta.url), 'utf8'))
const iconClasses = [...new Set(Object.values(iconSet).flat())].map((n) => `lucide-${n}`)

/** @type {import('tailwindcss').Config} */
export default {
  presets: [preset],
  content: [...content, './index.html', './src/**/*.{vue,js,ts}'],
  safelist: iconClasses,
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: v('primary'), soft: v('primary-soft'), ink: v('primary-ink'), solid: v('primary-solid') },
        accent: { DEFAULT: v('secondary'), soft: v('secondary-soft'), solid: v('secondary-solid') },
        income: { DEFAULT: v('income'), soft: v('income-soft'), solid: v('income-solid') },
        expense: { DEFAULT: v('expense'), soft: v('expense-soft'), solid: v('expense-solid') },
        savings: { DEFAULT: v('savings'), soft: v('savings-soft') },
        warn: { DEFAULT: v('warning'), soft: v('warning-soft') },
        canvas: v('canvas'),
        card: v('card'),
        line: v('line'),
        ink: { DEFAULT: v('ink'), muted: v('ink-muted'), faint: v('ink-faint') },
      },
      borderRadius: { card: '1.25rem', tile: '0.875rem', sheet: '1.75rem' },
      boxShadow: {
        card: '0 1px 2px rgb(15 23 42 / 0.04), 0 4px 16px rgb(15 23 42 / 0.05)',
        lift: '0 10px 30px -6px rgb(4 120 87 / 0.35)',
      },
    },
  },
}
