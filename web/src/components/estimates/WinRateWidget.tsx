'use client'

import { useQuery } from '@tanstack/react-query'
import { TrendingUp, TrendingDown, BarChart3 } from 'lucide-react'
import { outcomesApi } from '@/lib/api'

interface Props {
  /** Markup as a fraction of cost, e.g. 0.28 for 28%. */
  markupPct: number
  /** Band half-width in percentage points (default 5pp -> ±5pp). */
  bandPp?: number
  className?: string
}

/**
 * Read-only "Your win rate at this markup is X%" widget. Surfaces historical
 * outcomes; never auto-adjusts pricing.
 */
export function WinRateWidget({ markupPct, bandPp = 5, className }: Props) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['winrate', 'markup', markupPct, bandPp],
    queryFn: async () =>
      (await outcomesApi.winrateByMarkup(markupPct, bandPp)).data,
    staleTime: 5 * 60_000,
    enabled: Number.isFinite(markupPct) && markupPct >= 0,
  })

  if (isLoading || isError || !data) return null

  const inBand = data.in_band
  const overall = data.overall

  // Need at least a few decided estimates to be meaningful.
  if (inBand.n < 3 && overall.n < 3) return null

  const useBand = inBand.n >= 3
  const wr = useBand ? inBand.win_rate : overall.win_rate
  const n = useBand ? inBand.n : overall.n
  if (wr == null) return null

  const pct = Math.round(wr * 100)
  const trending =
    pct >= 60 ? 'up' : pct <= 40 ? 'down' : 'flat'

  return (
    <div
      className={[
        'flex items-start gap-3 rounded-lg border border-zinc-800 bg-zinc-900/40 px-3 py-2 text-sm',
        className ?? '',
      ].join(' ')}
      role="status"
      aria-label={`Historical win rate at this markup: ${pct} percent`}
    >
      {trending === 'up' ? (
        <TrendingUp className="mt-0.5 h-4 w-4 text-emerald-400" />
      ) : trending === 'down' ? (
        <TrendingDown className="mt-0.5 h-4 w-4 text-amber-400" />
      ) : (
        <BarChart3 className="mt-0.5 h-4 w-4 text-zinc-400" />
      )}
      <div className="flex-1 leading-tight">
        <div className="text-zinc-100">
          Your win rate at this markup is{' '}
          <span className="font-semibold">{pct}%</span>
        </div>
        <div className="text-xs text-zinc-500">
          {useBand
            ? `Based on ${n} decided estimates within ±${bandPp}pp of ${Math.round(
                markupPct * 100,
              )}%.`
            : `Based on ${n} decided estimates overall (not enough history near ${Math.round(
                markupPct * 100,
              )}% yet).`}
        </div>
      </div>
    </div>
  )
}
