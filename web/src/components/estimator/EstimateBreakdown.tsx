'use client'

import { CheckCircle2, AlertCircle, XCircle, ExternalLink, CheckCheck } from 'lucide-react'
import { cn, formatCurrency, formatCurrencyDecimal } from '@/lib/utils'
import type { EstimateBreakdown as EstimateBreakdownType } from '@/types'
import Link from 'next/link'

interface Props {
  estimate: EstimateBreakdownType
  confidenceLabel: string
  confidenceScore: number
  assumptions: string[]
  county: string
  compact?: boolean
}

const CONFIDENCE: Record<string, { icon: typeof CheckCircle2; color: string; bg: string }> = {
  HIGH:   { icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20' },
  MEDIUM: { icon: AlertCircle,  color: 'text-amber-400',   bg: 'bg-amber-500/10 border-amber-500/20' },
  LOW:    { icon: XCircle,      color: 'text-red-400',      bg: 'bg-red-500/10 border-red-500/20' },
}

export function EstimateBreakdown({
  estimate, confidenceLabel, confidenceScore, assumptions, county, compact = false,
}: Props) {
  const rawLabel = confidenceLabel?.toUpperCase()
  const label = (rawLabel === 'HIGH' || rawLabel === 'MEDIUM' || rawLabel === 'LOW') ? rawLabel : 'HIGH'
  const conf  = CONFIDENCE[label]
  const ConfIcon = conf.icon

  const total = estimate.grand_total || 1
  const costRows = [
    { label: 'Labor',       value: estimate.labor_total,     color: 'bg-blue-500',    pct: estimate.labor_total / total },
    { label: 'Materials',   value: estimate.materials_total, color: 'bg-violet-500',  pct: estimate.materials_total / total },
    { label: 'Markup',      value: estimate.markup_total,    color: 'bg-amber-500',   pct: estimate.markup_total / total },
    { label: 'Misc',        value: estimate.misc_total,      color: 'bg-orange-500',  pct: estimate.misc_total / total },
    { label: `Tax (${county})`, value: estimate.tax_total,  color: 'bg-zinc-500',    pct: estimate.tax_total / total },
  ].filter(r => r.value > 0)

  const pad = compact ? 'px-4 py-3.5' : 'px-5 py-4'

  return (
    <div className="flex-1 flex flex-col overflow-hidden">

      {/* ── Hero ── */}
      <div className={cn('shrink-0 bg-[#0c0c0c] border-b border-white/[0.06]', pad)}>
        <div className="text-[11px] font-semibold uppercase tracking-widest text-zinc-600 mb-2">
          Recommended Price
        </div>
        <div className={cn('font-extrabold text-white leading-none mb-3', compact ? 'text-4xl' : 'text-5xl')}>
          {formatCurrency(estimate.grand_total)}
        </div>
        <div className={cn(
          'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold border',
          conf.bg, conf.color,
        )}>
          <ConfIcon size={11} />
          {label} · {Math.round((confidenceScore || 0) * 100)}% confidence
        </div>
      </div>

      {/* ── Scrollable body ── */}
      <div className="flex-1 overflow-y-auto">
        <div className={cn('space-y-3', compact ? 'p-4' : 'p-5')}>

          {/* Cost breakdown */}
          <div className="card-sm overflow-hidden">
            <div className="px-4 pt-4 pb-3">
              <h3 className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest mb-3">Cost Breakdown</h3>
              <div className="space-y-2.5">
                {costRows.map(row => (
                  <div key={row.label}>
                    <div className="flex justify-between items-center text-xs mb-1">
                      <span className="text-zinc-500">{row.label}</span>
                      <span className="font-semibold text-zinc-200">{formatCurrencyDecimal(row.value)}</span>
                    </div>
                    <div className="h-1 bg-white/[0.05] rounded-full overflow-hidden">
                      <div
                        className={cn('cost-bar', row.color)}
                        style={{ width: `${Math.max(row.pct * 100, 2)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-3.5 pt-3 border-t border-white/[0.06] flex justify-between items-center">
                <span className="text-xs font-bold text-white">Total</span>
                <span className="text-base font-extrabold text-white">{formatCurrency(estimate.grand_total)}</span>
              </div>
            </div>
          </div>

          {/* Line items */}
          {estimate.line_items.length > 0 && (
            <div className="card-sm overflow-hidden">
              <div className="px-4 pt-3.5 pb-1">
                <h3 className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest">
                  Line Items <span className="text-zinc-700 normal-case">({estimate.line_items.length})</span>
                </h3>
              </div>
              <div className="divide-y divide-white/[0.05]">
                {estimate.line_items.map((item, i) => (
                  <div key={`${item.description}-${i}`} className="px-4 py-2.5 flex justify-between items-start gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-medium text-zinc-200 leading-snug">{item.description}</div>
                      <div className="text-[10px] text-zinc-600 mt-0.5 flex items-center gap-1.5 flex-wrap">
                        <span>{item.quantity} {item.unit} × {formatCurrencyDecimal(item.unit_cost)}</span>
                        {item.supplier && (
                          <span className="px-1.5 py-px bg-white/[0.04] border border-white/[0.06] rounded font-mono text-zinc-500">
                            {item.supplier}
                          </span>
                        )}
                      </div>
                    </div>
                    <span className="text-xs font-bold text-zinc-300 shrink-0">
                      {formatCurrencyDecimal(item.total_cost)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Assumptions */}
          {assumptions.length > 0 && (
            <div className="card-sm p-4">
              <h3 className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest mb-3">Assumptions</h3>
              <ul className="space-y-2">
                {assumptions.map((a, i) => (
                  <li key={`assumption-${i}-${a.slice(0, 20)}`} className="text-xs text-zinc-500 flex gap-2 leading-relaxed">
                    <CheckCircle2 size={12} className="text-zinc-700 shrink-0 mt-0.5" />
                    {a}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Actions */}
          <div className="space-y-2 pt-1">
            <div className="btn-secondary w-full opacity-60 cursor-default pointer-events-none gap-2 text-xs">
              <CheckCheck size={14} className="text-emerald-400" />
              <span className="text-zinc-300">Saved to Estimates</span>
            </div>
            <Link
              href="/estimates"
              className="btn-ghost w-full text-xs gap-2 border border-white/[0.06]"
            >
              <ExternalLink size={13} />
              View All Estimates
            </Link>
          </div>

        </div>
      </div>
    </div>
  )
}
