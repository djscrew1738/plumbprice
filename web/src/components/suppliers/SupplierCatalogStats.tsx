'use client'

import { Package, DollarSign, TrendingDown } from 'lucide-react'
import { formatCurrencyDecimal } from '@/lib/utils'

interface SupplierCatalogStatsProps {
  filteredCount: number
  totalCount: number
  avgBest: number
}

export function SupplierCatalogStats({ filteredCount, totalCount, avgBest }: SupplierCatalogStatsProps) {
  return (
    <div className="grid grid-cols-1 gap-2.5 md:grid-cols-3">
      <div className="card-inset flex items-center gap-2.5 p-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl border border-blue-500/20 bg-blue-500/10">
          <Package size={14} className="text-blue-700" />
        </div>
        <div>
          <div className="text-[10px] font-medium uppercase tracking-wider leading-none text-[color:var(--muted-ink)]">Showing</div>
          <div className="text-sm font-bold text-[color:var(--ink)]">{filteredCount} <span className="text-xs font-normal text-[color:var(--muted-ink)]">of {totalCount}</span></div>
        </div>
      </div>
      <div className="card-inset flex items-center gap-2.5 p-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl border border-emerald-500/20 bg-emerald-500/10">
          <DollarSign size={14} className="text-emerald-700" />
        </div>
        <div>
          <div className="text-[10px] font-medium uppercase tracking-wider leading-none text-[color:var(--muted-ink)]">Avg Best</div>
          <div className="text-sm font-bold text-[color:var(--ink)]">{formatCurrencyDecimal(avgBest)}</div>
        </div>
      </div>
      <div className="card-inset flex items-center gap-2.5 p-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl border border-violet-500/20 bg-violet-500/10">
          <TrendingDown size={14} className="text-violet-700" />
        </div>
        <div>
          <div className="text-[10px] font-medium uppercase tracking-wider leading-none text-[color:var(--muted-ink)]">Suppliers</div>
          <div className="text-sm font-bold text-[color:var(--ink)]">Ferguson · Moore · Apex</div>
        </div>
      </div>
    </div>
  )
}
