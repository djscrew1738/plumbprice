'use client'

import Link from 'next/link'
import { CheckCheck, CheckCircle2, ExternalLink } from 'lucide-react'
import { cn, formatCurrency, formatCurrencyDecimal } from '@/lib/utils'
import type { EstimateBreakdown as EstimateBreakdownType } from '@/types'
import { ConfidenceBadge } from './ConfidenceBadge'

interface Props {
  estimate: EstimateBreakdownType
  confidenceLabel: string
  confidenceScore: number
  assumptions: string[]
  county: string
  compact?: boolean
  savedEstimateId?: number | null
}

export function EstimateBreakdown({
  estimate,
  confidenceLabel,
  confidenceScore,
  assumptions,
  county,
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
        <ConfidenceBadge label={confidenceLabel} score={confidenceScore || 0} size="md" />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className={cn('space-y-3', compact ? 'p-4' : 'p-5')}>
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

          {estimate.line_items.length > 0 && (
            <div className="card-sm overflow-hidden">
              <div className="px-4 pb-1 pt-3.5">
                <h3 className="text-[10px] font-bold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">
                  Line Items <span className="normal-case text-[color:var(--muted-ink)]">({estimate.line_items.length})</span>
                </h3>
              </div>
              <div className="divide-y divide-[color:var(--line)]">
                {estimate.line_items.map((item, index) => (
                  <div key={`${item.description}-${index}`} className="flex items-start justify-between gap-3 px-4 py-2.5">
                    <div className="min-w-0 flex-1">
                      <div className="text-xs font-medium leading-snug text-[color:var(--ink)]">{item.description}</div>
                      <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[10px] text-[color:var(--muted-ink)]">
                        <span>{item.quantity} {item.unit} × {formatCurrencyDecimal(item.unit_cost)}</span>
                        {item.supplier && (
                          <span className="rounded border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-1.5 py-px font-mono text-[color:var(--muted-ink)]">
                            {item.supplier}
                          </span>
                        )}
                      </div>
                    </div>
                    <span className="shrink-0 text-xs font-bold text-[color:var(--ink)]">
                      {formatCurrencyDecimal(item.total_cost)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {assumptions.length > 0 && (
            <div className="card-sm p-4">
              <h3 className="mb-3 text-[10px] font-bold text-[color:var(--muted-ink)]">Assumptions</h3>
              <ul className="space-y-2">
                {assumptions.map((assumption, index) => (
                  <li key={`assumption-${index}-${assumption.slice(0, 24)}`} className="flex gap-2 text-xs leading-relaxed text-[color:var(--muted-ink)]">
                    <CheckCircle2 size={12} className="mt-0.5 shrink-0 text-emerald-600" />
                    {assumption}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="space-y-2 pt-1">
            <div className="btn-secondary pointer-events-none w-full cursor-default gap-2 text-xs opacity-65">
              <CheckCheck size={14} className="text-emerald-600" />
              <span>Saved to Estimates</span>
            </div>
            {savedEstimateId ? (
              <Link href={`/estimates/${savedEstimateId}`} className="btn-primary w-full gap-2 text-xs">
                <ExternalLink size={13} />
                View This Estimate
              </Link>
            ) : null}
            <Link href="/estimates" className="btn-ghost w-full gap-2 border border-[color:var(--line)] text-xs">
              <ExternalLink size={13} />
              View All Estimates
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
