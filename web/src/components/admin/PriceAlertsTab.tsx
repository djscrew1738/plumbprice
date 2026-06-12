'use client'

import { useState } from 'react'
import { useAdminPriceAlerts, type PriceAlertItem } from '@/lib/hooks'
import { AlertTriangle, TrendingUp, TrendingDown, Package, Clock } from 'lucide-react'
import { cn } from '@/lib/utils'

function AlertRow({ alert }: { alert: PriceAlertItem }) {
  const isIncrease = alert.new_cost > alert.old_cost
  return (
    <div className="flex items-start gap-4 rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] p-4">
      <div className={cn(
        'flex size-10 shrink-0 items-center justify-center rounded-xl',
        isIncrease ? 'bg-amber-50 text-amber-600' : 'bg-emerald-50 text-emerald-600'
      )}>
        {isIncrease ? <TrendingUp size={20} /> : <TrendingDown size={20} />}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className="text-sm font-semibold text-[color:var(--ink)] truncate">
            {alert.product_name}
          </h3>
          <span className="rounded-full bg-[color:var(--panel-strong)] px-2 py-0.5 text-[10px] text-[color:var(--muted-ink)]">
            {alert.canonical_item}
          </span>
        </div>
        <p className="mt-0.5 text-xs text-[color:var(--muted-ink)]">
          {alert.supplier_name} · Source: {alert.source}
        </p>
        <div className="mt-2 flex items-center gap-4">
          <div className="text-xs">
            <span className="text-[color:var(--muted-ink)]">Old:</span>{' '}
            <span className="font-medium text-[color:var(--ink)]">${alert.old_cost.toFixed(2)}</span>
          </div>
          <div className="text-xs">
            <span className="text-[color:var(--muted-ink)]">New:</span>{' '}
            <span className="font-medium text-[color:var(--ink)]">${alert.new_cost.toFixed(2)}</span>
          </div>
          <div className={cn(
            'text-xs font-semibold',
            isIncrease ? 'text-amber-600' : 'text-emerald-600'
          )}>
            {isIncrease ? '+' : ''}{alert.pct_change.toFixed(1)}%
          </div>
        </div>
      </div>
      <div className="hidden sm:flex items-center gap-1 text-[10px] text-[color:var(--muted-ink)]">
        <Clock size={10} />
        {new Date(alert.recorded_at).toLocaleDateString()}
      </div>
    </div>
  )
}

export function PriceAlertsTab() {
  const [days, setDays] = useState(7)
  const [threshold, setThreshold] = useState(10)
  const { data, isLoading, error } = useAdminPriceAlerts(days, threshold, {
    enabled: true,
  })

  const alerts = data?.alerts ?? []
  const total = data?.total ?? 0

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <div className="flex items-center gap-2">
          <AlertTriangle size={16} className="text-amber-500" />
          <h2 className="text-sm font-semibold text-[color:var(--ink)]">
            Price Change Alerts
          </h2>
          <span className="rounded-full bg-[color:var(--panel-strong)] px-2 py-0.5 text-[10px] text-[color:var(--muted-ink)]">
            {total} alert{total !== 1 ? 's' : ''}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="alert-days" className="text-[11px] text-[color:var(--muted-ink)]">Days:</label>
          <select
            id="alert-days"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="rounded-lg border border-[color:var(--line)] bg-[color:var(--panel)] px-2 py-1 text-xs text-[color:var(--ink)]"
          >
            <option value={1}>1 day</option>
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
            <option value={30}>30 days</option>
          </select>
          <label htmlFor="alert-threshold" className="text-[11px] text-[color:var(--muted-ink)] ml-2">Threshold:</label>
          <select
            id="alert-threshold"
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
            className="rounded-lg border border-[color:var(--line)] bg-[color:var(--panel)] px-2 py-1 text-xs text-[color:var(--ink)]"
          >
            <option value={5}>5%</option>
            <option value={10}>10%</option>
            <option value={15}>15%</option>
            <option value={25}>25%</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] p-8 text-center text-sm text-[color:var(--muted-ink)]">
          Loading price alerts…
        </div>
      ) : error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Failed to load price alerts.
        </div>
      ) : alerts.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] p-12 text-[color:var(--muted-ink)]">
          <Package size={28} strokeWidth={1.5} />
          <p className="text-sm font-medium">No price alerts</p>
          <p className="text-xs">No supplier price changes exceeded {threshold}% in the last {days} day{days !== 1 ? 's' : ''}.</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {alerts.map((alert) => (
            <AlertRow key={`${alert.id}-${alert.recorded_at}`} alert={alert} />
          ))}
        </div>
      )}
    </div>
  )
}
