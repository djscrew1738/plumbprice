'use client'

import Link from 'next/link'
import { CheckCircle2, ExternalLink } from 'lucide-react'
import { cn, formatCurrency, formatCurrencyDecimal } from '@/lib/utils'
import { ConfidenceBadge } from '@/components/estimator/ConfidenceBadge'
import { MarketAdjustmentBadge } from './MarketAdjustmentBadge'
import type { EstimateBreakdownV3 as EstimateBreakdownV3Type } from '@/lib/api-v3'

interface Props {
  estimate: EstimateBreakdownV3Type
  confidenceLabel: string
  confidenceScore: number
  assumptions: string[]
  county: string
  marketAdjustments?: Array<{ name: string; category: string; factor: number }>
  compact?: boolean
  savedEstimateId?: number | null
}

export function EstimateBreakdownV3({
  estimate,
  confidenceLabel,
  confidenceScore,
  assumptions,
  county,
  marketAdjustments = [],
  compact = false,
  savedEstimateId,
}: Props) {
  const total = estimate.grand_total || 1
  const costRows = [
    { label: 'Labor', value: estimate.labor_total, color: 'bg-[color:var(--accent)]', pct: estimate.labor_total / total },
    { label: 'Materials', value: estimate.materials_total, color: 'bg-amber-500', pct: estimate.materials_total / total },
    { label: 'Markup', value: estimate.markup_total, color: 'bg-emerald-500', pct: estimate.markup_total / total },
    { label: 'Misc', value: estimate.misc_total, color: 'bg-orange-500', pct: estimate.misc_total / total },
    { label: `Tax (${county})`, value: estimate.tax_total, color: 'bg-zinc-500', pct: estimate.tax_total / total },
  ].filter(row => row.value > 0)

  const hasMarketAdjustments = marketAdjustments.length > 0
  const pad = compact ? 'px-4 py-3.5' : 'px-5 py-4'

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className={cn('shrink-0 border-b border-[color:var(--line)] bg-[color:var(--panel-strong)]', pad)}>
        <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">
          Recommended Price
        </div>
        <div className={cn('mb-3 font-extrabold leading-none text-[color:var(--ink)]', compact ? 'text-4xl' : 'text-5xl')}>
          {formatCurrency(estimate.grand_total)}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ConfidenceBadge label={confidenceLabel} score={confidenceScore || 0} size="md" />
          {hasMarketAdjustments && (
            <span className="text-[10px] text-[color:var(--muted-ink)]">
              adj. ×{estimate.market_adjustment_applied.toFixed(3)}
            </span>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className={cn('space-y-3', compact ? 'p-4' : 'p-5')}>
          {/* Market Adjustments */}
          {hasMarketAdjustments && (
            <div className="card-sm overflow-hidden">
              <div className="px-4 pb-1 pt-3.5">
                <h3 className="mb-2 text-[10px] font-bold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">
                  Market Adjustments
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {marketAdjustments.map(ma => (
                    <MarketAdjustmentBadge
                      key={ma.name}
                      name={ma.name}
                      category={ma.category}
                      factor={ma.factor}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Cost Breakdown */}
          <div className="card-sm overflow-hidden">
            <div className="px-4 pb-3 pt-4">
              <h3 className="mb-3 text-[10px] font-bold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">Cost Breakdown</h3>
              <div className="space-y-2.5">
                {costRows.map(row => (
                  <div key={row.label}>
                    <div className="mb-1 flex items-center justify-between text-xs">
                      <span className="text-[color:var(--muted-ink)]">{row.label}</span>
                      <span className="font-semibold text-[color:var(--ink)]">{formatCurrencyDecimal(row.value)}</span>
                    </div>
                    <div className="h-1 rounded-full bg-[color:var(--panel-strong)]">
                      <div className={cn('cost-bar', row.color)} style={{ width: `${Math.max(row.pct * 100, 2)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-3.5 flex items-center justify-between border-t border-[color:var(--line)] pt-3">
                <span className="text-xs font-bold text-[color:var(--ink)]">Total</span>
                <span className="text-base font-extrabold text-[color:var(--ink)]">{formatCurrency(estimate.grand_total)}</span>
              </div>
            </div>
          </div>

          {/* Line Items */}
          {estimate.line_items.length > 0 && (
            <div className="card-sm overflow-hidden">
              <div className="px-4 pb-1 pt-3.5">
                <h3 className="text-[10px] font-bold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">
                  Line Items <span className="normal-case text-[color:var(--muted-ink)]">({estimate.line_items.length})</span>
                </h3>
              </div>
              <div className="divide-y divide-[color:var(--line)]">
                {estimate.line_items.map((item, i) => (
                  <div key={i} className="flex items-center justify-between px-4 py-2.5">
                    <div className="min-w-0">
                      <p className="truncate text-xs font-medium text-[color:var(--ink)]">{item.description}</p>
                      <p className="text-[10px] text-[color:var(--muted-ink)]">
                        {item.quantity} {item.unit} × {formatCurrencyDecimal(item.unit_cost)}
                        {item.supplier && <span className="ml-1.5 rounded bg-[color:var(--panel-strong)] px-1 py-0.5 text-[9px]">{item.supplier}</span>}
                      </p>
                    </div>
                    <span className="shrink-0 pl-3 text-xs font-semibold text-[color:var(--ink)]">{formatCurrencyDecimal(item.total_cost)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Assumptions */}
          {assumptions.length > 0 && (
            <div className="card-sm overflow-hidden">
              <div className="px-4 pb-3 pt-3.5">
                <h3 className="mb-2.5 text-[10px] font-bold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">Assumptions</h3>
                <ul className="space-y-2">
                  {assumptions.map((a, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-[color:var(--muted-ink)]">
                      <CheckCircle2 size={13} className="mt-0.5 shrink-0 text-[color:var(--accent)]" />
                      <span>{a}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Saved estimate link */}
          {savedEstimateId && (
            <div className="px-1">
              <Link
                href={`/estimates/${savedEstimateId}`}
                className="inline-flex items-center gap-1.5 text-xs font-medium text-[color:var(--accent-strong)] hover:underline"
              >
                View saved estimate <ExternalLink size={12} />
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
