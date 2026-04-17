'use client'

import { BarChart3, DollarSign, Wrench, Package } from 'lucide-react'
import { StatCard } from '@/components/ui/StatCard'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/ErrorState'

interface Stats {
  total_estimates: number
  avg_estimate_value: number
  labor_templates_count: number
  canonical_items_count: number
}

export interface StatsTabProps {
  stats: Stats | null
  loading: boolean
  onRetry: () => void
}

const STAT_ITEMS = [
  { key: 'total_estimates', label: 'Total Estimates', icon: BarChart3, variant: 'default' as const },
  { key: 'avg_estimate_value', label: 'Avg Value', icon: DollarSign, variant: 'success' as const },
  { key: 'labor_templates_count', label: 'Labor Templates', icon: Wrench, variant: 'accent' as const },
  { key: 'canonical_items_count', label: 'Catalog Items', icon: Package, variant: 'warning' as const },
] as const

export function StatsTab({ stats, loading, onRetry }: StatsTabProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-3">
        <Skeleton variant="stat-card" className="h-28 rounded-2xl" />
        <Skeleton variant="stat-card" className="h-28 rounded-2xl" />
        <Skeleton variant="stat-card" className="h-28 rounded-2xl" />
        <Skeleton variant="stat-card" className="h-28 rounded-2xl" />
      </div>
    )
  }

  if (!stats) {
    return <ErrorState message="Stats unavailable" onRetry={onRetry} />
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      {STAT_ITEMS.map(({ key, label, icon, variant }) => {
        const raw = stats[key]
        const value = key === 'avg_estimate_value'
          ? `$${Math.round(raw ?? 0).toLocaleString()}`
          : raw

        return (
          <StatCard
            key={key}
            icon={icon}
            label={label}
            value={value}
            variant={variant}
          />
        )
      })}
    </div>
  )
}
