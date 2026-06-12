'use client'

import { memo } from 'react'
import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Minus, type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Skeleton } from './Skeleton'
import { CountUp } from './Motion'
import { useReducedMotion } from '@/lib/useReducedMotion'

interface StatCardProps {
  label: string
  value: string | number
  change?: number
  changeLabel?: string
  trend?: { value: number; label?: string }
  icon?: LucideIcon | React.ElementType
  variant?: 'default' | 'accent' | 'success' | 'warning' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  className?: string
}

export const StatCard = memo(function StatCard({
  label,
  value,
  change,
  changeLabel,
  trend,
  icon: Icon,
  variant = 'default',
  size = 'md',
  loading = false,
  className,
}: StatCardProps) {
  const reduce = useReducedMotion()
  const effectiveChange = change ?? trend?.value
  const effectiveChangeLabel = changeLabel ?? trend?.label
  const changePositive = effectiveChange != null && effectiveChange > 0
  const changeNegative = effectiveChange != null && effectiveChange < 0
  const changeNeutral = effectiveChange != null && effectiveChange === 0
  const numericValue = typeof value === 'number' ? value : null
  const displayValue = numericValue !== null ? (
    <CountUp value={numericValue} formatter={(n) => n.toLocaleString()} />
  ) : value

  const variantStyles = {
    default: 'bg-[color:var(--panel-solid)] border-[color:var(--line)]',
    accent: 'bg-[color:var(--accent-soft)]/20 border-[color:var(--accent-soft)]',
    success: 'bg-[color:var(--success-soft)]/20 border-[color:var(--success-soft)]',
    warning: 'bg-[color:var(--warning-soft)]/20 border-[color:var(--warning-soft)]',
    danger: 'bg-[color:var(--danger-soft)]/20 border-[color:var(--danger-soft)]',
  }

  const sizeStyles = {
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-5',
  }

  const valueSize = {
    sm: 'text-lg',
    md: 'text-2xl',
    lg: 'text-3xl',
  }

  const iconBgStyles = {
    default: 'bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]',
    accent: 'bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]',
    success: 'bg-[hsl(var(--success-hsl)/0.1)] text-[hsl(var(--success-hsl))]',
    warning: 'bg-[hsl(var(--warning-hsl)/0.1)] text-[hsl(var(--warning-hsl))]',
    danger: 'bg-[hsl(var(--danger-hsl)/0.1)] text-[hsl(var(--danger-hsl))]',
  }

  if (loading) {
    return (
      <div className={cn('rounded-[1.25rem] border border-[color:var(--line)] bg-[color:var(--panel-solid)] p-4', className)}>
        <Skeleton className="h-3 w-16 rounded" />
        <Skeleton className="mt-2 h-7 w-24 rounded" />
      </div>
    )
  }

  return (
    <motion.div
      className={cn(
        'rounded-[1.25rem] border transition-all duration-fast hover:shadow-elev-2',
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      whileHover={reduce ? undefined : { y: -2 }}
      whileTap={reduce ? undefined : { scale: 0.99 }}
      transition={{ type: 'spring', damping: 28, stiffness: 320 }}
    >
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <p className="text-caption text-[color:var(--muted-ink)]">{label}</p>
          <p className={cn('mt-1 font-bold text-[color:var(--ink)] font-display', valueSize[size])}>
            {displayValue}
          </p>
        </div>
        {Icon && (
          <div className={cn('flex size-9 items-center justify-center rounded-[1rem] shrink-0', iconBgStyles[variant])}>
            <Icon size={18} aria-hidden="true" />
          </div>
        )}
      </div>
      {effectiveChange != null && (
        <div className="mt-2 flex items-center gap-1.5">
          {changePositive && <TrendingUp size={14} className="text-[color:var(--success)]" />}
          {changeNegative && <TrendingDown size={14} className="text-[color:var(--danger)]" />}
          {changeNeutral && <Minus size={14} className="text-[color:var(--muted-ink)]" />}
          <span className={cn(
            'text-xs font-semibold',
            changePositive ? 'text-[color:var(--success)]' :
            changeNegative ? 'text-[color:var(--danger)]' :
            'text-[color:var(--muted-ink)]'
          )}>
            {changePositive ? '+' : ''}{effectiveChange}%
          </span>
          {effectiveChangeLabel && (
            <span className="text-xs text-[color:var(--muted-ink)]">{effectiveChangeLabel}</span>
          )}
        </div>
      )}
    </motion.div>
  )
})
