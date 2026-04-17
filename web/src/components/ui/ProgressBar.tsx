'use client'

import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

/* ── Track sizes ─────────────────────────────────── */

const trackVariants = cva('w-full rounded-full bg-[color:var(--panel-strong)]', {
  variants: {
    size: {
      sm: 'h-1',
      md: 'h-2',
      lg: 'h-3',
    },
  },
  defaultVariants: { size: 'md' },
})

/* ── Bar colors ──────────────────────────────────── */

const barColors: Record<string, string> = {
  default: 'bg-[color:var(--accent)]',
  accent: 'bg-[color:var(--accent)]',
  success: 'bg-[hsl(var(--success))]',
  warning: 'bg-[hsl(var(--warning))]',
  danger: 'bg-[hsl(var(--danger))]',
}

/* ── Types ───────────────────────────────────────── */

export interface ProgressBarProps extends VariantProps<typeof trackVariants> {
  value: number
  max?: number
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'accent'
  showLabel?: boolean
  label?: string
  indeterminate?: boolean
  animated?: boolean
  className?: string
}

/* ── ProgressBar ─────────────────────────────────── */

export function ProgressBar({
  value,
  max = 100,
  variant = 'default',
  size,
  showLabel = false,
  label,
  indeterminate = false,
  animated = true,
  className,
}: ProgressBarProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))
  const displayLabel = label ?? `${Math.round(pct)}%`

  return (
    <div className={cn('w-full', className)}>
      {/* Label above the track for md/lg */}
      {showLabel && (size === 'md' || size === 'lg' || !size) && (
        <div className="mb-1 flex items-center justify-between">
          <span className="text-[11px] font-medium text-[color:var(--muted-ink)]">
            {displayLabel}
          </span>
        </div>
      )}

      <div className="flex items-center gap-2">
        <div
          className={cn(trackVariants({ size }))}
          role="progressbar"
          aria-valuenow={indeterminate ? undefined : Math.round(pct)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={displayLabel}
        >
          {indeterminate ? (
            <div
              className={cn(
                'h-full w-1/3 rounded-full animate-indeterminate',
                barColors[variant],
              )}
            />
          ) : (
            <div
              className={cn(
                'h-full rounded-full',
                barColors[variant],
                animated && 'transition-all duration-500 ease-out',
              )}
              style={{ width: `${pct}%` }}
            />
          )}
        </div>

        {/* Inline label for sm size */}
        {showLabel && size === 'sm' && (
          <span className="text-[10px] font-medium text-[color:var(--muted-ink)] shrink-0">
            {displayLabel}
          </span>
        )}
      </div>

      {/* Indeterminate keyframes */}
      {indeterminate && (
        <style dangerouslySetInnerHTML={{ __html: `
          @keyframes pp-indeterminate {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(400%); }
          }
          .animate-indeterminate {
            animation: pp-indeterminate 1.5s ease-in-out infinite;
          }
        `}} />
      )}
    </div>
  )
}
