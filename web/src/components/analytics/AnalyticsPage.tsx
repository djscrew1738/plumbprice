'use client'

import { useMemo, useState } from 'react'
import {
  FileText,
  Trophy,
  DollarSign,
  TrendingUp,
  BarChart3,
  PieChart,
  Target,
  ArrowUpDown,
} from 'lucide-react'

import { useEstimateStats, useOutcomes } from '@/lib/hooks'
import type { OutcomeListItem, OutcomeValue } from '@/lib/api'
import { formatCurrency } from '@/lib/utils'

import { StatCard } from '@/components/ui/StatCard'
import { DonutChart, type DonutSegment } from '@/components/ui/DonutChart'
import { BarChart, type BarDatum } from '@/components/ui/BarChart'
import { DataTable, type Column } from '@/components/ui/DataTable'
import { Badge } from '@/components/ui/Badge'
import { ProgressBar } from '@/components/ui/ProgressBar'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'

// ─── Helpers ────────────────────────────────────────────────────────────────

function pct(n: number, d: number) {
  return d > 0 ? Math.round((n / d) * 100) : 0
}

function monthKey(iso: string) {
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function monthLabel(key: string) {
  const [y, m] = key.split('-')
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
  return `${months[Number(m) - 1]} ${y.slice(2)}`
}

const OUTCOME_BADGE: Record<OutcomeValue, { variant: 'success' | 'danger' | 'warning' | 'neutral'; label: string }> = {
  won:     { variant: 'success', label: 'Won' },
  lost:    { variant: 'danger',  label: 'Lost' },
  pending: { variant: 'warning', label: 'Pending' },
  no_bid:  { variant: 'neutral', label: 'No Bid' },
}

// ─── Derived data hooks ─────────────────────────────────────────────────────

function useDerivedAnalytics(outcomes: OutcomeListItem[] | undefined) {
  return useMemo(() => {
    if (!outcomes?.length) {
      return {
        totalEstimates: 0,
        winRate: 0,
        avgEstimateValue: 0,
        totalRevenueWon: 0,
        confidenceTiers: [] as DonutSegment[],
        monthlyTrends: [] as { month: string; won: number; lost: number }[],
        avgEstimate: 0,
        avgFinal: 0,
        accuracyPct: 0,
        jobTypeStats: [] as { jobType: string; total: number; won: number; winRate: number }[],
      }
    }

    const decided = outcomes.filter(o => o.outcome === 'won' || o.outcome === 'lost')
    const wonItems = outcomes.filter(o => o.outcome === 'won')

    const totalEstimates = outcomes.length
    const winRate = pct(wonItems.length, decided.length)
    const avgEstimateValue = outcomes.reduce((s, o) => s + (o.estimate_grand_total ?? 0), 0) / totalEstimates
    const totalRevenueWon = wonItems.reduce((s, o) => s + (o.final_price ?? o.estimate_grand_total ?? 0), 0)

    // Confidence tiers
    const tiers = { high: { total: 0, won: 0 }, medium: { total: 0, won: 0 }, low: { total: 0, won: 0 } }
    for (const o of decided) {
      const score = o.confidence_score ?? 0
      const tier = score > 80 ? 'high' : score >= 50 ? 'medium' : 'low'
      tiers[tier].total++
      if (o.outcome === 'won') tiers[tier].won++
    }
    const confidenceTiers: DonutSegment[] = [
      { label: `High (${pct(tiers.high.won, tiers.high.total)}%)`, value: tiers.high.total, color: 'hsl(var(--success))' },
      { label: `Med (${pct(tiers.medium.won, tiers.medium.total)}%)`, value: tiers.medium.total, color: 'hsl(var(--warning))' },
      { label: `Low (${pct(tiers.low.won, tiers.low.total)}%)`, value: tiers.low.total, color: 'hsl(var(--danger))' },
    ].filter(s => s.value > 0)

    // Monthly trends (last 6 months)
    const monthMap = new Map<string, { won: number; lost: number }>()
    for (const o of decided) {
      const mk = monthKey(o.created_at)
      const entry = monthMap.get(mk) ?? { won: 0, lost: 0 }
      if (o.outcome === 'won') entry.won++
      else entry.lost++
      monthMap.set(mk, entry)
    }
    const monthlyTrends = Array.from(monthMap.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-6)
      .map(([m, v]) => ({ month: monthLabel(m), ...v }))

    // Estimate vs final price
    const withFinal = wonItems.filter(o => o.final_price != null && o.estimate_grand_total != null)
    const avgEstimate = withFinal.length
      ? withFinal.reduce((s, o) => s + (o.estimate_grand_total ?? 0), 0) / withFinal.length
      : 0
    const avgFinal = withFinal.length
      ? withFinal.reduce((s, o) => s + (o.final_price ?? 0), 0) / withFinal.length
      : 0
    const accuracyPct = avgFinal > 0 ? Math.round((1 - Math.abs(avgEstimate - avgFinal) / avgFinal) * 100) : 0

    // Win rate by job type
    const jtMap = new Map<string, { total: number; won: number }>()
    for (const o of decided) {
      const jt = o.job_type ?? 'Unknown'
      const entry = jtMap.get(jt) ?? { total: 0, won: 0 }
      entry.total++
      if (o.outcome === 'won') entry.won++
      jtMap.set(jt, entry)
    }
    const jobTypeStats = Array.from(jtMap.entries())
      .map(([jobType, v]) => ({ jobType, ...v, winRate: pct(v.won, v.total) }))
      .sort((a, b) => b.winRate - a.winRate)

    return {
      totalEstimates,
      winRate,
      avgEstimateValue,
      totalRevenueWon,
      confidenceTiers,
      monthlyTrends,
      avgEstimate,
      avgFinal,
      accuracyPct,
      jobTypeStats,
    }
  }, [outcomes])
}

// ─── Section wrapper ────────────────────────────────────────────────────────

function Section({ title, icon: Icon, children }: { title: string; icon: React.ElementType; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-5 shadow-[0_16px_32px_rgba(84,60,39,0.05)]">
      <div className="mb-4 flex items-center gap-2">
        <Icon className="h-4 w-4 text-[color:var(--accent-strong)]" />
        <h2 className="text-sm font-semibold text-[color:var(--ink)]">{title}</h2>
      </div>
      {children}
    </div>
  )
}

function SectionSkeleton() {
  return (
    <div className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-5">
      <Skeleton variant="text" className="mb-4 h-5 w-40" />
      <Skeleton variant="card" className="h-48" />
    </div>
  )
}

// ─── Stacked bar helper ─────────────────────────────────────────────────────

function StackedBarChart({
  data,
}: {
  data: { month: string; won: number; lost: number }[]
}) {
  const maxVal = Math.max(...data.map(d => d.won + d.lost), 1)
  return (
    <div className="flex items-end gap-2 h-48">
      {data.map((d) => {
        const total = d.won + d.lost
        const wonH = (d.won / maxVal) * 100
        const lostH = (d.lost / maxVal) * 100
        return (
          <div key={d.month} className="flex-1 flex flex-col items-center gap-1">
            <span className="text-[10px] font-semibold text-[color:var(--ink)] tabular-nums">
              {total}
            </span>
            <div className="w-full flex flex-col justify-end" style={{ height: '140px' }}>
              <div
                className="w-full rounded-t-md transition-all duration-500"
                style={{ height: `${lostH}%`, backgroundColor: 'hsl(var(--danger))' }}
              />
              <div
                className="w-full rounded-b-md transition-all duration-500"
                style={{
                  height: `${wonH}%`,
                  backgroundColor: 'hsl(var(--success))',
                  borderTopLeftRadius: lostH === 0 ? '0.375rem' : 0,
                  borderTopRightRadius: lostH === 0 ? '0.375rem' : 0,
                }}
              />
            </div>
            <span className="text-[10px] text-[color:var(--muted-ink)]">{d.month}</span>
          </div>
        )
      })}
    </div>
  )
}

// ─── Main component ─────────────────────────────────────────────────────────

export function AnalyticsPage() {
  const { data: stats, isLoading: statsLoading } = useEstimateStats()
  const { data: outcomes, isLoading: outcomesLoading } = useOutcomes()

  const loading = statsLoading || outcomesLoading
  const derived = useDerivedAnalytics(outcomes)

  const [sortKey, setSortKey] = useState('created_at')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(prev => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const sortedOutcomes = useMemo(() => {
    if (!outcomes) return []
    return [...outcomes].sort((a, b) => {
      let cmp = 0
      switch (sortKey) {
        case 'created_at':
          cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          break
        case 'estimate_grand_total':
          cmp = (a.estimate_grand_total ?? 0) - (b.estimate_grand_total ?? 0)
          break
        case 'final_price':
          cmp = (a.final_price ?? 0) - (b.final_price ?? 0)
          break
        case 'outcome':
          cmp = (a.outcome ?? '').localeCompare(b.outcome ?? '')
          break
        default:
          cmp = 0
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [outcomes, sortKey, sortDir])

  const recentOutcomeColumns: Column<OutcomeListItem>[] = useMemo(() => [
    {
      key: 'estimate_title',
      header: 'Project',
      sortable: false,
      render: (row) => (
        <span className="font-medium truncate max-w-[200px] block">
          {row.estimate_title ?? `Estimate #${row.estimate_id}`}
        </span>
      ),
    },
    {
      key: 'outcome',
      header: 'Outcome',
      sortable: true,
      render: (row) => {
        const cfg = OUTCOME_BADGE[row.outcome]
        return <Badge variant={cfg.variant} dot>{cfg.label}</Badge>
      },
    },
    {
      key: 'estimate_grand_total',
      header: 'Estimate',
      sortable: true,
      align: 'right' as const,
      render: (row) => (
        <span className="tabular-nums">{formatCurrency(row.estimate_grand_total)}</span>
      ),
    },
    {
      key: 'final_price',
      header: 'Final Price',
      sortable: true,
      align: 'right' as const,
      render: (row) => (
        <span className="tabular-nums">
          {row.final_price != null ? formatCurrency(row.final_price) : '—'}
        </span>
      ),
    },
    {
      key: 'variance',
      header: 'Variance',
      sortable: false,
      align: 'right' as const,
      render: (row) => {
        if (row.final_price == null || row.estimate_grand_total == null) return '—'
        const diff = row.final_price - row.estimate_grand_total
        const color = diff >= 0 ? 'text-emerald-500' : 'text-red-500'
        return (
          <span className={`tabular-nums font-medium ${color}`}>
            {diff >= 0 ? '+' : ''}{formatCurrency(diff)}
          </span>
        )
      },
    },
    {
      key: 'created_at',
      header: 'Date',
      sortable: true,
      render: (row) => (
        <span className="text-[color:var(--muted-ink)] tabular-nums">
          {new Date(row.created_at).toLocaleDateString()}
        </span>
      ),
    },
  ], [])

  // No data state
  if (!loading && (!outcomes || outcomes.length === 0)) {
    return (
      <div className="py-16">
        <EmptyState
          icon={<BarChart3 className="h-6 w-6" />}
          title="No outcome data yet"
          description="Record outcomes on your estimates to see analytics here."
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* A. Summary Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={FileText}
          label="Total Estimates"
          value={loading ? '—' : derived.totalEstimates.toLocaleString()}
          variant="accent"
          loading={loading}
        />
        <StatCard
          icon={Trophy}
          label="Win Rate"
          value={loading ? '—' : `${stats?.win_rate != null ? Math.round(stats.win_rate) : derived.winRate}%`}
          variant="success"
          loading={loading}
        />
        <StatCard
          icon={DollarSign}
          label="Avg Estimate Value"
          value={loading ? '—' : formatCurrency(derived.avgEstimateValue)}
          variant="accent"
          loading={loading}
        />
        <StatCard
          icon={TrendingUp}
          label="Total Revenue Won"
          value={loading ? '—' : formatCurrency(derived.totalRevenueWon)}
          variant="success"
          loading={loading}
        />
      </div>

      {/* B & C. Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* B. Win Rate by Confidence Tier */}
        {loading ? (
          <SectionSkeleton />
        ) : (
          <Section title="Win Rate by Confidence Tier" icon={PieChart}>
            {derived.confidenceTiers.length > 0 ? (
              <div className="flex justify-center">
                <DonutChart data={derived.confidenceTiers} size={200} thickness={30} />
              </div>
            ) : (
              <p className="text-sm text-[color:var(--muted-ink)] text-center py-8">
                No decided outcomes with confidence data
              </p>
            )}
          </Section>
        )}

        {/* C. Win/Loss Trends */}
        {loading ? (
          <SectionSkeleton />
        ) : (
          <Section title="Win / Loss Trends" icon={BarChart3}>
            {derived.monthlyTrends.length > 0 ? (
              <>
                <StackedBarChart data={derived.monthlyTrends} />
                <div className="mt-3 flex items-center justify-center gap-4 text-xs text-[color:var(--muted-ink)]">
                  <span className="flex items-center gap-1.5">
                    <span className="inline-block size-2.5 rounded-full" style={{ backgroundColor: 'hsl(var(--success))' }} />
                    Won
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="inline-block size-2.5 rounded-full" style={{ backgroundColor: 'hsl(var(--danger))' }} />
                    Lost
                  </span>
                </div>
              </>
            ) : (
              <p className="text-sm text-[color:var(--muted-ink)] text-center py-8">
                No monthly trend data available
              </p>
            )}
          </Section>
        )}
      </div>

      {/* D & E. Accuracy + Job Type */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* D. Estimate vs Final Price */}
        {loading ? (
          <SectionSkeleton />
        ) : (
          <Section title="Estimate vs Final Price" icon={Target}>
            {derived.avgEstimate > 0 ? (
              <div className="space-y-4">
                <BarChart
                  data={[
                    { label: 'Avg Estimate', value: derived.avgEstimate },
                    { label: 'Avg Final', value: derived.avgFinal },
                  ]}
                  height={180}
                  barColor="var(--accent)"
                  formatValue={(v) => formatCurrency(v)}
                />
                <div className="flex items-center justify-center gap-2">
                  <span className="text-xs text-[color:var(--muted-ink)]">Accuracy:</span>
                  <span className="text-sm font-bold text-[color:var(--ink)]">
                    {derived.accuracyPct}%
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-sm text-[color:var(--muted-ink)] text-center py-8">
                Record final prices on won estimates to see accuracy
              </p>
            )}
          </Section>
        )}

        {/* E. Win Rate by Job Type */}
        {loading ? (
          <SectionSkeleton />
        ) : (
          <Section title="Win Rate by Job Type" icon={ArrowUpDown}>
            {derived.jobTypeStats.length > 0 ? (
              <div className="space-y-3">
                {derived.jobTypeStats.map((jt) => (
                  <div key={jt.jobType} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-[color:var(--ink)] capitalize">
                        {jt.jobType.replace(/_/g, ' ')}
                      </span>
                      <span className="text-[color:var(--muted-ink)] tabular-nums">
                        {jt.winRate}% ({jt.won}/{jt.total})
                      </span>
                    </div>
                    <ProgressBar
                      value={jt.winRate}
                      size="sm"
                      variant={jt.winRate >= 60 ? 'success' : jt.winRate >= 40 ? 'warning' : 'danger'}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[color:var(--muted-ink)] text-center py-8">
                No job type data available
              </p>
            )}
          </Section>
        )}
      </div>

      {/* F. Recent Outcomes */}
      {loading ? (
        <SectionSkeleton />
      ) : (
        <Section title="Recent Outcomes" icon={FileText}>
          <DataTable
            columns={recentOutcomeColumns}
            data={sortedOutcomes}
            keyExtractor={(row) => row.id}
            sortKey={sortKey}
            sortDir={sortDir}
            onSort={handleSort}
            loading={loading}
            emptyMessage="No outcomes recorded yet"
          />
        </Section>
      )}
    </div>
  )
}
