'use client'

import { useMemo, useId } from 'react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn, formatCurrencyDecimal } from '@/lib/utils'
import { usePriceHistory } from '@/lib/hooks'
import { Modal } from '@/components/ui/Modal'
import { Badge } from '@/components/ui/Badge'
import { Skeleton } from '@/components/ui/Skeleton'

// ─── Types ──────────────────────────────────────────────────────────────────

export interface PriceHistoryModalProps {
  open: boolean
  onClose: () => void
  itemId: string
  itemName: string
}

// ─── SVG Line Chart ─────────────────────────────────────────────────────────

const CHART_W = 520
const CHART_H = 180
const PAD = { top: 20, right: 16, bottom: 32, left: 52 }

function PriceLineChart({ entries }: { entries: { price: number; date: string }[] }) {
  const id = useId()

  const { points, xLabels, yTicks, plotW, plotH, minY, rangeY } = useMemo(() => {
    const prices = entries.map(e => e.price)
    const minY = Math.min(...prices) * 0.95
    const maxY = Math.max(...prices) * 1.05
    const rangeY = maxY - minY || 1
    const plotW = CHART_W - PAD.left - PAD.right
    const plotH = CHART_H - PAD.top - PAD.bottom

    const pts = entries.map((e, i) => ({
      x: PAD.left + (entries.length > 1 ? (i / (entries.length - 1)) * plotW : plotW / 2),
      y: PAD.top + plotH - ((e.price - minY) / rangeY) * plotH,
      price: e.price,
      date: e.date,
    }))

    const yTicks = Array.from({ length: 4 }, (_, i) => minY + (rangeY * i) / 3)
    const step = Math.max(1, Math.floor(entries.length / 5))
    const xLabels = entries.filter((_, i) => i % step === 0 || i === entries.length - 1)
      .map((e, _i, arr) => {
        const idx = entries.indexOf(e)
        return {
          x: PAD.left + (entries.length > 1 ? (idx / (entries.length - 1)) * plotW : plotW / 2),
          label: new Date(e.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        }
      })

    return { points: pts, xLabels, yTicks, plotW, plotH, minY, rangeY }
  }, [entries])

  if (entries.length === 0) return null

  const polyline = points.map(p => `${p.x},${p.y}`).join(' ')

  // gradient fill area
  const areaPath = entries.length > 1
    ? `M${points[0].x},${PAD.top + plotH} ` +
      points.map(p => `L${p.x},${p.y}`).join(' ') +
      ` L${points[points.length - 1].x},${PAD.top + plotH} Z`
    : ''

  return (
    <svg
      viewBox={`0 0 ${CHART_W} ${CHART_H}`}
      className="w-full"
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="Price history chart"
    >
      <defs>
        <linearGradient id={`${id}-grad`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.2} />
          <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
        </linearGradient>
      </defs>

      {/* Grid lines + Y labels */}
      {yTicks.map((tick, i) => {
        const y = PAD.top + plotH - ((tick - minY) / rangeY) * plotH
        return (
          <g key={`y-${i}`}>
            <line x1={PAD.left} x2={CHART_W - PAD.right} y1={y} y2={y}
              stroke="var(--line)" strokeWidth={1} strokeDasharray="4 4" />
            <text x={PAD.left - 6} y={y + 4} textAnchor="end" fontSize={10}
              fill="var(--muted-ink)" fontFamily="inherit">
              ${tick.toFixed(0)}
            </text>
          </g>
        )
      })}

      {/* Area fill */}
      {areaPath && <path d={areaPath} fill={`url(#${id}-grad)`} />}

      {/* Line */}
      <polyline points={polyline} fill="none" stroke="var(--accent)"
        strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />

      {/* Dots */}
      {points.map((p, i) => (
        <circle key={`dot-${i}`} cx={p.x} cy={p.y} r={3}
          fill="var(--accent)" stroke="var(--panel)" strokeWidth={2} />
      ))}

      {/* X labels */}
      {xLabels.map((lbl, i) => (
        <text key={`x-${i}`} x={lbl.x} y={CHART_H - 6} textAnchor="middle"
          fontSize={10} fill="var(--muted-ink)" fontFamily="inherit">
          {lbl.label}
        </text>
      ))}
    </svg>
  )
}

// ─── Trend Icon ─────────────────────────────────────────────────────────────

function TrendIndicator({ trend }: { trend: 'up' | 'down' | 'stable' }) {
  if (trend === 'up') return <TrendingUp size={14} className="text-red-500" />
  if (trend === 'down') return <TrendingDown size={14} className="text-emerald-500" />
  return <Minus size={14} className="text-[color:var(--muted-ink)]" />
}

const trendLabel: Record<string, string> = { up: 'Increasing', down: 'Decreasing', stable: 'Stable' }
const trendColor: Record<string, 'danger' | 'success' | 'neutral'> = {
  up: 'danger', down: 'success', stable: 'neutral',
}

// ─── Component ──────────────────────────────────────────────────────────────

export function PriceHistoryModal({ open, onClose, itemId, itemName }: PriceHistoryModalProps) {
  const { data, isLoading } = usePriceHistory(itemId, { enabled: open && !!itemId })

  return (
    <Modal open={open} onClose={onClose} title="Price History" description={itemName} size="lg">
      {isLoading && (
        <div className="space-y-3">
          <Skeleton variant="card" className="h-44 rounded-xl" />
          <div className="grid grid-cols-3 gap-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} variant="card" className="h-16 rounded-xl" />
            ))}
          </div>
        </div>
      )}

      {!isLoading && data && (
        <div className="space-y-4">
          {/* Summary stats */}
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <div className="card-inset p-3 text-center">
              <div className="text-[10px] text-[color:var(--muted-ink)] font-medium uppercase tracking-wider">Min</div>
              <div className="text-sm font-bold text-emerald-600">{formatCurrencyDecimal(data.min_price)}</div>
            </div>
            <div className="card-inset p-3 text-center">
              <div className="text-[10px] text-[color:var(--muted-ink)] font-medium uppercase tracking-wider">Max</div>
              <div className="text-sm font-bold text-red-500">{formatCurrencyDecimal(data.max_price)}</div>
            </div>
            <div className="card-inset p-3 text-center">
              <div className="text-[10px] text-[color:var(--muted-ink)] font-medium uppercase tracking-wider">Average</div>
              <div className="text-sm font-bold text-[color:var(--ink)]">{formatCurrencyDecimal(data.avg_price)}</div>
            </div>
            <div className="card-inset p-3 text-center">
              <div className="text-[10px] text-[color:var(--muted-ink)] font-medium uppercase tracking-wider">Trend</div>
              <div className="flex items-center justify-center gap-1 mt-0.5">
                <TrendIndicator trend={data.trend} />
                <Badge variant={trendColor[data.trend]} size="sm">{trendLabel[data.trend]}</Badge>
              </div>
            </div>
          </div>

          {/* Chart */}
          {data.entries.length > 1 && (
            <div className="card-inset p-3 rounded-xl">
              <PriceLineChart entries={data.entries} />
            </div>
          )}

          {/* Table */}
          <div className="card-inset rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[color:var(--line)] bg-[color:var(--panel-strong)]">
                  <th className="px-4 py-2.5 text-left text-[10px] font-bold text-[color:var(--muted-ink)] uppercase tracking-widest">Date</th>
                  <th className="px-4 py-2.5 text-right text-[10px] font-bold text-[color:var(--muted-ink)] uppercase tracking-widest">Price</th>
                  <th className="px-4 py-2.5 text-right text-[10px] font-bold text-[color:var(--muted-ink)] uppercase tracking-widest">Change</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[color:var(--line)]">
                {data.entries.slice().reverse().map((entry, i) => (
                  <tr key={i} className="hover:bg-[color:var(--panel-strong)] transition-colors">
                    <td className="px-4 py-2 text-[color:var(--ink)]">
                      {new Date(entry.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </td>
                    <td className="px-4 py-2 text-right font-medium tabular-nums text-[color:var(--ink)]">
                      {formatCurrencyDecimal(entry.price)}
                    </td>
                    <td className="px-4 py-2 text-right">
                      {entry.change_pct != null && entry.change_pct !== 0 ? (
                        <span className={cn('text-xs font-semibold tabular-nums',
                          entry.change_pct > 0 ? 'text-red-500' : 'text-emerald-500'
                        )}>
                          {entry.change_pct > 0 ? '+' : ''}{entry.change_pct.toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-xs text-[color:var(--muted-ink)]">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data.entries.length === 0 && (
            <p className="text-center text-sm text-[color:var(--muted-ink)] py-6">
              No price history available for this item.
            </p>
          )}
        </div>
      )}

      {!isLoading && !data && (
        <p className="text-center text-sm text-[color:var(--muted-ink)] py-8">
          Could not load price history.
        </p>
      )}
    </Modal>
  )
}
