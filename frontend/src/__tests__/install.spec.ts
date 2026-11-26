import { beforeEach, describe, expect, it, vi } from 'vitest'

describe('install button state', () => {
  beforeEach(() => {
    vi.resetModules()
    localStorage.clear()
    window.matchMedia = ((q: string) => ({ matches: false, media: q, addEventListener() {}, removeEventListener() {} })) as any
  })

  it('shows until installed, uses the native prompt when available, then hides', async () => {
    const { listenForInstall, useInstall } = await import('@/composables/useInstall')
    listenForInstall()
    const s = useInstall()
    expect(s.showButton.value).toBe(true)
    expect(s.canPrompt.value).toBe(false)

    const ev = Object.assign(new Event('beforeinstallprompt'), {
      prompt: vi.fn().mockResolvedValue(undefined),
      userChoice: Promise.resolve({ outcome: 'accepted' as const }),
    })
    window.dispatchEvent(ev)
    expect(s.canPrompt.value).toBe(true)
    expect(await s.promptInstall()).toBe('accepted')
    expect(ev.prompt).toHaveBeenCalled()
    expect(s.showButton.value).toBe(false)
    expect(localStorage.getItem('et-installed')).toBe('1')
  })

  it('hides when the app is running installed (standalone)', async () => {
    window.matchMedia = ((q: string) => ({ matches: q.includes('standalone'), media: q, addEventListener() {} })) as any
    const { listenForInstall, useInstall } = await import('@/composables/useInstall')
    listenForInstall()
    expect(useInstall().showButton.value).toBe(false)
  })

  it('comes back if the browser offers install again (app was uninstalled)', async () => {
    localStorage.setItem('et-installed', '1')
    const { listenForInstall, useInstall } = await import('@/composables/useInstall')
    listenForInstall()
    expect(useInstall().showButton.value).toBe(false)
    window.dispatchEvent(Object.assign(new Event('beforeinstallprompt'), { prompt: vi.fn(), userChoice: new Promise(() => {}) }))
    expect(useInstall().showButton.value).toBe(true)
  })

  it('hides after the appinstalled event (installed from the browser menu)', async () => {
    const { listenForInstall, useInstall } = await import('@/composables/useInstall')
    listenForInstall()
    window.dispatchEvent(new Event('appinstalled'))
    expect(useInstall().showButton.value).toBe(false)
  })
})
