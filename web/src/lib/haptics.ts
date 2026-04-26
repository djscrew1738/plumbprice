/**
 * Lightweight haptic feedback helper. Uses the Vibration API (Android,
 * desktop Chrome) and falls back to a no-op on iOS Safari and other
 * browsers that gate vibration. Pattern names mirror common conventions
 * from native mobile UI guidelines.
 *
 * iOS note: Apple has not exposed the Vibration API in Safari; for a
 * future native iOS PWA wrapper, route these through Capacitor Haptics.
 */

type HapticPattern = 'tap' | 'success' | 'warning' | 'error' | 'selection'

const PATTERNS: Record<HapticPattern, number | number[]> = {
  tap: 10,
  selection: 8,
  success: [12, 40, 12],
  warning: [25, 60, 25],
  error: [40, 80, 40, 80, 40],
}

let userOptedOut = false

export function setHapticsEnabled(enabled: boolean) {
  userOptedOut = !enabled
  if (typeof window !== 'undefined') {
    try {
      window.localStorage.setItem('pp-haptics', enabled ? '1' : '0')
    } catch {
      // ignore storage errors
    }
  }
}

export function hapticsEnabled(): boolean {
  if (typeof window === 'undefined') return false
  if (userOptedOut) return false
  try {
    const v = window.localStorage.getItem('pp-haptics')
    if (v === '0') return false
  } catch {
    // ignore storage errors
  }
  return typeof navigator !== 'undefined' && 'vibrate' in navigator
}

export function haptic(pattern: HapticPattern = 'tap') {
  if (!hapticsEnabled()) return
  try {
    navigator.vibrate(PATTERNS[pattern])
  } catch {
    // ignore — some browsers throw if the call is too frequent
  }
}
