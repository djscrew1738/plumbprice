'use client'

import { useEffect, useRef, useState, type RefObject } from 'react'
import { haptic } from '@/lib/haptics'

interface PullToRefreshOptions {
  /** Async refresh function. Spinner shows until it resolves. */
  onRefresh: () => Promise<void> | void
  /** Distance in px the user must pull beyond the threshold to trigger. Default 70. */
  threshold?: number
  /** Disable pull-to-refresh (e.g., when a modal is open). */
  disabled?: boolean
}

interface PullToRefreshState {
  /** Current pull distance in px (0 when not pulling). */
  pullDistance: number
  /** True while the refresh handler is in flight. */
  refreshing: boolean
  /** True when the user has pulled past the threshold and release will fire. */
  willTrigger: boolean
}

/**
 * Native-feeling pull-to-refresh for any scrollable container. Attach the
 * returned ref to the scrollable element and render a spinner whose
 * translateY tracks `pullDistance`.
 *
 * Only engages when the container is scrolled to top (scrollTop === 0) so
 * it never fights normal scrolling. iOS Safari swipe-back near the left
 * edge is left alone.
 */
export function usePullToRefresh<T extends HTMLElement = HTMLElement>(
  options: PullToRefreshOptions
): { ref: RefObject<T | null>; state: PullToRefreshState } {
  const { onRefresh, threshold = 70, disabled = false } = options
  const ref = useRef<T>(null)
  const [pullDistance, setPullDistance] = useState(0)
  const [refreshing, setRefreshing] = useState(false)
  const startY = useRef<number | null>(null)
  const triggered = useRef(false)

  useEffect(() => {
    const el = ref.current
    if (!el || disabled) return

    const onTouchStart = (e: TouchEvent) => {
      if (refreshing) return
      if (el.scrollTop > 0) {
        startY.current = null
        return
      }
      startY.current = e.touches[0]?.clientY ?? null
      triggered.current = false
    }

    const onTouchMove = (e: TouchEvent) => {
      if (startY.current === null || refreshing) return
      const y = e.touches[0]?.clientY ?? startY.current
      const delta = y - startY.current
      if (delta <= 0) {
        setPullDistance(0)
        return
      }
      // Resistance curve so it doesn't track 1:1 — feels native.
      const resisted = Math.min(160, Math.pow(delta, 0.85))
      setPullDistance(resisted)
      if (resisted > threshold && !triggered.current) {
        triggered.current = true
        haptic('selection')
      } else if (resisted <= threshold && triggered.current) {
        triggered.current = false
      }
    }

    const onTouchEnd = async () => {
      if (startY.current === null) return
      const distance = pullDistance
      startY.current = null
      if (distance > threshold && !refreshing) {
        setRefreshing(true)
        haptic('success')
        try {
          await onRefresh()
        } finally {
          setRefreshing(false)
          setPullDistance(0)
          triggered.current = false
        }
      } else {
        setPullDistance(0)
      }
    }

    el.addEventListener('touchstart', onTouchStart, { passive: true })
    el.addEventListener('touchmove', onTouchMove, { passive: true })
    el.addEventListener('touchend', onTouchEnd)
    el.addEventListener('touchcancel', onTouchEnd)

    return () => {
      el.removeEventListener('touchstart', onTouchStart)
      el.removeEventListener('touchmove', onTouchMove)
      el.removeEventListener('touchend', onTouchEnd)
      el.removeEventListener('touchcancel', onTouchEnd)
    }
  }, [onRefresh, threshold, disabled, refreshing, pullDistance])

  return {
    ref,
    state: {
      pullDistance,
      refreshing,
      willTrigger: pullDistance > threshold,
    },
  }
}
