'use client'

import { TrendingDown, TrendingUp } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Tooltip } from '@/components/ui/Tooltip'

interface PriceChangeIndicatorProps {
  changePct: number | undefined | null
}

export function PriceChangeIndicator({ changePct }: PriceChangeIndicatorProps) {
  if (changePct == null || changePct === 0) return null
  const isIncrease = changePct > 0
  return (
    <Tooltip
      content={isIncrease ? 'Price increased recently' : 'Price decreased recently'}
      side="top"
    >
      <span className={cn(
        'inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-bold tabular-nums',
        isIncrease
          ? 'bg-red-500/10 text-red-600'
          : 'bg-emerald-500/10 text-emerald-600',
      )}>
        {isIncrease ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
        {isIncrease ? '+' : ''}{changePct.toFixed(1)}%
      </span>
    </Tooltip>
  )
}
