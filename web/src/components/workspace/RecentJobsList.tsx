'use client'

import Link from 'next/link'
import { RefreshCw } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useQuery } from '@tanstack/react-query'
import type { EstimateListItem } from '@/lib/api'
import { estimatesApi } from '@/lib/api'
import { cn, formatCurrency } from '@/lib/utils'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { Inbox } from 'lucide-react'

const STATUS_LABELS: Record<string, string> = {
  draft: 'Awaiting details',
  pending: 'Awaiting details',
  needs_info: 'Awaiting details',
  sent: 'Estimate sent',
  estimate_sent: 'Estimate sent',
  accepted: 'Estimate ready',
  ready: 'Estimate ready',
  completed: 'Estimate ready',
  won: 'Estimate ready',
  rejected: 'Not won',
  lost: 'Not won',
}

function normalizeRecentJobs(data: EstimateListItem[] | { estimates?: EstimateListItem[] }): EstimateListItem[] {
  const items = Array.isArray(data) ? data : data.estimates ?? []

  return [...items].sort((a, b) => {
    const aTime = new Date(a.created_at).getTime()
    const bTime = new Date(b.created_at).getTime()
    return (Number.isFinite(bTime) ? bTime : 0) - (Number.isFinite(aTime) ? aTime : 0)
  })
}

function formatRelativeDate(value: string) {
  const date = new Date(value)
  if (!Number.isFinite(date.getTime())) {
    return 'Unknown date'
  }

  return formatDistanceToNow(date, { addSuffix: true })
}

function humanizeStatus(status: string) {
  return status
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, char => char.toUpperCase())
}

export function getEstimateStatusLabel(status: string) {
  const key = status.trim().toLowerCase()
  return STATUS_LABELS[key] ?? humanizeStatus(key)
}

interface RecentJobsListProps {
  compact?: boolean
  heading?: string
  limit?: number
  className?: string
}

export function RecentJobsList({ compact = false, heading = 'Recent jobs', limit = 5, className }: RecentJobsListProps) {
  const { data, isLoading: loading, isError, refetch } = useQuery({
    queryKey: ['estimates'],
    queryFn: () => estimatesApi.list(),
  })
  const jobs = data ? normalizeRecentJobs(data.data).slice(0, limit) : []
  const error = isError ? 'Could not load recent jobs' : null

  return (
    <section className={cn(compact ? 'space-y-2' : 'shell-panel space-y-3 p-5', className)}>
      <div className="flex items-center justify-between gap-2 border-b border-[color:var(--line)] pb-3 mb-2">
        <h2 className={cn('font-bold tracking-tight text-[color:var(--ink)]', compact ? 'text-xs' : 'text-lg')}>
          {heading}
        </h2>
        <Link
          href="/estimates"
          className={cn('shrink-0 text-[color:var(--accent)] hover:underline transition-colors', compact ? 'text-[10px]' : 'text-xs')}
        >
          View all →
        </Link>
      </div>

      {loading && (
        <div className={cn('space-y-2', compact && 'space-y-1.5')}>
          <Skeleton
            variant={compact ? 'table-row' : 'card'}
            count={compact ? 3 : 4}
            className={cn('rounded-lg', compact ? 'h-12' : 'h-16')}
          />
        </div>
      )}

      {!loading && error && (
        <div className={cn('rounded-xl border border-[color:var(--line)] bg-[color:var(--panel-strong)] p-3', compact ? 'text-xs' : 'text-sm')}>
          <p className="text-[color:var(--muted-ink)]">{error}</p>
          <button
            type="button"
            onClick={() => void refetch()}
            className="mt-2 flex items-center gap-1.5 text-[color:var(--accent-strong)] hover:underline"
          >
            <RefreshCw size={12} />
            Try again
          </button>
        </div>
      )}

      {!loading && !error && jobs.length === 0 && (
        <EmptyState
          icon={<Inbox size={22} />}
          title="No estimates yet"
          description="No estimates yet — start with a pricing question or upload a blueprint."
          className={compact ? 'py-4' : 'py-6'}
        />
      )}

      {!loading && !error && jobs.length > 0 && (
        <ul className={cn('space-y-2', compact && 'space-y-1.5')}>
          {jobs.map(job => (
            <li key={job.id} className="rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)]">
              <Link
                href={`/estimates/${job.id}`}
                className={cn(
                  'group block rounded-xl transition-colors hover:bg-[color:var(--panel-strong)]',
                  compact ? 'px-2.5 py-2' : 'px-3 py-2.5'
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className={cn('truncate font-medium text-[color:var(--ink)]', compact ? 'text-xs' : 'text-sm')}>
                      {job.title || `Estimate #${job.id}`}
                    </p>
                    <p className={cn('truncate text-[color:var(--muted-ink)]', compact ? 'text-[11px]' : 'text-xs')}>
                      {getEstimateStatusLabel(job.status)}
                    </p>
                  </div>
                  <p className={cn('shrink-0 font-semibold text-[color:var(--ink)]', compact ? 'text-[11px]' : 'text-xs')}>
                    {formatCurrency(job.grand_total)}
                  </p>
                </div>
                <p className={cn('mt-1 text-[color:var(--muted-ink)]', compact ? 'text-[10px]' : 'text-[11px]')}>
                  {formatRelativeDate(job.created_at)}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
