'use client'

import { memo } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Skeleton } from './Skeleton'

/* ── Variant styles ──────────────────────────────── */

const iconVariants = cva(
  'size-9 rounded-xl flex items-center justify-center shrink-0',
  {
    variants: {
      variant: {
        default: 'bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]',
        accent: 'bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]',
        success: 'bg-[hsl(var(--success)/0.1)] text-[hsl(var(--success))]',
        warning: 'bg-[hsl(var(--warning)/0.1)] text-[hsl(var(--warning))]',
        danger: 'bg-[hsl(var(--danger)/0.1)] text-[hsl(var(--danger))]',
      },
    },
    defaultVariants: { variant: 'default' },
  },
)

/* ── Types ───────────────────────────────────────── */

export interface StatCardProps extends VariantProps<typeof iconVariants> {
  icon: React.ElementType
  label: string
  value: string | number
  trend?: { value: number; label?: string }
  loading?: boolean
  className?: string
}

/* ── StatCard ────────────────────────────────────── */

export const StatCard = memo(function StatCard({
  icon: Icon,
  label,
  value,
  trend,
  loading = false,
  variant,
  className,
}: StatCardProps) {
  const isPositive = trend && trend.value >= 0

  return (
    <div
      className={cn(
        'rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] px-4 py-3 shadow-[0_16px_32px_rgba(84,60,39,0.05)]',
        className,
      )}
    >
      <div className="flex items-center gap-3">
        <div className={cn(iconVariants({ variant }))}>
          <Icon className="h-4 w-4" aria-hidden="true" />
        </div>

        <div className="min-w-0 flex-1">
          {loading ? (
            <div className="space-y-1.5">
              <Skeleton variant="text" className="h-3 w-16" />
              <Skeleton variant="text" className="h-5 w-24" />
            </div>
          ) : (
            <>
              <p className="text-[11px] font-medium text-[color:var(--muted-ink)] truncate">
                {label}
              </p>
              <div className="flex items-baseline gap-2">
                <p className="text-sm font-semibold text-[color:var(--ink)]">
                  {value}
                </p>
                {trend && (
                  <span
                    className={cn(
                      'inline-flex items-center gap-0.5 text-[11px] font-medium',
                      isPositive ? 'text-emerald-500' : 'text-red-500',
                    )}
                  >
                    {isPositive ? (
                      <TrendingUp className="h-3 w-3" />
                    ) : (
                      <TrendingDown className="h-3 w-3" />
                    )}
                    {Math.abs(trend.value)}%
                    {trend.label && (
                      <span className="text-[color:var(--muted-ink)] ml-0.5">{trend.label}</span>
                    )}
                  </span>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
})
