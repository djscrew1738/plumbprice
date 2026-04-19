'use client'

import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus, Trash2, FileText, Calendar, MapPin, RefreshCw,
  TrendingUp, Search, ChevronDown, ArrowUpDown, Check, Download, Copy,
} from 'lucide-react'
import { format, isValid } from 'date-fns'
import { cn, formatCurrency } from '@/lib/utils'
import { api } from '@/lib/api'
import { useEstimates, useDeleteEstimate, useDuplicateEstimate } from '@/lib/hooks'
import { useToast } from '@/components/ui/Toast'
import { SearchInput } from '@/components/ui/SearchInput'
import { badgeVariants } from '@/components/ui/Badge'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { Tooltip } from '@/components/ui/Tooltip'

interface Estimate {
  id: number; title: string; job_type: string; status: string
  grand_total: number; confidence_label: string; county: string; created_at: string
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr)
  return isValid(d) ? format(d, 'MMM d, yy') : '—'
}

const JOB_TYPE_CLASS: Record<string, string> = {
  service: 'badge-service', construction: 'badge-construction', commercial: 'badge-commercial',
}
const STATUS_BADGE_VARIANT: Record<string, 'neutral' | 'info' | 'success' | 'danger'> = {
  draft: 'neutral',
  sent: 'info',
  accepted: 'success',
  rejected: 'danger',
}

const STATUS_OPTIONS = [
  { value: 'draft',    label: 'Draft'    },
  { value: 'sent',     label: 'Sent'     },
  { value: 'accepted', label: 'Accepted' },
  { value: 'rejected', label: 'Rejected' },
]

function StatusDropdown({
  estimateId,
  current,
  onChange,
}: {
  estimateId: number
  current: string
  onChange: (id: number, status: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [updating, setUpdating] = useState(false)
  const toast = useToast()

  const handleSelect = async (status: string) => {
    if (status === current) { setOpen(false); return }
    setUpdating(true)
    setOpen(false)
    try {
      await api.patch(`/estimates/${estimateId}/status`, { status })
      onChange(estimateId, status)
    } catch {
      toast.error('Could not update status', 'Please try again.')
    } finally {
      setUpdating(false)
    }
  }

  return (
    <div className="relative" onClick={e => e.stopPropagation()}>
      <button
        onClick={() => setOpen(o => !o)}
        disabled={updating}
        className={cn(
          badgeVariants({ variant: STATUS_BADGE_VARIANT[current] ?? 'neutral', size: 'sm' }),
          'cursor-pointer hover:opacity-80 transition-opacity gap-1',
          updating && 'opacity-50 pointer-events-none',
        )}
      >
        {current}
        <ChevronDown size={9} className={cn('transition-transform', open && 'rotate-180')} />
      </button>
      <AnimatePresence>
        {open && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
            <motion.div
              initial={{ opacity: 0, y: -4, scale: 0.96 }}
              animate={{ opacity: 1, y: 0,  scale: 1    }}
              exit={{   opacity: 0, y: -4,  scale: 0.96 }}
              transition={{ duration: 0.1 }}
              className="absolute top-full left-0 mt-1 bg-[color:var(--panel)] border border-[color:var(--line)] rounded-xl shadow-2xl z-20 overflow-hidden min-w-[110px]"
            >
              {STATUS_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => handleSelect(opt.value)}
                  className={cn(
                    'w-full flex items-center justify-between px-3 py-2 text-xs font-medium transition-colors text-left',
                    opt.value === current
                      ? 'text-[color:var(--accent-strong)] bg-[color:var(--accent-soft)]'
                      : 'text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] hover:bg-[color:var(--panel-strong)]',
                  )}
                >
                  {opt.label}
                  {opt.value === current && <Check size={10} />}
                </button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
const FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'service', label: 'Service' },
  { value: 'construction', label: 'Construction' },
  { value: 'commercial', label: 'Commercial' },
]
type SortKey = 'newest' | 'oldest' | 'highest' | 'lowest'
const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: 'newest',  label: 'Newest first' },
  { value: 'oldest',  label: 'Oldest first' },
  { value: 'highest', label: 'Highest value' },
  { value: 'lowest',  label: 'Lowest value' },
]

export function EstimatesListPage() {
  const router  = useRouter()
  const toast   = useToast()
  const queryClient = useQueryClient()

  const [filter,        setFilter]        = useState('all')
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null)
  const [search,        setSearch]        = useState('')
  const [sortBy,        setSortBy]        = useState<SortKey>('newest')
  const [sortOpen,      setSortOpen]      = useState(false)
  const sortRef = useRef<HTMLDivElement>(null)

  const { data: estimates = [], isLoading: loading, error: queryError, refetch: fetchEstimates } = useEstimates(
    { job_type: filter },
  )
  const deleteMutation = useDeleteEstimate()
  const duplicateMutation = useDuplicateEstimate()

  const deleting = deleteMutation.isPending ? (deleteMutation.variables ?? null) : null
  const duplicating = duplicateMutation.isPending ? (duplicateMutation.variables ?? null) : null

  const error = queryError ? 'Could not load estimates' : null

  // Close sort dropdown when clicking outside
  useEffect(() => {
    if (!sortOpen) return
    const handler = (e: MouseEvent) => {
      if (sortRef.current && !sortRef.current.contains(e.target as Node)) {
        setSortOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [sortOpen])

  const handleStatusChange = useCallback((id: number, status: string) => {
    queryClient.setQueryData<Estimate[]>(['estimates', { filter }], prev =>
      prev?.map(e => e.id === id ? { ...e, status } : e)
    )
  }, [queryClient, filter])

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
      const q = search.toLowerCase()
      return !q || (e.title ?? '').toLowerCase().includes(q) || e.county.toLowerCase().includes(q)
    })
    switch (sortBy) {
      case 'newest':  list = [...list].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()); break
      case 'oldest':  list = [...list].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()); break
      case 'highest': list = [...list].sort((a, b) => b.grand_total - a.grand_total); break
      case 'lowest':  list = [...list].sort((a, b) => a.grand_total - b.grand_total); break
    }
    return list
  }, [estimates, search, sortBy])

  const { totalValue, avgValue } = useMemo(() => {
    const total = visible.reduce((s, e) => s + (e.grand_total || 0), 0)
    return { totalValue: total, avgValue: visible.length > 0 ? total / visible.length : 0 }
  }, [visible])

  const currentSortLabel = SORT_OPTIONS.find(o => o.value === sortBy)?.label ?? 'Sort'

  return (
    <div className="min-h-full bg-[hsl(var(--background))]">

      {/* ── Top bar ── */}
      <div className="bg-[color:var(--panel)]/80 backdrop-blur-xl border-b border-[color:var(--line)] px-4 py-2.5 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto space-y-2.5">
          <div className="flex items-center justify-between gap-3">
            {/* Filter pills */}
            <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-hide">
              {FILTERS.map(f => (
                <button
                  key={f.value}
                  onClick={() => setFilter(f.value)}
                  aria-pressed={filter === f.value}
                  className={cn(
                    'px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all',
                    filter === f.value
                      ? 'bg-[color:var(--accent)] text-white'
                      : 'bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] hover:bg-[color:var(--panel-strong)] border border-[color:var(--line)]',
                  )}
                >
                  {f.label}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Tooltip content="Export visible estimates as CSV">
                <button
                  onClick={() => {
                    const rows = [
                      ['ID', 'Title', 'Job Type', 'Status', 'County', 'Grand Total', 'Confidence', 'Created'],
                      ...visible.map(e => [
                        String(e.id), e.title, e.job_type, e.status, e.county,
                        String(e.grand_total), e.confidence_label,
                        new Date(e.created_at).toLocaleDateString(),
                      ]),
                    ]
                    const csv = rows.map(r => r.map(v => `"${v.replace(/"/g, '""')}"`).join(',')).join('\n')
                    const a = Object.assign(document.createElement('a'), {
                      href: URL.createObjectURL(new Blob([csv], { type: 'text/csv' })),
                      download: 'estimates.csv',
                    })
                    a.click()
                  }}
                  className="flex items-center gap-1.5 px-2.5 py-2 rounded-xl hover:bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
                  aria-label="Export CSV"
                >
                  <Download size={15} />
                  <span className="hidden sm:inline text-xs font-medium">Export</span>
                </button>
              </Tooltip>
              <button onClick={() => void fetchEstimates()} className="p-2 rounded-xl hover:bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors" aria-label="Refresh estimates">
                <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
              </button>
              <Tooltip content="New estimate (N)">
                <button onClick={() => router.push('/estimator')} className="btn-primary px-3 py-2" aria-label="New estimate">
                  <Plus size={15} /><span className="hidden sm:inline">New</span>
                </button>
              </Tooltip>
            </div>
          </div>

          {/* Search + sort row */}
          <div className="flex gap-2">
            <SearchInput
              value={search}
              onChange={setSearch}
              placeholder="Search by title or county…"
              className="flex-1"
              aria-label="Search estimates"
            />
            {/* Sort dropdown */}
            <div className="relative" ref={sortRef}>
              <button
                onClick={() => setSortOpen(o => !o)}
                className="flex items-center gap-1.5 px-3 py-2 bg-[color:var(--panel-strong)] border border-[color:var(--line)] rounded-xl text-xs font-medium text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] hover:bg-[color:var(--panel-strong)] transition-all whitespace-nowrap"
              >
                <ArrowUpDown size={13} />
                <span className="hidden sm:inline">{currentSortLabel}</span>
                <ChevronDown size={11} className={cn('text-[color:var(--muted-ink)] transition-transform', sortOpen && 'rotate-180')} />
              </button>
              <AnimatePresence>
                {sortOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -6, scale: 0.96 }}
                    animate={{ opacity: 1, y: 0,  scale: 1    }}
                    exit={{   opacity: 0, y: -6,  scale: 0.96 }}
                    transition={{ duration: 0.12 }}
                    className="absolute top-full right-0 mt-1.5 bg-[color:var(--panel)] border border-[color:var(--line)] rounded-xl shadow-2xl overflow-hidden z-20 min-w-[152px]"
                  >
                    {SORT_OPTIONS.map(o => (
                      <button
                        key={o.value}
                        onClick={() => { setSortBy(o.value); setSortOpen(false) }}
                        className={cn(
                          'w-full text-left px-3.5 py-2 text-xs font-medium transition-colors',
                          o.value === sortBy ? 'text-[color:var(--accent-strong)] bg-[color:var(--accent-soft)]' : 'text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] hover:bg-[color:var(--panel-strong)]',
                        )}
                      >
                        {o.label}
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-4">

        {/* Summary stats */}
        {!loading && visible.length > 0 && (
          <div className="grid grid-cols-3 gap-3 mb-4">
            {[
              { label: 'Showing',     value: visible.length.toString(), icon: FileText,   color: 'text-[hsl(var(--info))]',           bg: 'bg-[hsl(var(--info)/0.1)] border-[hsl(var(--info)/0.2)]' },
              { label: 'Total Value', value: formatCurrency(totalValue), icon: TrendingUp, color: 'text-[hsl(var(--success))]',        bg: 'bg-[hsl(var(--success)/0.1)] border-[hsl(var(--success)/0.2)]' },
              { label: 'Avg Value',   value: formatCurrency(avgValue),   icon: MapPin,     color: 'text-[color:var(--accent-strong)]', bg: 'bg-[color:var(--accent-soft)] border-[color:var(--accent)]/20' },
            ].map(({ label, value, icon: Icon, color, bg }) => (
              <div key={label} className="card p-3.5 flex items-center gap-3">
                <div className={cn('w-9 h-9 rounded-xl flex items-center justify-center border shrink-0', bg)}>
                  <Icon size={14} className={color} />
                </div>
                <div className="min-w-0">
                  <div className="text-[10px] text-[color:var(--muted-ink)] font-bold tracking-tight">{label}</div>
                  <div className="text-sm font-bold text-[color:var(--ink)] truncate">{value}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="space-y-2.5">
            {[1,2,3,4].map(i => (
              <div key={i} className="card p-4 space-y-2.5">
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
              title="No estimates yet"
              description="Chat with the estimator to generate your first price."
              action={
                <button onClick={() => router.push('/estimator')} className="btn-primary">
                  Start Estimating
                </button>
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
              description={`No estimates match \u201c${search}\u201d`}
              action={
                <button onClick={() => setSearch('')} className="btn-ghost text-xs">
                  Clear search
                </button>
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
                    className="card p-4 cursor-pointer hover:border-[color:var(--line)] hover:-translate-y-0.5 hover:shadow-md transition-all"
                    onClick={() => router.push(`/estimates/${est.id}`)}
                  >
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-[color:var(--ink)] text-sm truncate mb-1.5 flex items-center gap-1.5">
  {est.title || `Estimate #${est.id}`}
  {est.outcome && (
    <span
      className={cn(
        'ml-2 px-2 py-0.5 rounded-full text-[11px] font-semibold border',
        est.outcome === 'won' && 'bg-emerald-50 text-emerald-700 border-emerald-200',
        est.outcome === 'lost' && 'bg-red-50 text-red-700 border-red-200',
        est.outcome === 'no_bid' && 'bg-zinc-50 text-zinc-600 border-zinc-200',
        est.outcome === 'pending' && 'bg-yellow-50 text-yellow-700 border-yellow-200',
      )}
      role="status"
    >
      {est.outcome === 'won' ? 'Won' : est.outcome === 'lost' ? 'Lost' : est.outcome === 'no_bid' ? 'No Bid' : 'Pending'}
    </span>
  )}
</h3>
<div className="flex items-center gap-1.5 flex-wrap">
  <span className={cn('badge', JOB_TYPE_CLASS[est.job_type] ?? 'badge-service')}>{est.job_type}</span>
  <StatusDropdown estimateId={est.id} current={est.status} onChange={handleStatusChange} />
  <span className={cn('badge', 'badge-' + (est.confidence_label?.toLowerCase() ?? 'high'))}>{est.confidence_label ?? 'HIGH'}</span>
</div>
                      </div>
                      <div className="text-xl font-extrabold text-[color:var(--ink)] shrink-0 tabular-nums">{formatCurrency(est.grand_total)}</div>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 text-[11px] text-[color:var(--muted-ink)]">
                        <span className="flex items-center gap-1"><MapPin size={10} />{est.county}</span>
                        <span className="flex items-center gap-1"><Calendar size={10} />{formatDate(est.created_at)}</span>
                      </div>
                      <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                        {confirmDelete === est.id ? (
                          <div className="flex items-center gap-1.5">
                            <span className="text-[11px] text-[hsl(var(--danger))] font-medium">Delete?</span>
                            <button
                              onClick={() => void handleDeleteConfirm(est.id)}
                              disabled={deleting === est.id}
                              className="px-2 py-1 rounded-lg bg-[hsl(var(--danger)/0.15)] text-[hsl(var(--danger))] text-[11px] font-semibold hover:bg-[hsl(var(--danger)/0.25)] transition-colors disabled:opacity-40"
                            >Yes</button>
                            <button
                              onClick={() => setConfirmDelete(null)}
                              className="px-2 py-1 rounded-lg bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)] text-[11px] font-semibold hover:bg-[color:var(--panel-strong)] transition-colors"
                            >No</button>
                          </div>
                        ) : (
                          <>
                            <Tooltip content="Duplicate">
                              <button
                                onClick={e => handleDuplicate(est.id, e)}
                                disabled={duplicating === est.id}
                                className="p-2 rounded-xl hover:bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors disabled:opacity-40"
                                aria-label="Duplicate estimate"
                              >
                                {duplicating === est.id ? <RefreshCw size={13} className="animate-spin" /> : <Copy size={13} />}
                              </button>
                            </Tooltip>
                            <Tooltip content="Delete">
                              <button
                                onClick={e => { e.stopPropagation(); setConfirmDelete(est.id) }}
                                disabled={deleting === est.id}
                                className="p-2 rounded-xl hover:bg-[hsl(var(--danger)/0.1)] text-[color:var(--muted-ink)] hover:text-[hsl(var(--danger))] transition-colors disabled:opacity-40"
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
                        className="hover:bg-[color:var(--panel-strong)] hover:shadow-sm transition-all group cursor-pointer"
                        role="row"
                        onClick={() => router.push(`/estimates/${est.id}`)}
                      >
                        <td className="px-4 py-3 font-medium text-[color:var(--ink)] max-w-[180px] truncate flex items-center gap-1.5">
  {est.title || `Estimate #${est.id}`}
  {est.outcome && (
    <span
      className={cn(
        'ml-2 px-2 py-0.5 rounded-full text-[11px] font-semibold border',
        est.outcome === 'won' && 'bg-emerald-50 text-emerald-700 border-emerald-200',
        est.outcome === 'lost' && 'bg-red-50 text-red-700 border-red-200',
        est.outcome === 'no_bid' && 'bg-zinc-50 text-zinc-600 border-zinc-200',
        est.outcome === 'pending' && 'bg-yellow-50 text-yellow-700 border-yellow-200',
      )}
      role="status"
    >
      {est.outcome === 'won' ? 'Won' : est.outcome === 'lost' ? 'Lost' : est.outcome === 'no_bid' ? 'No Bid' : 'Pending'}
    </span>
  )}
</td>
                        <td className="px-4 py-3"><span className={cn('badge', JOB_TYPE_CLASS[est.job_type] ?? 'badge-service')}>{est.job_type}</span></td>
                        <td className="px-4 py-3"><StatusDropdown estimateId={est.id} current={est.status} onChange={handleStatusChange} /></td>
                        <td className="px-4 py-3"><span className={cn('badge', 'badge-' + (est.confidence_label?.toLowerCase() ?? 'high'))}>{est.confidence_label ?? 'HIGH'}</span></td>
                        <td className="px-4 py-3 text-[color:var(--muted-ink)] text-xs">{est.county}</td>
                        <td className="px-4 py-3 font-bold text-[color:var(--ink)] tabular-nums">{formatCurrency(est.grand_total)}</td>
                        <td className="px-4 py-3 text-[color:var(--muted-ink)] text-xs whitespace-nowrap">{formatDate(est.created_at)}</td>
                        <td className="px-4 py-3">
                          <div className={cn('flex items-center gap-1 transition-opacity', confirmDelete === est.id ? 'opacity-100' : 'opacity-0 group-hover:opacity-100')} onClick={e => e.stopPropagation()}>
                            {confirmDelete === est.id ? (
                              <>
                                <span className="text-[11px] text-[hsl(var(--danger))] font-medium mr-1">Delete?</span>
                                <button
                                  onClick={() => void handleDeleteConfirm(est.id)}
                                  disabled={deleting === est.id}
                                  className="px-2 py-1 rounded-lg bg-[hsl(var(--danger)/0.15)] text-[hsl(var(--danger))] text-[11px] font-semibold hover:bg-[hsl(var(--danger)/0.25)] transition-colors disabled:opacity-40"
                                >Yes</button>
                                <button
                                  onClick={() => setConfirmDelete(null)}
                                  className="px-2 py-1 rounded-lg bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)] text-[11px] font-semibold hover:bg-[color:var(--panel-strong)] transition-colors"
                                >No</button>
                              </>
                            ) : (
                              <>
                                <button
                                  onClick={e => handleDuplicate(est.id, e)}
                                  disabled={duplicating === est.id}
                                  className="flex min-h-[32px] min-w-[32px] items-center justify-center rounded-lg p-2 hover:bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors disabled:opacity-40"
                                  aria-label="Duplicate estimate"
                                >
                                  {duplicating === est.id ? <RefreshCw size={12} className="animate-spin" /> : <Copy size={12} />}
                                </button>
                                <button
                                  onClick={e => { e.stopPropagation(); setConfirmDelete(est.id) }}
                                  disabled={deleting === est.id}
                                  className="flex min-h-[32px] min-w-[32px] items-center justify-center rounded-lg p-2 hover:bg-[hsl(var(--danger)/0.1)] text-[color:var(--muted-ink)] hover:text-[hsl(var(--danger))] transition-colors disabled:opacity-40"
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
    </div>
  )
}
