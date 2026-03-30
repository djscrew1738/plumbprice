'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus, Trash2, FileText, Calendar, MapPin, RefreshCw,
  TrendingUp, Search, X, ChevronDown, ArrowUpDown,
} from 'lucide-react'
import { format, isValid } from 'date-fns'
import { cn, formatCurrency } from '@/lib/utils'
import { api } from '@/lib/api'
import { useToast } from '@/components/ui/Toast'
import { PageIntro } from '@/components/layout/PageIntro'

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
const STATUS_CLASS: Record<string, string> = {
  draft: 'border-[color:var(--line)] bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)]',
  sent: 'bg-blue-500/10 text-blue-700 border border-blue-500/20',
  accepted: 'bg-emerald-500/10 text-emerald-700 border border-emerald-500/20',
  rejected: 'bg-red-500/10 text-red-700 border border-red-500/20',
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

  const [estimates, setEstimates] = useState<Estimate[]>([])
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState<string | null>(null)
  const [filter,    setFilter]    = useState('all')
  const [deleting,  setDeleting]  = useState<number | null>(null)
  const [search,    setSearch]    = useState('')
  const [sortBy,    setSortBy]    = useState<SortKey>('newest')
  const [sortOpen,  setSortOpen]  = useState(false)

  const fetchEstimates = useCallback(async () => {
    try {
      setLoading(true); setError(null)
      const params = filter !== 'all' ? { job_type: filter } : {}
      const res = await api.get('/estimates', { params })
      setEstimates(res.data.estimates ?? res.data ?? [])
    } catch {
      setError('Could not load estimates')
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => { fetchEstimates() }, [fetchEstimates])

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this estimate?')) return
    setDeleting(id)
    try {
      await api.delete(`/estimates/${id}`)
      setEstimates(prev => prev.filter(e => e.id !== id))
      toast.success('Estimate deleted')
    } catch {
      toast.error('Failed to delete', 'Please try again.')
    } finally {
      setDeleting(null)
    }
  }

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

  const totalValue = visible.reduce((s, e) => s + (e.grand_total || 0), 0)
  const avgValue   = visible.length > 0 ? totalValue / visible.length : 0

  const currentSortLabel = SORT_OPTIONS.find(o => o.value === sortBy)?.label ?? 'Sort'

  return (
    <div className="min-h-full">
      <div className="mx-auto w-full max-w-5xl px-4 py-5 sm:px-6 lg:px-8">
        <PageIntro
          eyebrow="Jobs Workspace"
          title="Review and resume saved estimates."
          description="Filter, search, and keep the pricing queue moving without leaving the shell."
          actions={(
            <>
              <button
                onClick={fetchEstimates}
                className="btn-secondary min-h-0 px-3 py-2"
                aria-label="Refresh estimates"
              >
                <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
              </button>
              <button
                onClick={() => router.push('/estimator?entry=quick-quote')}
                className="btn-primary min-h-0 px-3 py-2"
              >
                <Plus size={15} />
                Quick Quote
              </button>
            </>
          )}
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-hide">
                {FILTERS.map(f => (
                  <button
                    key={f.value}
                    onClick={() => setFilter(f.value)}
                    className={cn(
                      'px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all border',
                      filter === f.value
                        ? 'border-[color:var(--accent)] bg-[color:var(--accent)] text-white'
                        : 'border-[color:var(--line)] bg-[color:var(--panel)] text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]',
                    )}
                  >
                    {f.label}
                  </button>
                ))}
              </div>

              {!loading && (
                <div className="hidden rounded-full border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 py-1 text-xs font-medium text-[color:var(--muted-ink)] sm:block">
                  {visible.length} showing
                </div>
              )}
            </div>

            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[color:var(--muted-ink)] pointer-events-none" />
                <input
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder="Search by title or county…"
                  className="input min-h-0 py-2 pl-9 pr-8"
                />
                {search && (
                  <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors">
                    <X size={13} />
                  </button>
                )}
              </div>

              <div className="relative">
                <button
                  onClick={() => setSortOpen(o => !o)}
                  className="btn-secondary min-h-0 px-3 py-2 text-xs whitespace-nowrap"
                >
                  <ArrowUpDown size={13} />
                  <span className="hidden sm:inline">{currentSortLabel}</span>
                  <ChevronDown size={11} className={cn('transition-transform', sortOpen && 'rotate-180')} />
                </button>
                <AnimatePresence>
                  {sortOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: -6, scale: 0.96 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: -6, scale: 0.96 }}
                      transition={{ duration: 0.12 }}
                      className="absolute top-full right-0 z-20 mt-1.5 min-w-[152px] overflow-hidden rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] shadow-[0_16px_32px_rgba(84,60,39,0.16)]"
                    >
                      {SORT_OPTIONS.map(o => (
                        <button
                          key={o.value}
                          onClick={() => { setSortBy(o.value); setSortOpen(false) }}
                          className={cn(
                            'w-full px-3.5 py-2 text-left text-xs font-medium transition-colors',
                            o.value === sortBy
                              ? 'bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]'
                              : 'text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]',
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
        </PageIntro>

        <div className="mt-4">

        {/* Summary stats */}
        {!loading && visible.length > 0 && (
          <div className="grid grid-cols-3 gap-3 mb-4">
            {[
              { label: 'Showing', value: visible.length.toString(), icon: FileText, color: 'text-blue-700', bg: 'bg-blue-500/10 border-blue-500/20' },
              { label: 'Total Value', value: formatCurrency(totalValue), icon: TrendingUp, color: 'text-emerald-700', bg: 'bg-emerald-500/10 border-emerald-500/20' },
              { label: 'Avg Value', value: formatCurrency(avgValue), icon: MapPin, color: 'text-violet-700', bg: 'bg-violet-500/10 border-violet-500/20' },
            ].map(({ label, value, icon: Icon, color, bg }) => (
              <div key={label} className="card p-3.5 flex items-center gap-3">
                <div className={cn('w-9 h-9 rounded-xl flex items-center justify-center border shrink-0', bg)}>
                  <Icon size={14} className={color} />
                </div>
                <div className="min-w-0">
                  <div className="text-[10px] text-[color:var(--muted-ink)] font-bold uppercase tracking-wider">{label}</div>
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
          <div className="card p-8 text-center">
            <p className="text-red-700 font-medium text-sm mb-3">{error}</p>
            <button onClick={fetchEstimates} className="btn-primary mx-auto">Retry</button>
          </div>
        )}

        {/* Empty */}
        {!loading && !error && estimates.length === 0 && (
          <div className="card p-12 text-center">
            <div className="w-12 h-12 bg-[color:var(--panel-strong)] border border-[color:var(--line)] rounded-2xl flex items-center justify-center mx-auto mb-4">
              <FileText size={20} className="text-[color:var(--muted-ink)]" />
            </div>
            <h3 className="font-bold text-[color:var(--ink)] mb-1.5">No estimates yet</h3>
            <p className="text-[color:var(--muted-ink)] text-sm mb-6">Run a quick quote to generate your first saved job.</p>
            <button onClick={() => router.push('/estimator?entry=quick-quote')} className="btn-primary mx-auto">Start Quote</button>
          </div>
        )}

        {/* No search results */}
        {!loading && !error && estimates.length > 0 && visible.length === 0 && (
          <div className="card p-10 text-center">
            <Search size={24} className="text-[color:var(--muted-ink)] mx-auto mb-3" />
            <p className="text-[color:var(--muted-ink)] text-sm">No estimates match &ldquo;{search}&rdquo;</p>
            <button onClick={() => setSearch('')} className="btn-ghost mt-3 mx-auto text-xs">Clear search</button>
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
                    className="card p-4"
                  >
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-[color:var(--ink)] text-sm truncate mb-1.5">{est.title || `Estimate #${est.id}`}</h3>
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className={cn('badge', JOB_TYPE_CLASS[est.job_type] ?? 'badge-service')}>{est.job_type}</span>
                          <span className={cn('badge', STATUS_CLASS[est.status] ?? 'border-[color:var(--line)] bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)]')}>{est.status}</span>
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
                      <button
                        onClick={() => handleDelete(est.id)}
                        disabled={deleting === est.id}
                        className="p-2 rounded-xl hover:bg-red-500/10 text-[color:var(--muted-ink)] hover:text-red-700 transition-colors disabled:opacity-40"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>

            {/* Desktop table */}
            <div className="hidden lg:block card overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[color:var(--line)] bg-[color:var(--panel-strong)]">
                    {['Title', 'Type', 'Status', 'Confidence', 'County', 'Total', 'Date', ''].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-[10px] font-bold text-[color:var(--muted-ink)] uppercase tracking-widest">{h}</th>
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
                        className="hover:bg-[color:var(--panel-strong)] transition-colors group"
                      >
                        <td className="px-4 py-3 font-medium text-[color:var(--ink)] max-w-[180px] truncate">{est.title || `Estimate #${est.id}`}</td>
                        <td className="px-4 py-3"><span className={cn('badge', JOB_TYPE_CLASS[est.job_type] ?? 'badge-service')}>{est.job_type}</span></td>
                        <td className="px-4 py-3"><span className={cn('badge', STATUS_CLASS[est.status] ?? 'border-[color:var(--line)] bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)]')}>{est.status}</span></td>
                        <td className="px-4 py-3"><span className={cn('badge', 'badge-' + (est.confidence_label?.toLowerCase() ?? 'high'))}>{est.confidence_label ?? 'HIGH'}</span></td>
                        <td className="px-4 py-3 text-[color:var(--muted-ink)] text-xs">{est.county}</td>
                        <td className="px-4 py-3 font-bold text-[color:var(--ink)] tabular-nums">{formatCurrency(est.grand_total)}</td>
                        <td className="px-4 py-3 text-[color:var(--muted-ink)] text-xs whitespace-nowrap">{formatDate(est.created_at)}</td>
                        <td className="px-4 py-3">
                          <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={() => handleDelete(est.id)}
                              disabled={deleting === est.id}
                              className="p-1.5 rounded-lg hover:bg-red-500/10 text-[color:var(--muted-ink)] hover:text-red-700 transition-colors disabled:opacity-40"
                            >
                              <Trash2 size={13} />
                            </button>
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
    </div>
  )
}
