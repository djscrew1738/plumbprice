'use client'

import { cn } from '@/lib/utils'

interface EstimateOutcomeBadgeProps {
  outcome: string
}

export function EstimateOutcomeBadge({ outcome }: EstimateOutcomeBadgeProps) {
  return (
    <span
      className={cn(
        'ml-2 rounded-full border px-2 py-0.5 text-[11px] font-semibold',
        outcome === 'won' && 'border-[hsl(var(--success)/0.25)] bg-[hsl(var(--success)/0.1)] text-[hsl(var(--success))]',
        outcome === 'lost' && 'border-[hsl(var(--danger)/0.25)] bg-[hsl(var(--danger)/0.1)] text-[hsl(var(--danger))]',
        outcome === 'no_bid' && 'border-[color:var(--line)] bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)]',
        outcome === 'pending' && 'border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning)/0.12)] text-[hsl(var(--warning))]',
      )}
      role="status"
    >
      {outcome === 'won' ? 'Won' : outcome === 'lost' ? 'Lost' : outcome === 'no_bid' ? 'No Bid' : 'Pending'}
    </span>
  )
}
