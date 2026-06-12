'use client'

import { useRef, useCallback, useState } from 'react'

interface SwipeState {
  deltaX: number
  direction: 'left' | 'right' | null
}

interface UseSwipeActionsOptions {
  onSwipeLeft?: () => void
  onSwipeRight?: () => void
  threshold?: number
}

export function useSwipeActions({ onSwipeLeft, onSwipeRight, threshold = 80 }: UseSwipeActionsOptions = {}) {
  const [swipe, setSwipe] = useState<SwipeState>({ deltaX: 0, direction: null })
  const startX = useRef<number | null>(null)
  const currentDelta = useRef(0)

  const onTouchStart = useCallback((e: React.TouchEvent) => {
    startX.current = e.touches[0].clientX
    currentDelta.current = 0
    setSwipe({ deltaX: 0, direction: null })
  }, [])

  const onTouchMove = useCallback((e: React.TouchEvent) => {
    if (startX.current === null) return
    const dx = e.touches[0].clientX - startX.current
    currentDelta.current = dx
    setSwipe({
      deltaX: dx,
      direction: dx > 0 ? 'right' : dx < 0 ? 'left' : null,
    })
  }, [])

  const onTouchEnd = useCallback(() => {
    if (startX.current === null) return
    const dx = currentDelta.current
    if (dx > threshold && onSwipeRight) {
      onSwipeRight()
    } else if (dx < -threshold && onSwipeLeft) {
      onSwipeLeft()
    }
    startX.current = null
    currentDelta.current = 0
    setSwipe({ deltaX: 0, direction: null })
  }, [onSwipeLeft, onSwipeRight, threshold])

  return {
    swipe,
    handlers: {
      onTouchStart,
      onTouchMove,
      onTouchEnd,
    },
  }
}
