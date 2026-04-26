import { describe, it, expect, beforeEach, vi } from 'vitest'
import { haptic, hapticsEnabled, setHapticsEnabled } from './haptics'

describe('haptics', () => {
  beforeEach(() => {
    window.localStorage.clear()
    setHapticsEnabled(true)
  })

  it('returns false when navigator.vibrate is missing', () => {
    const original = (navigator as any).vibrate
    delete (navigator as any).vibrate
    expect(hapticsEnabled()).toBe(false)
    if (original) (navigator as any).vibrate = original
  })

  it('returns true when vibrate is present and not opted out', () => {
    ;(navigator as any).vibrate = vi.fn().mockReturnValue(true)
    expect(hapticsEnabled()).toBe(true)
  })

  it('respects user opt-out persisted in localStorage', () => {
    ;(navigator as any).vibrate = vi.fn().mockReturnValue(true)
    setHapticsEnabled(false)
    expect(hapticsEnabled()).toBe(false)
    expect(window.localStorage.getItem('pp-haptics')).toBe('0')
  })

  it('calls navigator.vibrate with the mapped pattern', () => {
    const spy = vi.fn().mockReturnValue(true)
    ;(navigator as any).vibrate = spy
    haptic('success')
    expect(spy).toHaveBeenCalledWith([12, 40, 12])
  })

  it('is a no-op when haptics are disabled', () => {
    const spy = vi.fn().mockReturnValue(true)
    ;(navigator as any).vibrate = spy
    setHapticsEnabled(false)
    haptic('tap')
    expect(spy).not.toHaveBeenCalled()
  })

  it('swallows exceptions from navigator.vibrate', () => {
    ;(navigator as any).vibrate = () => {
      throw new Error('throttled')
    }
    expect(() => haptic('tap')).not.toThrow()
  })
})
