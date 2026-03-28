'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Plus, Trash2, FileText, Calendar, MapPin, RefreshCw, TrendingUp } from 'lucide-react'
import { format, isValid } from 'date-fns'
import { cn, formatCurrency } from '@/lib/utils'
import { api } from '@/lib/api'

interface Estimate {
  id: number
  title: string
  job_type: string
  status: string
  grand_total: number
  confidence_label: string
  county: string
  created_at: string
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return isValid(d) ? format(d, 'MMM d, yy') : '—'
}

const JOB_TYPE_CLASS: Record<string, string> = {
  service:      'badge-service',
  construction: 'badge-construction',
  commercial:   'badge-commercial',
}

const STATUS_CLASS: Record<string, string> = {
  draft:    'bg-white/[0.04] text-zinc-500 border border-white/[0.08]',
  sent:     'bg-blue-500/10 text-blue-400 border border-blue-500/20',
  accepted: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
  rejected: 'bg-red-500/10 text-red-400 border border-red-500/20',
}

const FILTERS = [
  { value: 'all',          label: 'All' },
  { value: 'service',      label: 'Service' },
  { value: 'construction', label: 'Construction' },
  { value: 'commercial',   label: 'Commercial' },
]

export function EstimatesListPage() {
  const router   = useRouter()
  const [estimates, setEstimates] = useState<Estimate[]>([])
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState<string | null>(null)
  const [filter,    setFilter]    = useState('all')
  const [deleting,  setDeleting]  = useState<number | null>(null)

  const fetchEstimates = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
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
    } catch {
      alert('Failed to delete')
    } finally {
      setDeleting(null)
    }
  }

  const totalValue = estimates.reduce((s, e) => s + (e.grand_total || 0), 0)
  const avgValue   = estimates.length > 0 ? totalValue / estimates.length : 0

  return (
    <div className="min-h-full bg-[#080808]">

      {/* ── Top bar ── */}
      <div className="bg-[#080808]/80 backdrop-blur-xl border-b border-white/[0.06] px-4 py-2.5 sticky top-0 z-10">
        <div className="flex items-center justify-between gap-3 max-w-5xl mx-auto">
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
            <button
              onClick={fetchEstimates}
              className="p-2 rounded-xl hover:bg-white/[0.07] text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
            </button>
            <button
              onClick={() => router.push('/estimator')}
              className="btn-primary px-3 py-2"
            >
              <Plus size={15} />
              <span className="hidden sm:inline">New</span>
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-4">

        {/* ── Summary stats ── */}
        {!loading && estimates.length > 0 && (
          <div className="grid grid-cols-3 gap-3 mb-4">
            {[
              { label: 'Estimates', value: estimates.length.toString(), icon: FileText, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20' },
              { label: 'Total Value', value: formatCurrency(totalValue), icon: TrendingUp, color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20' },
              { label: 'Avg Value',   value: formatCurrency(avgValue),   icon: MapPin,     color: 'text-violet-400', bg: 'bg-violet-500/10 border-violet-500/20' },
            ].map(({ label, value, icon: Icon, color, bg }) => (
              <div key={label} className="card p-3.5 flex items-center gap-3">
                <div className={cn('w-9 h-9 rounded-xl flex items-center justify-center border shrink-0', bg)}>
                  <Icon size={15} className={color} />
                </div>
                <div className="min-w-0">
                  <div className="text-[10px] text-zinc-600 font-medium uppercase tracking-wide">{label}</div>
                  <div className="text-sm font-bold text-white truncate">{value}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── Loading skeletons ── */}
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

        {/* ── Error ── */}
        {error && !loading && (
          <div className="card p-8 text-center">
            <p className="text-red-400 font-medium text-sm mb-3">{error}</p>
            <button onClick={fetchEstimates} className="btn-primary text-sm mx-auto">Retry</button>
          </div>
        )}

        {/* ── Empty ── */}
        {!loading && !error && estimates.length === 0 && (
          <div className="card p-12 text-center">
            <div className="w-12 h-12 bg-white/[0.03] border border-white/[0.07] rounded-2xl flex items-center justify-center mx-auto mb-4">
              <FileText size={20} className="text-zinc-700" />
            </div>
            <h3 className="font-bold text-white mb-1.5">No estimates yet</h3>
            <p className="text-zinc-600 text-sm mb-6">Chat with the estimator to generate your first price.</p>
            <button onClick={() => router.push('/estimator')} className="btn-primary mx-auto">
              Start Estimating
            </button>
          </div>
        )}

        {/* ── Data ── */}
        {!loading && !error && estimates.length > 0 && (
          <>
            {/* Mobile cards */}
            <div className="space-y-2.5 lg:hidden">
              {estimates.map((est, i) => (
                <motion.div
                  key={est.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.18, delay: i * 0.03 }}
                  className="card p-4"
                >
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-white text-sm truncate mb-1.5">
                        {est.title || `Estimate #${est.id}`}
                      </h3>
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className={cn('badge', JOB_TYPE_CLASS[est.job_type] ?? 'badge-service')}>
                          {est.job_type}
                        </span>
                        <span className={cn('badge', STATUS_CLASS[est.status] ?? 'bg-white/[0.04] text-zinc-500 border border-white/[0.08]')}>
                          {est.status}
                        </span>
                        <span className={cn('badge', 'badge-' + (est.confidence_label?.toLowerCase() ?? 'high'))}>
                          {est.confidence_label}
                        </span>
                      </div>
                    </div>
                    <div className="text-xl font-extrabold text-white shrink-0 tabular-nums">
                      {formatCurrency(est.grand_total)}
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 text-[11px] text-zinc-600">
                      <span className="flex items-center gap-1"><MapPin size={10} />{est.county}</span>
                      <span className="flex items-center gap-1"><Calendar size={10} />{formatDate(est.created_at)}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleDelete(est.id)}
                        disabled={deleting === est.id}
                        className="p-2 rounded-xl hover:bg-red-500/10 text-zinc-600 hover:text-red-400 transition-colors disabled:opacity-40"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Desktop table */}
            <div className="hidden lg:block card overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/[0.06] bg-white/[0.015]">
                    {['Title', 'Type', 'Status', 'Confidence', 'County', 'Total', 'Date', ''].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-[10px] font-bold text-zinc-600 uppercase tracking-widest">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.05]">
                  {estimates.map((est, i) => (
                    <motion.tr
                      key={est.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.15, delay: i * 0.02 }}
                      className="hover:bg-white/[0.025] transition-colors group"
                    >
                      <td className="px-4 py-3 font-medium text-zinc-200 max-w-[180px] truncate">
                        {est.title || `Estimate #${est.id}`}
                      </td>
                      <td className="px-4 py-3">
                        <span className={cn('badge', JOB_TYPE_CLASS[est.job_type] ?? 'badge-service')}>
                          {est.job_type}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={cn('badge', STATUS_CLASS[est.status] ?? 'bg-white/[0.04] text-zinc-500 border border-white/[0.08]')}>
                          {est.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={cn('badge', 'badge-' + (est.confidence_label?.toLowerCase() ?? 'high'))}>
                          {est.confidence_label ?? 'HIGH'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-zinc-500 text-xs">{est.county}</td>
                      <td className="px-4 py-3 font-bold text-white tabular-nums">
                        {formatCurrency(est.grand_total)}
                      </td>
                      <td className="px-4 py-3 text-zinc-600 text-xs whitespace-nowrap">
                        {formatDate(est.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={() => handleDelete(est.id)}
                            disabled={deleting === est.id}
                            className="p-1.5 rounded-lg hover:bg-red-500/10 text-zinc-600 hover:text-red-400 transition-colors disabled:opacity-40"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
