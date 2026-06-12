'use client'

import { FileText, TrendingUp, MapPin } from 'lucide-react'
import { cn, formatCurrency } from '@/lib/utils'

interface EstimateSummaryStatsProps {
  count: number
  totalValue: number
  avgValue: number
}

export function EstimateSummaryStats({ count, totalValue, avgValue }: EstimateSummaryStatsProps) {
  const items = [
    { label: 'Showing',     value: count.toString(),     icon: FileText,   color: 'text-[hsl(var(--info))]',           bg: 'bg-[hsl(var(--info)/0.1)] border-[hsl(var(--info)/0.2)]' },
    { label: 'Total Value', value: formatCurrency(totalValue), icon: TrendingUp, color: 'text-[hsl(var(--success))]',        bg: 'bg-[hsl(var(--success)/0.1)] border-[hsl(var(--success)/0.2)]' },
    { label: 'Avg Value',   value: formatCurrency(avgValue),   icon: MapPin,     color: 'text-[color:var(--accent-strong)]', bg: 'bg-[color:var(--accent-soft)] border-[color:var(--accent)]/20' },
  ]

  return (
    <div className="mb-4 grid grid-cols-3 gap-3">
      {items.map(({ label, value, icon: Icon, color, bg }) => (
        <div key={label} className="card flex items-center gap-3 p-3.5">
          <div className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border', bg)}>
            <Icon size={14} className={color} />
          </div>
          <div className="min-w-0">
            <div className="text-[10px] font-bold tracking-tight text-[color:var(--muted-ink)]">{label}</div>
            <div className="truncate text-sm font-bold text-[color:var(--ink)]">{value}</div>
          </div>
        </div>
      ))}
    </div>
  )
}
