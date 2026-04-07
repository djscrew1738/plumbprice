'use client'

import { useEffect, useRef } from 'react'

const FOCUSABLE_SELECTORS = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')

/**
 * Traps keyboard focus inside the returned ref's element while `active` is true.
 * Returns a ref to attach to the container element.
 */
export function useFocusTrap<T extends HTMLElement = HTMLDivElement>(active: boolean) {
  const containerRef = useRef<T>(null)

  useEffect(() => {
    if (!active) return

    const container = containerRef.current
    if (!container) return

    const focusable = Array.from(
      container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTORS)
    ).filter(el => !el.closest('[aria-hidden="true"]'))

    const first = focusable[0]
    const last = focusable[focusable.length - 1]

    // Move focus into the container on open
    first?.focus()

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== 'Tab') return
      if (focusable.length === 0) {
        event.preventDefault()
        return
      }

      if (event.shiftKey) {
        if (document.activeElement === first) {
          event.preventDefault()
          last?.focus()
        }
      } else {
        if (document.activeElement === last) {
          event.preventDefault()
          first?.focus()
        }
      }
    }

    container.addEventListener('keydown', handleKeyDown)
    return () => container.removeEventListener('keydown', handleKeyDown)
  }, [active])

  return containerRef
}

/**
 * Calls `onOutside` when the user clicks or focuses an element outside
 * the `[data-focus-trap]` region while `active` is true.
 */
export function useTrapFocusOutside(active: boolean, onOutside: () => void) {
  useEffect(() => {
    if (!active) return

    function handlePointerDown(event: PointerEvent) {
      const target = event.target as Node | null
      const trapRoots = document.querySelectorAll('[data-focus-trap]')
      const inside = Array.from(trapRoots).some(root => root.contains(target))
      if (!inside) onOutside()
    }

    document.addEventListener('pointerdown', handlePointerDown)
    return () => document.removeEventListener('pointerdown', handlePointerDown)
  }, [active, onOutside])
}
