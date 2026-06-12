'use client'

import Link from 'next/link'
import { CheckCircle2, ExternalLink } from 'lucide-react'
import { cn, formatCurrency, formatCurrencyDecimal } from '@/lib/utils'
import { ConfidenceBadge } from '@/components/ui/ConfidenceBadge'
import { MarketAdjustmentBadge } from './MarketAdjustmentBadge'
import type { EstimateBreakdownV3 as EstimateBreakdownV3Type } from '@/lib/api-v3'
import dynamic from 'next/dynamic'
import { useState, useCallback, useEffect, useRef } from 'react'
import { ProfitMarginIndicator } from './charts/ProfitMarginIndicator'

const WaterfallChart = dynamic(() => import('./charts/WaterfallChart').then(m => ({ default: m.WaterfallChart })), { ssr: false })
const MarketAdjustmentMap = dynamic(() => import('./charts/MarketAdjustmentMap').then(m => ({ default: m.MarketAdjustmentMap })), { ssr: false })

interface Props {
  estimate: EstimateBreakdownV3Type
  confidenceLabel: string
  confidenceScore: number
  assumptions: string[]
  county: string
  marketAdjustments?: Array<{ name: string; category: string; factor: number }>
  compact?: boolean
  savedEstimateId?: number | null
  onLineItemChange?: (index: number, quantity: number) => void
  estimateId?: number | null
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
  onLineItemChange,
  estimateId,
}: Props) {
  const total = estimate.grand_total || 1
  const costRows = [
    { label: 'Labor', value: estimate.labor_total, color: '#3b82f6', pct: estimate.labor_total / total },
    { label: 'Materials', value: estimate.materials_total, color: '#f59e0b', pct: estimate.materials_total / total },
    { label: 'Markup', value: estimate.markup_total, color: '#10b981', pct: estimate.markup_total / total },
    { label: 'Misc', value: estimate.misc_total, color: '#f97316', pct: estimate.misc_total / total },
    { label: `Tax (${county})`, value: estimate.tax_total, color: '#71717a', pct: estimate.tax_total / total },
  ].filter(row => row.value > 0)

  const hasMarketAdjustments = marketAdjustments.length > 0
  const pad = compact ? 'px-4 py-3.5' : 'px-5 py-4'

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden" data-testid="estimate-breakdown">
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
              {!compact && (
                <div className="px-4 pb-3">
                  <MarketAdjustmentMap adjustments={marketAdjustments} />
                </div>
              )}
            </div>
          )}

          {/* Cost Breakdown */}
          <div className="card-sm overflow-hidden">
            <div className="px-4 pb-3 pt-4">
              <h3 className="mb-3 text-[10px] font-bold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">Cost Breakdown</h3>
              {!compact && (
                <WaterfallChart
                  data={costRows.map(r => ({ name: r.label, value: r.value, color: r.color }))}
                  total={total}
                  className="mb-3"
                />
              )}
              <div className="space-y-2.5">
                {costRows.map(row => (
                  <div key={row.label}>
                    <div className="mb-1 flex items-center justify-between text-xs">
                      <span className="text-[color:var(--muted-ink)]">{row.label}</span>
                      <span className="font-semibold text-[color:var(--ink)]">{formatCurrencyDecimal(row.value)}</span>
                    </div>
                    <div className="h-1 rounded-full bg-[color:var(--panel-strong)]">
                      <div className="cost-bar" style={{ width: `${Math.max(row.pct * 100, 2)}%`, backgroundColor: row.color }} />
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
                  <LineItemRow
                    key={i}
                    item={item}
                    index={i}
                    onQuantityChange={onLineItemChange}
                    editable={!!onLineItemChange && !!estimateId}
                  />
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

interface LineItemRowProps {
  item: EstimateBreakdownV3Type['line_items'][number]
  index: number
  onQuantityChange?: (index: number, quantity: number) => void
  editable: boolean
}

function LineItemRow({ item, index, onQuantityChange, editable }: LineItemRowProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [draftQty, setDraftQty] = useState(String(item.quantity))
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isEditing) {
      inputRef.current?.focus()
      inputRef.current?.select()
    }
  }, [isEditing])

  const handleBlur = useCallback(() => {
    const num = parseFloat(draftQty)
    if (!isNaN(num) && num > 0 && num !== item.quantity) {
      onQuantityChange?.(index, num)
    } else {
      setDraftQty(String(item.quantity))
    }
    setIsEditing(false)
  }, [draftQty, item.quantity, index, onQuantityChange])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleBlur()
    }
  }, [handleBlur])

  // Estimate cost for margin indicator (assume 60% of unit_cost is actual cost for materials, 40% for labor)
  const estimatedCost = item.line_type === 'labor'
    ? item.unit_cost * 0.4
    : item.unit_cost * 0.6

  return (
    <div className="px-4 py-2.5">
      <div className="flex items-center justify-between">
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-medium text-[color:var(--ink)]">{item.description}</p>
          <div className="flex items-center gap-1.5 text-[10px] text-[color:var(--muted-ink)]">
            {isEditing ? (
              <input
                type="number"
                value={draftQty}
                onChange={e => setDraftQty(e.target.value)}
                onBlur={handleBlur}
                onKeyDown={handleKeyDown}
                className="w-16 rounded border border-[color:var(--line)] bg-[color:var(--panel)] px-1 py-0.5 text-[10px] text-[color:var(--ink)]"
                ref={inputRef}
                step="0.1"
                min="0"
              />
            ) : (
              <button
                type="button"
                onClick={() => editable && setIsEditing(true)}
                className={cn(
                  'rounded px-1 py-0.5 transition-colors',
                  editable ? 'hover:bg-[color:var(--panel-strong)] cursor-pointer' : 'cursor-default'
                )}
                title={editable ? 'Click to edit quantity' : undefined}
              >
                {item.quantity} {item.unit}
              </button>
            )}
            <span>× {formatCurrencyDecimal(item.unit_cost)}</span>
            {item.supplier && <span className="rounded bg-[color:var(--panel-strong)] px-1 py-0.5 text-[9px]">{item.supplier}</span>}
          </div>
          {!isEditing && (
            <div className="mt-1.5">
              <ProfitMarginIndicator cost={estimatedCost * item.quantity} price={item.total_cost} />
            </div>
          )}
        </div>
        <span className="shrink-0 pl-3 text-xs font-semibold text-[color:var(--ink)]">{formatCurrencyDecimal(item.total_cost)}</span>
      </div>
    </div>
  )
}
