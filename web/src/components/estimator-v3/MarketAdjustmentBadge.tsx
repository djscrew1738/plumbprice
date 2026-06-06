'use client'

import { TrendingUp, TrendingDown } from 'lucide-react'
import { cn } from '@/lib/utils'

interface MarketAdjustmentBadgeProps {
  name: string
  category: string
  factor: number
}

export function MarketAdjustmentBadge({ name, category, factor }: MarketAdjustmentBadgeProps) {
  const isIncrease = factor > 1.0
  const pct = Math.round((factor - 1.0) * 1000) / 10

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium',
        isIncrease
          ? 'border-amber-200 bg-amber-50 text-amber-700'
          : 'border-emerald-200 bg-emerald-50 text-emerald-700'
      )}
      title={`${name} (${category})`}
    >
      {isIncrease ? (
        <TrendingUp size={12} />
      ) : (
        <TrendingDown size={12} />
      )}
      <span>
        {isIncrease ? '+' : ''}
        {pct}% {name}
      </span>
    </div>
  )
}
