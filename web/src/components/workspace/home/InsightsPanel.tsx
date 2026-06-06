'use client'

import { useState } from 'react'
import dynamic from 'next/dynamic'
import Link from 'next/link'
import { AlertTriangle, BarChart3, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useReducedMotion } from '@/lib/useReducedMotion'

// Lazy-loaded chart — keeps Home initial bundle lean.
const BarChart = dynamic(
  () => import('@/components/ui/BarChart').then((m) => ({ default: m.BarChart })),
  { ssr: false, loading: () => <div className="h-[180px] animate-pulse rounded-[var(--radius-md)] bg-[color:var(--surface-2)]" /> },
)

export interface InsightsPanelProps {
  expiredCount: number
  dailyActivity: Array<{ label: string; value: number }> | null
  /** Default open state. Closed on mobile to keep above-the-fold tight. */
  defaultOpen?: boolean
}

export function InsightsPanel({
  expiredCount,
  dailyActivity,
  defaultOpen = false,
}: InsightsPanelProps) {
  const [open, setOpen] = useState(defaultOpen)
  const reduce = useReducedMotion()
  const hasChart = dailyActivity && dailyActivity.some((d) => d.value > 0)

  if (expiredCount === 0 && !hasChart) return null

  return (
    <section aria-label="Insights" className="space-y-3">
      {expiredCount > 0 && (
        <div
          className="flex items-center gap-3 rounded-[var(--radius-lg)] border border-[hsl(var(--warning)/0.4)] bg-[hsl(var(--warning)/0.08)] px-4 py-3"
          role="status"
        >
          <AlertTriangle size={16} className="shrink-0 text-[hsl(var(--warning))]" aria-hidden />
          <p className="text-sm text-[color:var(--ink)]">
            <span className="font-semibold">
              {expiredCount} estimate{expiredCount === 1 ? '' : 's'} expired
            </span>{' '}
            and still open — consider following up or refreshing the quote.
          </p>
          <Link
            href="/estimates?status=expired"
            className="ml-auto shrink-0 text-xs font-semibold text-[hsl(var(--warning))] hover:underline"
          >
            View →
          </Link>
        </div>
      )}

      {hasChart && (
        <div className="rounded-[var(--radius-xl)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-1)] shadow-[var(--shadow-sm)]">
          <button
            type="button"
            onClick={() => setOpen((p) => !p)}
            className="flex w-full items-center gap-2 rounded-[var(--radius-xl)] px-4 py-3 text-left transition-colors hover:bg-[color:var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ring-focus)]"
            aria-expanded={open}
            aria-controls="insights-chart"
          >
            <BarChart3 size={14} className="text-[color:var(--accent-strong)]" aria-hidden />
            <h2 className="flex-1 text-sm font-semibold text-[color:var(--ink)]">
              Estimates this week
            </h2>
            <ChevronDown
              size={16}
              className={cn(
                'text-[color:var(--muted-ink)]',
                !reduce && 'transition-transform duration-200',
                open && 'rotate-180',
              )}
              aria-hidden
            />
          </button>
          {open && (
            <div id="insights-chart" className="border-t border-[color:var(--border-subtle)] p-4">
              <BarChart data={dailyActivity} height={180} barColor="var(--accent-strong)" />
            </div>
          )}
        </div>
      )}
    </section>
  )
}
