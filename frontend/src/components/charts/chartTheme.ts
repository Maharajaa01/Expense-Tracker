/** Chart colours resolved from CSS tokens (see theme/tokens.css). */
export interface ChartTheme {
  income: string
  expense: string
  other: string
  savings: string
  surface: string
  grid: string
  axis: string
  ink: string
  muted: string
  dark: boolean
}

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}
function rgbVar(name: string): string {
  return `rgb(${cssVar(name).split(/\s+/).join(', ')})`
}

export function readChartTheme(dark: boolean): ChartTheme {
  return {
    income: cssVar('--et-chart-income'),
    expense: cssVar('--et-chart-expense'),
    other: cssVar('--et-chart-other'),
    savings: rgbVar('--et-savings'),
    surface: rgbVar('--et-card'),
    grid: rgbVar('--et-line'),
    axis: rgbVar('--et-ink-faint'),
    ink: rgbVar('--et-ink'),
    muted: rgbVar('--et-ink-muted'),
    dark,
  }
}

/** Shared tooltip styling: card surface, ink text. */
export function tooltipBase(t: ChartTheme) {
  return {
    backgroundColor: t.surface,
    borderColor: t.grid,
    borderWidth: 1,
    padding: [8, 12],
    textStyle: { color: t.ink, fontFamily: 'InterVariable, Inter, sans-serif', fontSize: 13 },
    extraCssText: 'border-radius:12px;box-shadow:0 8px 24px rgb(15 23 42 / 0.12);',
    confine: true,
  }
}
