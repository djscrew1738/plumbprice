'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import {
  ArrowLeft, Calendar, MapPin, Layers, CircleDollarSign,
  FileText, TrendingUp, Tag, AlertCircle,
} from 'lucide-react'
import { format, isValid } from 'date-fns'
import { api } from '@/lib/api'
import { cn, formatCurrency, formatCurrencyDecimal } from '@/lib/utils'

interface LineItem {
  line_type: string
  description: string
  quantity: number
  unit: string
  unit_cost: number
  total_cost: number
  supplier?: string | null
  sku?: string | null
  canonical_item?: string | null
}

interface EstimateDetail {
  id: number
  title: string
  job_type: string
  status: string
  labor_total: number
  materials_total: number
  tax_total: number
  markup_total: number
  misc_total: number
  subtotal: number
  grand_total: number
  confidence_score: number
  confidence_label: string
  assumptions: string[]
  county: string
  tax_rate: number
  preferred_supplier?: string | null
  line_items: LineItem[]
  created_at: string
}

const JOB_TYPE_CLASS: Record<string, string> = {
  service: 'badge-service',
  construction: 'badge-construction',
  commercial: 'badge-commercial',
}

const LINE_TYPE_LABEL: Record<string, string> = {
  labor: 'Labor',
  material: 'Material',
  markup: 'Markup',
  tax: 'Tax',
  misc: 'Misc',
}

const LINE_TYPE_COLOR: Record<string, string> = {
  labor:    'text-blue-400',
  material: 'text-emerald-400',
  markup:   'text-amber-400',
  tax:      'text-zinc-500',
  misc:     'text-violet-400',
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr)
  return isValid(d) ? format(d, 'MMMM d, yyyy · h:mm a') : '—'
}

export function EstimateDetailPage() {
  const params = useParams()
  const router = useRouter()
  const id = Number(params?.id)

  const [estimate, setEstimate] = useState<EstimateDetail | null>(null)
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    const load = async () => {
      try {
        setLoading(true)
        setError(null)
        const res = await api.get(`/estimates/${id}`)
        setEstimate(res.data)
      } catch {
        setError('Could not load estimate')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [id])

  // ── Loading ──────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-full bg-[#080808] px-4 py-6 max-w-4xl mx-auto space-y-4">
        <div className="skeleton h-8 w-48 rounded-xl" />
        <div className="card p-6 space-y-4">
          <div className="skeleton h-6 w-2/3 rounded-lg" />
          <div className="skeleton h-4 w-1/3 rounded-lg" />
          <div className="grid grid-cols-3 gap-3 mt-4">
            {[1,2,3].map(i => <div key={i} className="skeleton h-20 rounded-xl" />)}
          </div>
        </div>
        <div className="card p-6 space-y-3">
          {[1,2,3,4,5].map(i => <div key={i} className="skeleton h-10 rounded-lg" />)}
        </div>
      </div>
    )
  }

  // ── Error ────────────────────────────────────────────────────────────────────
  if (error || !estimate) {
    return (
      <div className="min-h-full bg-[#080808] flex flex-col items-center justify-center gap-4 p-8">
        <AlertCircle size={32} className="text-red-400" />
        <p className="text-zinc-400 text-sm">{error ?? 'Estimate not found'}</p>
        <button onClick={() => router.back()} className="btn-secondary">
          <ArrowLeft size={14} /> Go back
        </button>
      </div>
    )
  }

  const laborLines    = estimate.line_items.filter(l => l.line_type === 'labor')
  const materialLines = estimate.line_items.filter(l => l.line_type === 'material')
  const otherLines    = estimate.line_items.filter(l => !['labor','material'].includes(l.line_type))

  return (
    <div className="min-h-full bg-[#080808]">

      {/* ── Sticky header ────────────────────────────────────────────────────── */}
      <div className="bg-[#080808]/80 backdrop-blur-xl border-b border-white/[0.06] px-4 py-3 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <button
            onClick={() => router.back()}
            className="p-2 rounded-xl hover:bg-white/[0.07] text-zinc-500 hover:text-zinc-200 transition-colors"
          >
            <ArrowLeft size={16} />
          </button>
          <div className="flex-1 min-w-0">
            <h1 className="text-sm font-bold text-white truncate">{estimate.title || `Estimate #${estimate.id}`}</h1>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={cn('badge', JOB_TYPE_CLASS[estimate.job_type] ?? 'badge-service')}>
                {estimate.job_type}
              </span>
              <span className="text-[11px] text-zinc-600">{estimate.county} County</span>
            </div>
          </div>
          <div className="text-right shrink-0">
            <div className="text-lg font-extrabold text-white tabular-nums">
              {formatCurrency(estimate.grand_total)}
            </div>
            <div className="text-[10px] text-zinc-600">grand total</div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-5 space-y-4">

        {/* ── Summary cards ────────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="grid grid-cols-2 sm:grid-cols-4 gap-3"
        >
          {[
            { label: 'Labor',     value: estimate.labor_total,     icon: TrendingUp,       color: 'text-blue-400',    bg: 'bg-blue-500/10 border-blue-500/20'     },
            { label: 'Materials', value: estimate.materials_total,  icon: Layers,           color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20'},
            { label: 'Markup',    value: estimate.markup_total,     icon: Tag,              color: 'text-amber-400',   bg: 'bg-amber-500/10 border-amber-500/20'   },
            { label: 'Tax',       value: estimate.tax_total,        icon: CircleDollarSign, color: 'text-zinc-400',    bg: 'bg-white/[0.03] border-white/[0.08]'   },
          ].map(({ label, value, icon: Icon, color, bg }) => (
            <div key={label} className="card p-3.5 flex items-center gap-3">
              <div className={cn('w-8 h-8 rounded-xl flex items-center justify-center border shrink-0', bg)}>
                <Icon size={13} className={color} />
              </div>
              <div className="min-w-0">
                <div className="text-[10px] text-zinc-600 font-bold uppercase tracking-wider">{label}</div>
                <div className="text-sm font-bold text-white tabular-nums">{formatCurrency(value)}</div>
              </div>
            </div>
          ))}
        </motion.div>

        {/* ── Metadata row ─────────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, delay: 0.05 }}
          className="card p-4 flex flex-wrap gap-4 text-sm"
        >
          <div className="flex items-center gap-2 text-zinc-500">
            <Calendar size={13} className="text-zinc-600 shrink-0" />
            <span className="text-xs">{formatDate(estimate.created_at)}</span>
          </div>
          <div className="flex items-center gap-2 text-zinc-500">
            <MapPin size={13} className="text-zinc-600 shrink-0" />
            <span className="text-xs">{estimate.county} County · {(estimate.tax_rate * 100).toFixed(2)}% tax</span>
          </div>
          {estimate.preferred_supplier && (
            <div className="flex items-center gap-2 text-zinc-500">
              <FileText size={13} className="text-zinc-600 shrink-0" />
              <span className="text-xs">Supplier: {estimate.preferred_supplier}</span>
            </div>
          )}
          <div className="ml-auto flex items-center gap-2">
            <span className={cn('badge', `badge-${estimate.confidence_label?.toLowerCase() ?? 'high'}`)}>
              {estimate.confidence_label} confidence
            </span>
            <span className="text-xs text-zinc-600 tabular-nums">
              {Math.round(estimate.confidence_score * 100)}%
            </span>
          </div>
        </motion.div>

        {/* ── Line items ───────────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, delay: 0.1 }}
          className="card overflow-hidden"
        >
          <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
            <h2 className="text-xs font-bold text-white uppercase tracking-wider">Line Items</h2>
            <span className="text-[11px] text-zinc-600">{estimate.line_items.length} items</span>
          </div>

          {/* Labor */}
          {laborLines.length > 0 && (
            <LineItemSection title="Labor" items={laborLines} />
          )}

          {/* Materials */}
          {materialLines.length > 0 && (
            <LineItemSection title="Materials" items={materialLines} />
          )}

          {/* Other (markup, tax, misc) */}
          {otherLines.length > 0 && (
            <LineItemSection title="Fees & Taxes" items={otherLines} />
          )}

          {/* Totals footer */}
          <div className="bg-white/[0.02] border-t border-white/[0.06] divide-y divide-white/[0.04]">
            {[
              { label: 'Subtotal',  value: estimate.subtotal },
              { label: `Tax (${(estimate.tax_rate * 100).toFixed(2)}%)`, value: estimate.tax_total },
            ].map(({ label, value }) => (
              <div key={label} className="flex items-center justify-between px-5 py-2.5 text-sm">
                <span className="text-zinc-500">{label}</span>
                <span className="text-zinc-300 font-semibold tabular-nums">{formatCurrencyDecimal(value)}</span>
              </div>
            ))}
            <div className="flex items-center justify-between px-5 py-3">
              <span className="text-sm font-bold text-white">Grand Total</span>
              <span className="text-xl font-extrabold text-white tabular-nums">{formatCurrencyDecimal(estimate.grand_total)}</span>
            </div>
          </div>
        </motion.div>

        {/* ── Assumptions ──────────────────────────────────────────────────── */}
        {estimate.assumptions.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, delay: 0.15 }}
            className="card p-4"
          >
            <h2 className="text-xs font-bold text-white uppercase tracking-wider mb-3">Assumptions</h2>
            <ul className="space-y-2">
              {estimate.assumptions.map((a, i) => (
                <li key={i} className="flex items-start gap-2.5 text-xs text-zinc-500">
                  <span className="w-1.5 h-1.5 rounded-full bg-zinc-700 mt-1.5 shrink-0" />
                  {a}
                </li>
              ))}
            </ul>
          </motion.div>
        )}
      </div>
    </div>
  )
}

function LineItemSection({ title, items }: { title: string; items: LineItem[] }) {
  return (
    <div>
      <div className="px-4 py-2 bg-white/[0.015] border-y border-white/[0.04]">
        <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest">{title}</span>
      </div>
      <div className="divide-y divide-white/[0.04]">
        {items.map((item, i) => (
          <div key={i} className="px-4 py-3 flex items-start gap-3 hover:bg-white/[0.015] transition-colors">
            <div className="flex-1 min-w-0">
              <div className="text-sm text-zinc-200 font-medium">{item.description}</div>
              <div className="flex items-center gap-3 mt-1">
                {item.supplier && (
                  <span className="text-[10px] text-zinc-600">{item.supplier}</span>
                )}
                {item.sku && (
                  <span className="text-[10px] text-zinc-700 font-mono">SKU: {item.sku}</span>
                )}
                <span className={cn('text-[10px] font-semibold', LINE_TYPE_COLOR[item.line_type] ?? 'text-zinc-500')}>
                  {LINE_TYPE_LABEL[item.line_type] ?? item.line_type}
                </span>
              </div>
            </div>
            <div className="text-right shrink-0">
              <div className="text-sm font-semibold text-white tabular-nums">
                {formatCurrencyDecimal(item.total_cost)}
              </div>
              {item.quantity !== 1 && (
                <div className="text-[10px] text-zinc-600 tabular-nums">
                  {item.quantity} × {formatCurrencyDecimal(item.unit_cost)} / {item.unit}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
