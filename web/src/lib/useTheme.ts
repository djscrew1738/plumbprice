'use client'

import { useCallback, useEffect, useSyncExternalStore } from 'react'

const STORAGE_KEY = 'pp_theme'

export type Theme = 'light' | 'dark'

const listeners = new Set<() => void>()

function getSnapshot(): Theme {
  if (typeof window === 'undefined') return 'light'
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light'
}

function getServerSnapshot(): Theme {
  return 'light'
}

function notify() {
  listeners.forEach(l => l())
}

function applyTheme(theme: Theme) {
  if (theme === 'dark') {
    document.documentElement.classList.add('dark')
    document.documentElement.style.colorScheme = 'dark'
  } else {
    document.documentElement.classList.remove('dark')
    document.documentElement.style.colorScheme = 'light'
  }
  notify()
}

function subscribe(callback: () => void) {
  listeners.add(callback)
  return () => { listeners.delete(callback) }
}

/**
 * Temporarily adds the `theme-transitioning` class to the HTML element
 * to enable smooth CSS transitions between light/dark modes.
 * The class is removed after the transition completes.
 */
function withTransition(fn: () => void) {
  const html = document.documentElement
  html.classList.add('theme-transitioning')
  fn()
  // Remove after the CSS transition duration (300ms + buffer)
  window.setTimeout(() => {
    html.classList.remove('theme-transitioning')
  }, 350)
}

export function useTheme(): {
  theme: Theme
  toggle: () => void
  setTheme: (t: Theme) => void
} {
  const theme = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)

  const setTheme = useCallback((t: Theme) => {
    localStorage.setItem(STORAGE_KEY, t)
    withTransition(() => applyTheme(t))
  }, [])

  const toggle = useCallback(() => {
    setTheme(theme === 'light' ? 'dark' : 'light')
  }, [theme, setTheme])

  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = (e: MediaQueryListEvent) => {
      // Only follow system preference if user hasn't set an explicit choice
      if (!localStorage.getItem(STORAGE_KEY)) {
        withTransition(() => applyTheme(e.matches ? 'dark' : 'light'))
      }
    }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  return { theme, toggle, setTheme }
}
