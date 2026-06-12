'use client'

import { useState, useCallback, useMemo } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus, Trash2, FileText, Calendar, MapPin,
  RefreshCw, Copy, AlertTriangle, Search,
} from 'lucide-react'
import { cn, formatCurrency } from '@/lib/utils'
import { useEstimates, useDeleteEstimate, useDuplicateEstimate, estimateKeys } from '@/lib/hooks'
import { useToast } from '@/components/ui/Toast'
import { haptic } from '@/lib/haptics'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { Tooltip } from '@/components/ui/Tooltip'
import { formatDateShort } from '@/lib/formatters'
import { JOB_TYPE_CLASS } from '@/lib/badgeConfig'
import { PageShell, PageHeader } from '@/components/layout/shell'
import { downloadCsv } from '@/lib/download-csv'
import { useCommandPaletteEvent } from '@/lib/hooks/useCommandPaletteEvent'
import { EstimateStatusDropdown } from './EstimateStatusDropdown'
import { EstimateOutcomeBadge } from './EstimateOutcomeBadge'
import { EstimateListFilters, type SortKey } from './EstimateListFilters'
import { EstimateSummaryStats } from './EstimateSummaryStats'

interface Estimate {
  id: number; title: string; job_type: string; status: string
  grand_total: number; confidence_label: string; county: string; created_at: string
  outcome?: string | null; is_expired?: boolean | null; valid_until?: string | null
}

export function EstimatesListPage() {
  const router  = useRouter()
  const searchParams = useSearchParams()
  const toast   = useToast()
  const queryClient = useQueryClient()

  const initialStatus = searchParams.get('status') ?? 'all'
  const [filter,        setFilter]        = useState('all')
  const [statusFilter,  setStatusFilter]  = useState(
    ['draft', 'sent', 'accepted', 'rejected'].includes(initialStatus) ? initialStatus : 'all'
  )
  const [expiredOnly,   setExpiredOnly]   = useState(initialStatus === 'expired')
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null)
  const [search,        setSearch]        = useState('')
  const [sortBy,        setSortBy]        = useState<SortKey>('newest')

  const { data: estimates = [], isLoading: loading, error: queryError, refetch: fetchEstimates } = useEstimates(
    { job_type: filter !== 'all' ? filter : undefined, status: statusFilter !== 'all' ? statusFilter : undefined },
  )
  const deleteMutation = useDeleteEstimate()
  const duplicateMutation = useDuplicateEstimate()

  const deleting = deleteMutation.isPending ? (deleteMutation.variables ?? null) : null
  const duplicating = duplicateMutation.isPending ? (duplicateMutation.variables ?? null) : null

  const error = queryError ? 'Could not load estimates' : null

  const handleStatusChange = useCallback((id: number, status: string) => {
    queryClient.setQueriesData<Estimate[]>({ queryKey: estimateKeys.lists() }, prev =>
      prev?.map(e => e.id === id ? { ...e, status } : e)
    )
  }, [queryClient])

  const handleDeleteConfirm = useCallback((id: number) => {
    setConfirmDelete(null)
    deleteMutation.mutate(id, {
      onSuccess: () => toast.success('Estimate deleted'),
      onError: () => toast.error('Failed to delete', 'Please try again.'),
    })
  }, [deleteMutation, toast])

  const handleDuplicate = useCallback((id: number, e: React.MouseEvent) => {
    e.stopPropagation()
    duplicateMutation.mutate(id, {
      onSuccess: (copy) => toast.success('Estimate duplicated', copy.title || `Estimate #${copy.id}`),
      onError: () => toast.error('Could not duplicate', 'Please try again.'),
    })
  }, [duplicateMutation, toast])

  const visible = useMemo(() => {
    let list = estimates.filter(e => {
      if (expiredOnly && !e.is_expired) return false
      const q = search.toLowerCase()
      return !q || (e.title ?? '').toLowerCase().includes(q) || e.county.toLowerCase().includes(q) || e.status.toLowerCase().includes(q)
    })
    switch (sortBy) {
      case 'newest':  list = [...list].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()); break
      case 'oldest':  list = [...list].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()); break
      case 'highest': list = [...list].sort((a, b) => b.grand_total - a.grand_total); break
      case 'lowest':  list = [...list].sort((a, b) => a.grand_total - b.grand_total); break
    }
    return list
  }, [estimates, search, sortBy, expiredOnly])

  const { totalValue, avgValue } = useMemo(() => {
    const total = visible.reduce((s, e) => s + (e.grand_total || 0), 0)
    return { totalValue: total, avgValue: visible.length > 0 ? total / visible.length : 0 }
  }, [visible])

  const handleExportCsv = useCallback(() => {
    downloadCsv(
      visible.map(e => ({
        ID: e.id,
        Title: e.title,
        'Job Type': e.job_type,
        Status: e.status,
        County: e.county,
        'Grand Total': e.grand_total,
        Confidence: e.confidence_label,
        Created: new Date(e.created_at).toLocaleDateString(),
      })),
      'estimates.csv'
    )
  }, [visible])

  useCommandPaletteEvent('trigger-csv-export', handleExportCsv)

  const clearStatus = () => {
    setStatusFilter('all')
    setExpiredOnly(false)
  }

  return (
    <PageShell width="default">
      <PageHeader
        eyebrow="Saved Estimates"
        title="Continue active bids"
        description="Review finished pricing work, reopen drafts, and move back into the workspace with one tap."
        actions={
          <Tooltip content="New estimate (N)">
            <button onClick={() => router.push('/estimator')} className="shell-button-primary px-4 py-2.5" aria-label="New estimate">
              <Plus size={15} /><span className="hidden sm:inline">New estimate</span>
            </button>
          </Tooltip>
        }
      />

      <EstimateListFilters
        filter={filter}
        onFilterChange={setFilter}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        expiredOnly={expiredOnly}
        onExpiredOnlyChange={setExpiredOnly}
        search={search}
        onSearchChange={setSearch}
        sortBy={sortBy}
        onSortChange={setSortBy}
        loading={loading}
        onExport={handleExportCsv}
        onRefresh={() => void fetchEstimates()}
        onNew={() => router.push('/estimator')}
      />

      <div className="mx-auto max-w-5xl px-4 py-4">

        {/* Summary stats */}
        {!loading && visible.length > 0 && (
          <EstimateSummaryStats count={visible.length} totalValue={totalValue} avgValue={avgValue} />
        )}

        {/* Loading */}
        {loading && (
          <div className="space-y-2.5">
            {[1,2,3,4].map(i => (
              <div key={i} className="card space-y-2.5 p-4">
                <div className="skeleton h-3.5 w-2/3 rounded-lg" />
                <div className="skeleton h-7 w-1/3 rounded-lg" />
                <div className="skeleton h-3 w-1/2 rounded-lg" />
              </div>
            ))}
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div className="card">
            <ErrorState message={error} onRetry={() => void fetchEstimates()} />
          </div>
        )}

        {/* Empty */}
        {!loading && !error && estimates.length === 0 && (
          <div className="card">
            <EmptyState
              icon={<FileText size={20} />}
              title={expiredOnly ? 'No expired estimates' : statusFilter !== 'all' ? `No ${statusFilter} estimates` : 'No estimates yet'}
              description={
                expiredOnly
                  ? 'No estimates have expired.'
                  : statusFilter !== 'all'
                  ? `No estimates with status "${statusFilter}"${filter !== 'all' ? ` for ${filter} jobs` : ''}.`
                  : 'Chat with the estimator to generate your first price.'
              }
              action={
                expiredOnly || statusFilter !== 'all' ? (
                  <button onClick={clearStatus} className="btn-ghost text-xs">
                    Show all statuses
                  </button>
                ) : (
                  <button onClick={() => router.push('/estimator')} className="btn-primary">
                    Start Estimating
                  </button>
                )
              }
            />
          </div>
        )}

        {/* No search results */}
        {!loading && !error && estimates.length > 0 && visible.length === 0 && (
          <div className="card">
            <EmptyState
              icon={<Search size={20} />}
              title="No matches"
              description={search ? `No estimates match "${search}"` : 'No estimates match the active filters.'}
              action={
                <div className="flex items-center gap-2">
                  {search && (
                    <button onClick={() => setSearch('')} className="btn-ghost text-xs">
                      Clear search
                    </button>
                  )}
                  {(statusFilter !== 'all' || expiredOnly) && (
                    <button onClick={clearStatus} className="btn-ghost text-xs">
                      Clear status filter
                    </button>
                  )}
                </div>
              }
            />
          </div>
        )}

        {/* Data */}
        {!loading && !error && visible.length > 0 && (
          <>
            {/* Mobile cards */}
            <div className="space-y-2.5 lg:hidden">
              <AnimatePresence initial={false}>
                {visible.map((est, i) => (
                  <motion.div
                    key={est.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.97 }}
                    transition={{ duration: 0.18, delay: i * 0.02 }}
                    className="card cursor-pointer p-4 transition-all hover:-translate-y-0.5 hover:border-[color:var(--line)] hover:shadow-md"
                    onClick={() => router.push(`/estimates/${est.id}`)}
                  >
                    <div className="mb-3 flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <h3 className="mb-1.5 flex items-center gap-1.5 truncate text-sm font-semibold text-[color:var(--ink)]">
                          {est.title || `Estimate #${est.id}`}
                          {est.outcome && <EstimateOutcomeBadge outcome={est.outcome} />}
                        </h3>
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className={cn('badge', JOB_TYPE_CLASS[est.job_type] ?? 'badge-service')}>{est.job_type}</span>
                          <EstimateStatusDropdown estimateId={est.id} current={est.status} onChange={handleStatusChange} />
                          <span className={cn('badge', 'badge-' + (est.confidence_label?.toLowerCase() ?? 'high'))}>{est.confidence_label ?? 'HIGH'}</span>
                        </div>
                      </div>
                      <div className="shrink-0 text-xl font-extrabold tabular-nums text-[color:var(--ink)]">{formatCurrency(est.grand_total)}</div>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 text-[11px] text-[color:var(--muted-ink)]">
                        <span className="flex items-center gap-1"><MapPin size={10} />{est.county}</span>
                        <span className="flex items-center gap-1"><Calendar size={10} />{formatDateShort(est.created_at)}</span>
                        {est.is_expired && (
                          <Tooltip content="This estimate has expired">
                            <span className="flex items-center gap-0.5 text-[hsl(var(--warning))]">
                              <AlertTriangle size={10} />
                              Expired
                            </span>
                          </Tooltip>
                        )}
                      </div>
                      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions */}
                      <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                        {confirmDelete === est.id ? (
                          <div className="flex items-center gap-1.5">
                            <span className="text-[11px] font-medium text-[hsl(var(--danger))]">Delete?</span>
                            <button
                              onClick={() => void handleDeleteConfirm(est.id)}
                              disabled={deleting === est.id}
                              className="rounded-lg bg-[hsl(var(--danger)/0.15)] px-2 py-1 text-[11px] font-semibold text-[hsl(var(--danger))] transition-colors hover:bg-[hsl(var(--danger)/0.25)] disabled:opacity-40"
                            >Yes</button>
                            <button
                              onClick={() => setConfirmDelete(null)}
                              className="rounded-lg bg-[color:var(--panel-strong)] px-2 py-1 text-[11px] font-semibold text-[color:var(--muted-ink)] transition-colors hover:bg-[color:var(--panel-strong)]"
                            >No</button>
                          </div>
                        ) : (
                          <>
                            <Tooltip content="Duplicate">
                              <button
                                onClick={e => {
                                  haptic('tap')
                                  handleDuplicate(est.id, e)
                                }}
                                disabled={duplicating === est.id}
                                className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl p-2.5 text-[color:var(--muted-ink)] transition-colors hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)] disabled:opacity-40"
                                aria-label="Duplicate estimate"
                              >
                                {duplicating === est.id ? <RefreshCw size={13} className="animate-spin" /> : <Copy size={13} />}
                              </button>
                            </Tooltip>
                            <Tooltip content="Delete">
                              <button
                                onClick={e => {
                                  e.stopPropagation()
                                  haptic('error')
                                  setConfirmDelete(est.id)
                                }}
                                disabled={deleting === est.id}
                                className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl p-2.5 text-[color:var(--muted-ink)] transition-colors hover:bg-[hsl(var(--danger)/0.1)] hover:text-[hsl(var(--danger))] disabled:opacity-40"
                                aria-label="Delete estimate"
                              >
                                <Trash2 size={14} />
                              </button>
                            </Tooltip>
                          </>
                        )}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>

            {/* Desktop table */}
            <div className="hidden lg:block card overflow-hidden">
              <table className="w-full text-sm" role="table">
                <thead>
                  <tr role="row" className="border-b border-[color:var(--line)] bg-[color:var(--panel-strong)]">
                    {['Title', 'Type', 'Status', 'Confidence', 'County', 'Total', 'Date', ''].map(h => (
                      <th key={h} role="columnheader" className="px-4 py-3 text-left text-[11px] font-bold text-[color:var(--muted-ink)] transition-colors group-hover:text-[color:var(--ink)]">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[color:var(--line)]">
                  <AnimatePresence initial={false}>
                    {visible.map((est, i) => (
                      <motion.tr
                        key={est.id}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.12, delay: i * 0.015 }}
                        className="group cursor-pointer transition-all hover:bg-[color:var(--panel-strong)] hover:shadow-sm"
                        role="row"
                        onClick={() => router.push(`/estimates/${est.id}`)}
                      >
                        <td className="flex max-w-[180px] items-center gap-1.5 truncate px-4 py-3 font-medium text-[color:var(--ink)]">
                          {est.title || `Estimate #${est.id}`}
                          {est.outcome && <EstimateOutcomeBadge outcome={est.outcome} />}
                        </td>
                        <td className="px-4 py-3"><span className={cn('badge', JOB_TYPE_CLASS[est.job_type] ?? 'badge-service')}>{est.job_type}</span></td>
                        <td className="px-4 py-3"><EstimateStatusDropdown estimateId={est.id} current={est.status} onChange={handleStatusChange} /></td>
                        <td className="px-4 py-3"><span className={cn('badge', 'badge-' + (est.confidence_label?.toLowerCase() ?? 'high'))}>{est.confidence_label ?? 'HIGH'}</span></td>
                        <td className="px-4 py-3 text-xs text-[color:var(--muted-ink)]">{est.county}</td>
                        <td className="px-4 py-3 font-bold tabular-nums text-[color:var(--ink)]">{formatCurrency(est.grand_total)}</td>
                        <td className="whitespace-nowrap px-4 py-3 text-xs text-[color:var(--muted-ink)]">
                          <span>{formatDateShort(est.created_at)}</span>
                          {est.is_expired && (
                            <Tooltip content="This estimate has expired">
                              <span className="ml-1.5 inline-flex items-center gap-0.5 text-[10px] font-semibold text-[hsl(var(--warning))]">
                                <AlertTriangle size={10} />Expired
                              </span>
                            </Tooltip>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions */}
                          <div className={cn('flex items-center gap-1 transition-opacity', confirmDelete === est.id ? 'opacity-100' : 'opacity-0 group-hover:opacity-100')} onClick={e => e.stopPropagation()}>
                            {confirmDelete === est.id ? (
                              <>
                                <span className="mr-1 text-[11px] font-medium text-[hsl(var(--danger))]">Delete?</span>
                                <button
                                  onClick={() => void handleDeleteConfirm(est.id)}
                                  disabled={deleting === est.id}
                                  className="rounded-lg bg-[hsl(var(--danger)/0.15)] px-2 py-1 text-[11px] font-semibold text-[hsl(var(--danger))] transition-colors hover:bg-[hsl(var(--danger)/0.25)] disabled:opacity-40"
                                >Yes</button>
                                <button
                                  onClick={() => setConfirmDelete(null)}
                                  className="rounded-lg bg-[color:var(--panel-strong)] px-2 py-1 text-[11px] font-semibold text-[color:var(--muted-ink)] transition-colors hover:bg-[color:var(--panel-strong)]"
                                >No</button>
                              </>
                            ) : (
                              <>
                                <button
                                  onClick={e => handleDuplicate(est.id, e)}
                                  disabled={duplicating === est.id}
                                  className="flex min-h-[32px] min-w-[32px] items-center justify-center rounded-lg p-2 text-[color:var(--muted-ink)] transition-colors hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)] disabled:opacity-40"
                                  aria-label="Duplicate estimate"
                                >
                                  {duplicating === est.id ? <RefreshCw size={12} className="animate-spin" /> : <Copy size={12} />}
                                </button>
                                <button
                                  onClick={e => { e.stopPropagation(); setConfirmDelete(est.id) }}
                                  disabled={deleting === est.id}
                                  className="flex min-h-[32px] min-w-[32px] items-center justify-center rounded-lg p-2 text-[color:var(--muted-ink)] transition-colors hover:bg-[hsl(var(--danger)/0.1)] hover:text-[hsl(var(--danger))] disabled:opacity-40"
                                  aria-label="Delete estimate"
                                >
                                  <Trash2 size={13} />
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </PageShell>
  )
}
