'use client'

import {
  useState,
  useRef,
  useCallback,
  useEffect,
  useId,
  type ReactNode,
} from 'react'
import { createPortal } from 'react-dom'
import { cn } from '@/lib/utils'

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type Side = 'top' | 'right' | 'bottom' | 'left'

export interface TooltipProps {
  content: ReactNode
  children: ReactNode
  side?: Side
  delayMs?: number
  className?: string
}

/* ------------------------------------------------------------------ */
/*  Positioning helpers                                                */
/* ------------------------------------------------------------------ */

const GAP = 8

function computePosition(
  triggerRect: DOMRect,
  tooltipRect: DOMRect,
  preferred: Side,
): { x: number; y: number; actual: Side } {
  const vw = window.innerWidth
  const vh = window.innerHeight

  const positions: Record<Side, { x: number; y: number }> = {
    top: {
      x: triggerRect.left + triggerRect.width / 2 - tooltipRect.width / 2,
      y: triggerRect.top - tooltipRect.height - GAP,
    },
    bottom: {
      x: triggerRect.left + triggerRect.width / 2 - tooltipRect.width / 2,
      y: triggerRect.bottom + GAP,
    },
    left: {
      x: triggerRect.left - tooltipRect.width - GAP,
      y: triggerRect.top + triggerRect.height / 2 - tooltipRect.height / 2,
    },
    right: {
      x: triggerRect.right + GAP,
      y: triggerRect.top + triggerRect.height / 2 - tooltipRect.height / 2,
    },
  }

  const fits = (side: Side) => {
    const p = positions[side]
    return (
      p.x >= 4 &&
      p.y >= 4 &&
      p.x + tooltipRect.width <= vw - 4 &&
      p.y + tooltipRect.height <= vh - 4
    )
  }

  const opposite: Record<Side, Side> = {
    top: 'bottom',
    bottom: 'top',
    left: 'right',
    right: 'left',
  }

  let actual = preferred
  if (!fits(preferred)) {
    actual = fits(opposite[preferred]) ? opposite[preferred] : preferred
  }

  let { x, y } = positions[actual]

  // Clamp within viewport
  x = Math.max(4, Math.min(x, vw - tooltipRect.width - 4))
  y = Math.max(4, Math.min(y, vh - tooltipRect.height - 4))

  return { x, y, actual }
}

/* ------------------------------------------------------------------ */
/*  Arrow styles                                                       */
/* ------------------------------------------------------------------ */

const arrowStyles: Record<Side, string> = {
  top: 'left-1/2 -translate-x-1/2 top-full border-t-[color:var(--ink)] border-x-transparent border-b-transparent',
  bottom: 'left-1/2 -translate-x-1/2 bottom-full border-b-[color:var(--ink)] border-x-transparent border-t-transparent',
  left: 'top-1/2 -translate-y-1/2 left-full border-l-[color:var(--ink)] border-y-transparent border-r-transparent',
  right: 'top-1/2 -translate-y-1/2 right-full border-r-[color:var(--ink)] border-y-transparent border-l-transparent',
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function Tooltip({
  content,
  children,
  side = 'top',
  delayMs = 300,
  className,
}: TooltipProps) {
  const id = useId()
  const tooltipId = `${id}-tooltip`

  const [visible, setVisible] = useState(false)
  const [coords, setCoords] = useState<{ x: number; y: number; actual: Side } | null>(null)

  const triggerRef = useRef<HTMLSpanElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const show = useCallback(() => {
    timerRef.current = setTimeout(() => setVisible(true), delayMs)
  }, [delayMs])

  const hide = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = null
    setVisible(false)
  }, [])

  // Position after tooltip becomes visible
  useEffect(() => {
    if (!visible || !triggerRef.current || !tooltipRef.current) return
    const triggerRect = triggerRef.current.getBoundingClientRect()
    const tooltipRect = tooltipRef.current.getBoundingClientRect()
    setCoords(computePosition(triggerRect, tooltipRect, side))
  }, [visible, side])

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [])

  const tooltipEl = visible ? (
    <div
      ref={tooltipRef}
      id={tooltipId}
      role="tooltip"
      style={{
        position: 'fixed',
        left: coords?.x ?? -9999,
        top: coords?.y ?? -9999,
        zIndex: 9999,
        opacity: coords ? 1 : 0,
        transition: 'opacity 0.15s ease',
        pointerEvents: 'none',
      }}
      className={cn(
        'bg-[color:var(--ink)] text-[color:var(--background)] text-xs font-medium px-2.5 py-1.5 rounded-lg shadow-lg max-w-xs',
        className,
      )}
    >
      {content}
      {/* Arrow */}
      <span
        aria-hidden="true"
        className={cn(
          'absolute w-0 h-0 border-[4px]',
          arrowStyles[coords?.actual ?? side],
        )}
      />
    </div>
  ) : null

  return (
    <>
      <span
        ref={triggerRef}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
        aria-describedby={visible ? tooltipId : undefined}
        className="inline-flex"
      >
        {children}
      </span>
      {typeof document !== 'undefined' && tooltipEl && createPortal(tooltipEl, document.body)}
    </>
  )
}
