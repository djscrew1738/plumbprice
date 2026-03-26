'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Plus, Trash2, ExternalLink, FileText, Calendar, MapPin, Filter, RefreshCw } from 'lucide-react'
import { format } from 'date-fns'
import { cn, formatCurrency } from '@/lib/utils'
import axios from 'axios'

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

const API = process.env.NEXT_PUBLIC_API_URL + '/api/v1'

export function EstimatesListPage() {
  const router = useRouter()
  const [estimates, setEstimates] = useState<Estimate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<string>('all')
  const [deleting, setDeleting] = useState<number | null>(null)

  const fetchEstimates = async () => {
    try {
      setLoading(true)
      setError(null)
      const params = filter !== 'all' ? { job_type: filter } : {}
      const res = await axios.get(`${API}/estimates`, { params })
      setEstimates(res.data.estimates ?? res.data ?? [])
    } catch {
      setError('Could not load estimates')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchEstimates() }, [filter])

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this estimate?')) return
    setDeleting(id)
    try {
      await axios.delete(`${API}/estimates/${id}`)
      setEstimates(prev => prev.filter(e => e.id !== id))
    } catch {
      alert('Failed to delete')
    } finally {
      setDeleting(null)
    }
  }

  const jobTypeClass: Record<string, string> = {
    service: 'badge-service',
    construction: 'badge-construction',
    commercial: 'badge-commercial',
  }

  const statusColors: Record<string, string> = {
    draft: 'bg-white/5 text-zinc-400 border border-white/10',
    sent: 'bg-blue-500/10 text-blue-400 border border-blue-500/20',
    accepted: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
    rejected: 'bg-red-500/10 text-red-400 border border-red-500/20',
  }

  const filters = [
    { value: 'all', label: 'All' },
    { value: 'service', label: 'Service' },
    { value: 'construction', label: 'Construction' },
    { value: 'commercial', label: 'Commercial' },
  ]

  return (
    <div className="min-h-full bg-[#0a0a0a]">
      {/* Top bar */}
      <div className="bg-black/40 backdrop-blur-xl border-b border-white/5 px-4 py-3 sticky top-0 z-10">
        <div className="flex items-center justify-between gap-3 max-w-5xl mx-auto">
          <div className="flex items-center gap-2 overflow-x-auto scrollbar-hide">
            <Filter size={14} className="text-zinc-500 shrink-0" />
            {filters.map(f => (
              <button
                key={f.value}
                onClick={() => setFilter(f.value)}
                className={cn(
                  'px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all',
                  filter === f.value
                    ? 'bg-blue-600 text-white'
                    : 'bg-white/5 text-zinc-400 hover:bg-white/10 border border-white/[0.06]'
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button onClick={fetchEstimates} className="p-2 rounded-xl hover:bg-white/10 text-zinc-400 transition-colors">
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            </button>
            <button
              onClick={() => router.push('/estimator')}
              className="btn-primary text-sm px-3 py-2 gap-1.5"
            >
              <Plus size={16} />
              <span className="hidden sm:inline">New</span>
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-4">
        {/* Loading */}
        {loading && (
          <div className="space-y-3">
            {[1,2,3,4].map(i => (
              <div key={i} className="card p-4 space-y-2">
                <div className="skeleton h-4 w-2/3 rounded-lg" />
                <div className="skeleton h-8 w-1/3 rounded-lg" />
                <div className="skeleton h-3 w-1/2 rounded-lg" />
              </div>
            ))}
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div className="card p-8 text-center">
            <p className="text-red-400 font-medium mb-3">{error}</p>
            <button onClick={fetchEstimates} className="btn-primary text-sm">Retry</button>
          </div>
        )}

        {/* Empty */}
        {!loading && !error && estimates.length === 0 && (
          <div className="card p-10 text-center">
            <div className="w-14 h-14 bg-white/5 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-white/[0.06]">
              <FileText size={24} className="text-zinc-600" />
            </div>
            <h3 className="font-bold text-white mb-1">No estimates yet</h3>
            <p className="text-zinc-400 text-sm mb-5">Chat with the estimator to generate your first price.</p>
            <button onClick={() => router.push('/estimator')} className="btn-primary text-sm mx-auto">
              Start Estimating
            </button>
          </div>
        )}

        {/* Data */}
        {!loading && !error && estimates.length > 0 && (
          <>
            {/* Mobile card list */}
            <div className="space-y-3 lg:hidden">
              {estimates.map((est, i) => (
                <motion.div
                  key={est.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2, delay: i * 0.03 }}
                  className="card p-4 hover:border-white/10 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-white text-sm truncate">{est.title || `Estimate #${est.id}`}</h3>
                      <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                        <span className={cn('badge text-[11px]', jobTypeClass[est.job_type] ?? 'badge-service')}>
                          {est.job_type}
                        </span>
                        <span className={cn('badge text-[11px]', statusColors[est.status] ?? 'bg-white/5 text-zinc-400 border border-white/10')}>
                          {est.status}
                        </span>
                        <span className={cn('badge text-[11px]', 'badge-' + (est.confidence_label?.toLowerCase() ?? 'high'))}>
                          {est.confidence_label}
                        </span>
                      </div>
                    </div>
                    <div className="text-2xl font-extrabold text-white shrink-0">
                      {formatCurrency(est.grand_total)}
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 text-xs text-zinc-500">
                      <span className="flex items-center gap-1">
                        <MapPin size={11} />{est.county}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar size={11} />
                        {format(new Date(est.created_at), 'MMM d, yyyy')}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button className="p-2 rounded-xl hover:bg-white/10 text-zinc-500 hover:text-blue-400 transition-colors">
                        <ExternalLink size={16} />
                      </button>
                      <button
                        onClick={() => handleDelete(est.id)}
                        disabled={deleting === est.id}
                        className="p-2 rounded-xl hover:bg-red-500/10 text-zinc-500 hover:text-red-400 transition-colors"
                      >
                        <Trash2 size={16} />
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
                  <tr className="border-b border-white/5 bg-white/[0.02]">
                    {['Title', 'Type', 'Status', 'Confidence', 'County', 'Total', 'Date', ''].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {estimates.map((est, i) => (
                    <motion.tr
                      key={est.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.15, delay: i * 0.02 }}
                      className="hover:bg-white/[0.03] transition-colors"
                    >
                      <td className="px-4 py-3 font-medium text-white max-w-[180px] truncate">
                        {est.title || `Estimate #${est.id}`}
                      </td>
                      <td className="px-4 py-3">
                        <span className={cn('badge', jobTypeClass[est.job_type] ?? 'badge-service')}>
                          {est.job_type}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={cn('badge', statusColors[est.status])}>
                          {est.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={cn('badge', 'badge-' + est.confidence_label?.toLowerCase())}>
                          {est.confidence_label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-zinc-400">{est.county}</td>
                      <td className="px-4 py-3 font-bold text-white text-right">
                        {formatCurrency(est.grand_total)}
                      </td>
                      <td className="px-4 py-3 text-zinc-500 whitespace-nowrap">
                        {format(new Date(est.created_at), 'MMM d, yyyy')}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          <button className="p-1.5 rounded-lg hover:bg-white/10 text-zinc-500 hover:text-blue-400 transition-colors">
                            <ExternalLink size={14} />
                          </button>
                          <button
                            onClick={() => handleDelete(est.id)}
                            className="p-1.5 rounded-lg hover:bg-red-500/10 text-zinc-500 hover:text-red-400 transition-colors"
                          >
                            <Trash2 size={14} />
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
