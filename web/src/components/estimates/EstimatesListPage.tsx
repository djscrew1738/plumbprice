'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus, Trash2, FileText, Calendar, MapPin, RefreshCw,
  TrendingUp, Search, X, ChevronDown, ArrowUpDown, Check,
} from 'lucide-react'
import { format, isValid } from 'date-fns'
import { cn, formatCurrency } from '@/lib/utils'
import { api } from '@/lib/api'
import { useToast } from '@/components/ui/Toast'

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
  draft:    'bg-white/[0.04] text-zinc-500 border border-white/[0.08]',
  sent:     'bg-blue-500/10 text-blue-400 border border-blue-500/20',
  accepted: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
  rejected: 'bg-red-500/10 text-red-400 border border-red-500/20',
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
          'badge cursor-pointer hover:opacity-80 transition-opacity gap-1',
          STATUS_CLASS[current] ?? 'bg-white/[0.04] text-zinc-500 border border-white/[0.08]',
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
              className="absolute top-full left-0 mt-1 bg-[#111] border border-white/[0.1] rounded-xl shadow-2xl z-20 overflow-hidden min-w-[110px]"
            >
              {STATUS_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => handleSelect(opt.value)}
                  className={cn(
                    'w-full flex items-center justify-between px-3 py-2 text-xs font-medium transition-colors text-left',
                    opt.value === current
                      ? 'text-blue-400 bg-blue-500/10'
                      : 'text-zinc-400 hover:text-white hover:bg-white/[0.06]',
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
      setEstimates(res.data ?? [])
    } catch {
      setError('Could not load estimates')
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => { fetchEstimates() }, [fetchEstimates])

  const handleStatusChange = (id: number, status: string) => {
    setEstimates(prev => prev.map(e => e.id === id ? { ...e, status } : e))
  }

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
    <div className="min-h-full bg-[#080808]">

      {/* ── Top bar ── */}
      <div className="bg-[#080808]/80 backdrop-blur-xl border-b border-white/[0.06] px-4 py-2.5 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto space-y-2.5">
          <div className="flex items-center justify-between gap-3">
            {/* Filter pills */}
            <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-hide">
              {FILTERS.map(f => (
                <button
                  key={f.value}
                  onClick={() => setFilter(f.value)}
                  className={cn(
                    'px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all',
                    filter === f.value
                      ? 'bg-blue-600 text-white'
                      : 'bg-white/[0.04] text-zinc-500 hover:text-zinc-200 hover:bg-white/[0.08] border border-white/[0.06]',
                  )}
                >
                  {f.label}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button onClick={fetchEstimates} className="p-2 rounded-xl hover:bg-white/[0.07] text-zinc-500 hover:text-zinc-300 transition-colors">
                <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
              </button>
              <button onClick={() => router.push('/estimator')} className="btn-primary px-3 py-2">
                <Plus size={15} /><span className="hidden sm:inline">New</span>
              </button>
            </div>
          </div>

          {/* Search + sort row */}
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-600 pointer-events-none" />
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search by title or county…"
                className="w-full pl-9 pr-8 py-2 bg-white/[0.04] border border-white/[0.08] rounded-xl text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-500/40 transition-all"
              />
              {search && (
                <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-600 hover:text-zinc-300 transition-colors">
                  <X size={13} />
                </button>
              )}
            </div>
            {/* Sort dropdown */}
            <div className="relative">
              <button
                onClick={() => setSortOpen(o => !o)}
                className="flex items-center gap-1.5 px-3 py-2 bg-white/[0.04] border border-white/[0.08] rounded-xl text-xs font-medium text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.07] transition-all whitespace-nowrap"
              >
                <ArrowUpDown size={13} />
                <span className="hidden sm:inline">{currentSortLabel}</span>
                <ChevronDown size={11} className={cn('text-zinc-600 transition-transform', sortOpen && 'rotate-180')} />
              </button>
              <AnimatePresence>
                {sortOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -6, scale: 0.96 }}
                    animate={{ opacity: 1, y: 0,  scale: 1    }}
                    exit={{   opacity: 0, y: -6,  scale: 0.96 }}
                    transition={{ duration: 0.12 }}
                    className="absolute top-full right-0 mt-1.5 bg-[#111] border border-white/[0.08] rounded-xl shadow-2xl overflow-hidden z-20 min-w-[152px]"
                  >
                    {SORT_OPTIONS.map(o => (
                      <button
                        key={o.value}
                        onClick={() => { setSortBy(o.value); setSortOpen(false) }}
                        className={cn(
                          'w-full text-left px-3.5 py-2 text-xs font-medium transition-colors',
                          o.value === sortBy ? 'text-blue-400 bg-blue-500/10' : 'text-zinc-400 hover:text-white hover:bg-white/[0.06]',
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
              { label: 'Showing',     value: visible.length.toString(), icon: FileText,   color: 'text-blue-400',    bg: 'bg-blue-500/10 border-blue-500/20' },
              { label: 'Total Value', value: formatCurrency(totalValue), icon: TrendingUp, color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20' },
              { label: 'Avg Value',   value: formatCurrency(avgValue),   icon: MapPin,     color: 'text-violet-400',  bg: 'bg-violet-500/10 border-violet-500/20' },
            ].map(({ label, value, icon: Icon, color, bg }) => (
              <div key={label} className="card p-3.5 flex items-center gap-3">
                <div className={cn('w-9 h-9 rounded-xl flex items-center justify-center border shrink-0', bg)}>
                  <Icon size={14} className={color} />
                </div>
                <div className="min-w-0">
                  <div className="text-[10px] text-zinc-600 font-bold uppercase tracking-wider">{label}</div>
                  <div className="text-sm font-bold text-white truncate">{value}</div>
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
            <p className="text-red-400 font-medium text-sm mb-3">{error}</p>
            <button onClick={fetchEstimates} className="btn-primary mx-auto">Retry</button>
          </div>
        )}

        {/* Empty */}
        {!loading && !error && estimates.length === 0 && (
          <div className="card p-12 text-center">
            <div className="w-12 h-12 bg-white/[0.03] border border-white/[0.07] rounded-2xl flex items-center justify-center mx-auto mb-4">
              <FileText size={20} className="text-zinc-700" />
            </div>
            <h3 className="font-bold text-white mb-1.5">No estimates yet</h3>
            <p className="text-zinc-600 text-sm mb-6">Chat with the estimator to generate your first price.</p>
            <button onClick={() => router.push('/estimator')} className="btn-primary mx-auto">Start Estimating</button>
          </div>
        )}

        {/* No search results */}
        {!loading && !error && estimates.length > 0 && visible.length === 0 && (
          <div className="card p-10 text-center">
            <Search size={24} className="text-zinc-700 mx-auto mb-3" />
            <p className="text-zinc-500 text-sm">No estimates match &ldquo;{search}&rdquo;</p>
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
                    className="card p-4 cursor-pointer hover:border-white/10 transition-colors"
                    onClick={() => router.push(`/estimates/${est.id}`)}
                  >
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-white text-sm truncate mb-1.5">{est.title || `Estimate #${est.id}`}</h3>
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className={cn('badge', JOB_TYPE_CLASS[est.job_type] ?? 'badge-service')}>{est.job_type}</span>
                          <StatusDropdown estimateId={est.id} current={est.status} onChange={handleStatusChange} />
                          <span className={cn('badge', 'badge-' + (est.confidence_label?.toLowerCase() ?? 'high'))}>{est.confidence_label ?? 'HIGH'}</span>
                        </div>
                      </div>
                      <div className="text-xl font-extrabold text-white shrink-0 tabular-nums">{formatCurrency(est.grand_total)}</div>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 text-[11px] text-zinc-600">
                        <span className="flex items-center gap-1"><MapPin size={10} />{est.county}</span>
                        <span className="flex items-center gap-1"><Calendar size={10} />{formatDate(est.created_at)}</span>
                      </div>
                      <button
                        onClick={e => { e.stopPropagation(); handleDelete(est.id) }}
                        disabled={deleting === est.id}
                        className="p-2 rounded-xl hover:bg-red-500/10 text-zinc-600 hover:text-red-400 transition-colors disabled:opacity-40"
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
                  <tr className="border-b border-white/[0.06] bg-white/[0.015]">
                    {['Title', 'Type', 'Status', 'Confidence', 'County', 'Total', 'Date', ''].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-[10px] font-bold text-zinc-600 uppercase tracking-widest">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.05]">
                  <AnimatePresence initial={false}>
                    {visible.map((est, i) => (
                      <motion.tr
                        key={est.id}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.12, delay: i * 0.015 }}
                        className="hover:bg-white/[0.025] transition-colors group cursor-pointer"
                        onClick={() => router.push(`/estimates/${est.id}`)}
                      >
                        <td className="px-4 py-3 font-medium text-zinc-200 max-w-[180px] truncate">{est.title || `Estimate #${est.id}`}</td>
                        <td className="px-4 py-3"><span className={cn('badge', JOB_TYPE_CLASS[est.job_type] ?? 'badge-service')}>{est.job_type}</span></td>
                        <td className="px-4 py-3"><StatusDropdown estimateId={est.id} current={est.status} onChange={handleStatusChange} /></td>
                        <td className="px-4 py-3"><span className={cn('badge', 'badge-' + (est.confidence_label?.toLowerCase() ?? 'high'))}>{est.confidence_label ?? 'HIGH'}</span></td>
                        <td className="px-4 py-3 text-zinc-500 text-xs">{est.county}</td>
                        <td className="px-4 py-3 font-bold text-white tabular-nums">{formatCurrency(est.grand_total)}</td>
                        <td className="px-4 py-3 text-zinc-600 text-xs whitespace-nowrap">{formatDate(est.created_at)}</td>
                        <td className="px-4 py-3">
                          <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={e => { e.stopPropagation(); handleDelete(est.id) }}
                              disabled={deleting === est.id}
                              className="p-1.5 rounded-lg hover:bg-red-500/10 text-zinc-600 hover:text-red-400 transition-colors disabled:opacity-40"
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
  )
}
