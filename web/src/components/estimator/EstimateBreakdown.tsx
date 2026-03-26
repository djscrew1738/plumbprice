'use client'

import { useState } from 'react'
import { ChevronDown, ChevronUp, CheckCircle2, AlertCircle, XCircle, FileOutput, Save } from 'lucide-react'
import { cn, formatCurrency, formatCurrencyDecimal, getConfidenceColor } from '@/lib/utils'
import type { EstimateBreakdown as EstimateBreakdownType } from '@/types'

interface Props {
  estimate: EstimateBreakdownType
  confidenceLabel: string
  confidenceScore: number
  assumptions: string[]
  county: string
  compact?: boolean
}

const CONFIDENCE_ICON = {
  HIGH: CheckCircle2,
  MEDIUM: AlertCircle,
  LOW: XCircle,
}

export function EstimateBreakdown({
  estimate, confidenceLabel, confidenceScore, assumptions, county, compact = false
}: Props) {
  const [showItems, setShowItems] = useState(false)

  const label = confidenceLabel?.toUpperCase() as 'HIGH' | 'MEDIUM' | 'LOW'
  const ConfIcon = CONFIDENCE_ICON[label] ?? CheckCircle2

  const rows = [
    { label: 'Labor', value: estimate.labor_total, className: 'text-blue-400 font-semibold' },
    { label: 'Materials', value: estimate.materials_total, className: 'text-zinc-300' },
    ...(estimate.markup_total > 0 ? [{ label: 'Materials Markup', value: estimate.markup_total, className: 'text-zinc-500' }] : []),
    ...(estimate.misc_total > 0 ? [{ label: 'Misc / Disposal', value: estimate.misc_total, className: 'text-zinc-500' }] : []),
    { label: `Tax (${county} Co.)`, value: estimate.tax_total, className: 'text-zinc-500' },
  ]

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Hero total */}
      <div className={cn('bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 text-white shrink-0', compact ? 'px-5 py-4' : 'px-6 py-5')}>
        <div className="text-xs font-semibold uppercase tracking-wider text-blue-200 mb-1">
          Recommended Price
        </div>
        <div className={cn('font-extrabold leading-none mb-2', compact ? 'text-4xl' : 'text-5xl')}>
          {formatCurrency(estimate.grand_total)}
        </div>
        <div className={cn(
          'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold',
          label === 'HIGH' ? 'bg-emerald-500/20 text-emerald-200' :
          label === 'MEDIUM' ? 'bg-amber-500/20 text-amber-200' :
          'bg-red-500/20 text-red-200'
        )}>
          <ConfIcon size={12} />
          {label} Confidence . {Math.round((confidenceScore || 0) * 100)}%
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        <div className={cn('space-y-3', compact ? 'p-4' : 'p-5')}>

          {/* Cost breakdown */}
          <div className="card-sm p-4">
            <h3 className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-3">Cost Breakdown</h3>
            <div className="space-y-2.5">
              {rows.map(row => (
                <div key={row.label} className="flex justify-between items-center text-sm">
                  <span className="text-zinc-400">{row.label}</span>
                  <span className={cn('font-semibold', row.className)}>
                    {formatCurrencyDecimal(row.value)}
                  </span>
                </div>
              ))}
              <div className="border-t border-white/5 pt-2.5 flex justify-between items-center">
                <span className="text-sm font-bold text-white">Total</span>
                <span className="text-lg font-extrabold text-white">{formatCurrency(estimate.grand_total)}</span>
              </div>
            </div>
          </div>

          {/* Line items toggle */}
          <div className="card-sm overflow-hidden">
            <button
              onClick={() => setShowItems(!showItems)}
              className="w-full px-4 py-3 flex items-center justify-between text-sm font-semibold text-zinc-300 hover:bg-white/5 transition-colors"
            >
              <span>Line Items <span className="text-zinc-500 font-normal">({estimate.line_items.length})</span></span>
              {showItems ? <ChevronUp size={16} className="text-zinc-500" /> : <ChevronDown size={16} className="text-zinc-500" />}
            </button>
            {showItems && (
              <div className="border-t border-white/5 divide-y divide-white/5">
                {estimate.line_items.map((item, i) => (
                  <div key={i} className="px-4 py-3">
                    <div className="flex justify-between items-start gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-semibold text-zinc-200 leading-tight">{item.description}</div>
                        <div className="text-[11px] text-zinc-500 mt-0.5">
                          {item.quantity} {item.unit} x {formatCurrencyDecimal(item.unit_cost)}
                          {item.supplier && (
                            <span className="ml-1.5 px-1.5 py-0.5 bg-white/5 rounded text-zinc-400 font-mono border border-white/[0.06]">{item.supplier}</span>
                          )}
                        </div>
                      </div>
                      <div className="text-xs font-bold text-white shrink-0">
                        {formatCurrencyDecimal(item.total_cost)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Assumptions */}
          {assumptions.length > 0 && (
            <div className="card-sm p-4">
              <h3 className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2.5">Assumptions</h3>
              <ul className="space-y-1.5">
                {assumptions.map((a, i) => (
                  <li key={i} className="text-xs text-zinc-400 flex gap-2">
                    <span className="text-blue-400 shrink-0 mt-0.5">*</span>
                    {a}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Actions */}
          <div className="space-y-2 pt-1">
            <button className="btn-primary w-full gap-2 text-sm">
              <FileOutput size={16} />
              View Proposal
            </button>
            <button className="btn-secondary w-full gap-2 text-sm">
              <Save size={16} />
              Save Estimate
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
