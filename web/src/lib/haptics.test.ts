import { describe, it, expect, beforeEach, vi } from 'vitest'
import { haptic, hapticsEnabled, setHapticsEnabled } from './haptics'

type NavWithVibrate = Navigator & { vibrate?: (pattern: number | number[]) => boolean }
const nav = () => navigator as NavWithVibrate

describe('haptics', () => {
  beforeEach(() => {
    window.localStorage.clear()
    setHapticsEnabled(true)
  })

  it('returns false when navigator.vibrate is missing', () => {
    const original = nav().vibrate
    delete nav().vibrate
    expect(hapticsEnabled()).toBe(false)
    if (original) nav().vibrate = original
  })

  it('returns true when vibrate is present and not opted out', () => {
    nav().vibrate = vi.fn().mockReturnValue(true)
    expect(hapticsEnabled()).toBe(true)
  })

  it('respects user opt-out persisted in localStorage', () => {
    nav().vibrate = vi.fn().mockReturnValue(true)
    setHapticsEnabled(false)
    expect(hapticsEnabled()).toBe(false)
    expect(window.localStorage.getItem('pp-haptics')).toBe('0')
  })

  it('calls navigator.vibrate with the mapped pattern', () => {
    const spy = vi.fn().mockReturnValue(true)
    nav().vibrate = spy
    haptic('success')
    expect(spy).toHaveBeenCalledWith([12, 40, 12])
  })

  it('is a no-op when haptics are disabled', () => {
    const spy = vi.fn().mockReturnValue(true)
    nav().vibrate = spy
    setHapticsEnabled(false)
    haptic('tap')
    expect(spy).not.toHaveBeenCalled()
  })

  it('swallows exceptions from navigator.vibrate', () => {
    nav().vibrate = () => {
      throw new Error('throttled')
    }
    expect(() => haptic('tap')).not.toThrow()
  })
})
