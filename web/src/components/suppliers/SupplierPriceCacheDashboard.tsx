'use client'

import { RefreshCw, Database, Zap, AlertTriangle, Clock } from 'lucide-react'
import { cn } from '@/lib/utils'
import { StatCard } from '@/components/ui/StatCard'

interface SupplierPriceCacheDashboardProps {
  cachedItems?: number
  hitRate?: number
  staleCount?: number
  lastRefresh?: string | null
  loading: boolean
  refreshing: boolean
  suppliers: string[]
  supplierLabels: Record<string, string>
  itemCount: number
  onRefreshAll: () => void
  onRefreshSupplier: (supplierId: string) => void
}

export function SupplierPriceCacheDashboard({
  cachedItems,
  hitRate,
  staleCount,
  lastRefresh,
  loading,
  refreshing,
  suppliers,
  supplierLabels,
  itemCount,
  onRefreshAll,
  onRefreshSupplier,
}: SupplierPriceCacheDashboardProps) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <StatCard
          icon={Database}
          label="Cached Items"
          value={cachedItems ?? '—'}
          loading={loading}
          variant="default"
        />
        <StatCard
          icon={Zap}
          label="Hit Rate"
          value={hitRate !== undefined ? `${(hitRate * 100).toFixed(1)}%` : '—'}
          loading={loading}
          variant="success"
        />
        <StatCard
          icon={AlertTriangle}
          label="Stale Items"
          value={staleCount ?? '—'}
          loading={loading}
          variant={(staleCount ?? 0) > 0 ? 'warning' : 'default'}
        />
        <StatCard
          icon={Clock}
          label="Last Refresh"
          value={lastRefresh ?? '—'}
          loading={loading}
          variant="default"
        />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={onRefreshAll}
          disabled={refreshing}
          className={cn(
            'btn-secondary flex min-h-0 items-center gap-1.5 px-3 py-2 text-xs font-semibold',
            refreshing && 'opacity-70'
          )}
          aria-label="Refresh all supplier prices"
        >
          <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
          Refresh All Prices
        </button>

        {suppliers.map(sup => (
          <button
            key={sup}
            onClick={() => onRefreshSupplier(sup)}
            disabled={refreshing}
            className="btn-secondary flex min-h-0 items-center gap-1 px-2.5 py-1.5 text-[11px] font-semibold"
            aria-label={`Refresh ${supplierLabels[sup] ?? sup} prices`}
          >
            <RefreshCw size={11} className={refreshing ? 'animate-spin' : ''} />
            {supplierLabels[sup]}
          </button>
        ))}
      </div>

      {refreshing && (
        <div className="flex items-center gap-2 text-xs text-[color:var(--muted-ink)]" role="status" aria-live="polite">
          <RefreshCw size={12} className="shrink-0 animate-spin text-emerald-500" />
          <span>Refreshing prices for {itemCount > 0 ? `${itemCount} items` : 'all items'}…</span>
          <div className="h-1 min-w-[60px] flex-1 overflow-hidden rounded-full bg-emerald-100">
            <div className="h-full w-2/5 animate-pulse rounded-full bg-emerald-400" />
          </div>
        </div>
      )}
    </div>
  )
}
