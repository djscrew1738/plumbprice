'use client'

import { useState } from 'react'
import { cn } from '@/lib/utils'

interface ProfitMarginIndicatorProps {
  cost: number
  price: number
  className?: string
}

export function ProfitMarginIndicator({ cost, price, className }: ProfitMarginIndicatorProps) {
  const [showTooltip, setShowTooltip] = useState(false)
  const margin = price - cost
  const marginPct = price > 0 ? (margin / price) * 100 : 0
  const costPct = price > 0 ? (cost / price) * 100 : 0

  return (
    <div
      className={cn('relative', className)}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <div className="h-2 w-full overflow-hidden rounded-full bg-[color:var(--panel-strong)]">
        <div className="flex h-full">
          <div
            className="h-full bg-zinc-400"
            style={{ width: `${Math.max(costPct, 2)}%` }}
          />
          <div
            className="h-full bg-emerald-500"
            style={{ width: `${Math.max(marginPct, 2)}%` }}
          />
        </div>
      </div>
      {showTooltip && (
        <div className="absolute -top-10 left-1/2 z-10 -translate-x-1/2 rounded-lg border border-[color:var(--line)] bg-[color:var(--panel)] px-2.5 py-1.5 text-[10px] shadow-lg whitespace-nowrap">
          <span className="text-zinc-400">Cost ${cost.toFixed(2)}</span>
          <span className="mx-1 text-[color:var(--muted-ink)]">·</span>
          <span className="text-emerald-500">Margin ${margin.toFixed(2)} ({marginPct.toFixed(1)}%)</span>
        </div>
      )}
    </div>
  )
}
