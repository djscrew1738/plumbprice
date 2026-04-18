'use client'

import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRevenue, usePipelineAnalytics, useRepPerformance } from '@/lib/hooks'
import { Select } from '@/components/ui/Select'

const PERIOD_OPTIONS = [
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' },
  { value: '365d', label: 'Last 365 days' },
  { value: 'all', label: 'All time' },
]

function fmt(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

function fmtPct(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

// ─── Revenue Section ─────────────────────────────────────────────────────────

function RevenueSection() {
  const [period, setPeriod] = useState('all')
  const { data, isLoading, error } = useRevenue(period)

  const maxRevenue = data?.monthly_breakdown.reduce((m, r) => Math.max(m, r.revenue), 1) ?? 1

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-[color:var(--ink)]">Revenue</h2>
        <div className="w-44">
          <Select options={PERIOD_OPTIONS} value={period} onChange={setPeriod} size="sm" />
        </div>
      </div>

      {isLoading && (
        <div className="animate-pulse space-y-3">
          <div className="h-24 rounded-xl bg-[color:var(--panel-strong)]" />
          <div className="h-40 rounded-xl bg-[color:var(--panel-strong)]" />
        </div>
      )}

      {error && !isLoading && (
        <p className="text-sm text-red-500">Failed to load revenue data.</p>
      )}

      {data && !isLoading && (
        <>
          {/* KPI card */}
          <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] p-4">
            <p className="text-xs text-[color:var(--muted-ink)]">Total Revenue</p>
            <p className="mt-1 text-3xl font-bold text-[color:var(--ink)]">
              {fmt(data.total_revenue)}
            </p>
          </div>

          {/* Monthly breakdown */}
          {data.monthly_breakdown.length > 0 && (
            <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] p-4">
              <p className="mb-3 text-xs font-medium text-[color:var(--muted-ink)] uppercase tracking-wide">
                Monthly Trend
              </p>
              <div className="space-y-2">
                {data.monthly_breakdown.map((row) => (
                  <div key={row.month} className="flex items-center gap-3">
                    <span className="w-20 shrink-0 text-xs text-[color:var(--muted-ink)]">
                      {row.month}
                    </span>
                    <div className="flex-1 rounded-full bg-[color:var(--panel-strong)] h-4 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-[color:var(--accent)]"
                        style={{ width: `${Math.round((row.revenue / maxRevenue) * 100)}%` }}
                      />
                    </div>
                    <span className="w-24 shrink-0 text-right text-xs text-[color:var(--ink)]">
                      {fmt(row.revenue)}
                    </span>
                    <span className="w-16 shrink-0 text-right text-xs text-[color:var(--muted-ink)]">
                      {row.estimate_count} est.
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* By job type */}
          {data.by_job_type.length > 0 && (
            <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] p-4">
              <p className="mb-3 text-xs font-medium text-[color:var(--muted-ink)] uppercase tracking-wide">
                By Job Type
              </p>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-[color:var(--muted-ink)]">
                    <th className="pb-2 font-medium">Job Type</th>
                    <th className="pb-2 font-medium text-right">Revenue</th>
                    <th className="pb-2 font-medium text-right">Count</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[color:var(--line)]">
                  {data.by_job_type.map((row) => (
                    <tr key={row.job_type}>
                      <td className="py-2 capitalize">{row.job_type}</td>
                      <td className="py-2 text-right font-medium">{fmt(row.revenue)}</td>
                      <td className="py-2 text-right text-[color:var(--muted-ink)]">{row.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  )
}

// ─── Pipeline Section ─────────────────────────────────────────────────────────

function PipelineSection() {
  const { data, isLoading, error } = usePipelineAnalytics()

  return (
    <section className="space-y-4">
      <h2 className="text-base font-semibold text-[color:var(--ink)]">Pipeline</h2>

      {isLoading && (
        <div className="animate-pulse space-y-3">
          <div className="h-24 rounded-xl bg-[color:var(--panel-strong)]" />
          <div className="h-32 rounded-xl bg-[color:var(--panel-strong)]" />
        </div>
      )}

      {error && !isLoading && (
        <p className="text-sm text-red-500">Failed to load pipeline data.</p>
      )}

      {data && !isLoading && (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] p-4">
              <p className="text-xs text-[color:var(--muted-ink)]">Active Pipeline Value</p>
              <p className="mt-1 text-2xl font-bold text-[color:var(--ink)]">
                {fmt(data.active_pipeline_value)}
              </p>
            </div>
            <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] p-4">
              <p className="text-xs text-[color:var(--muted-ink)]">Conversion Rate</p>
              <p className="mt-1 text-2xl font-bold text-[color:var(--ink)]">
                {fmtPct(data.conversion_rate)}
              </p>
            </div>
          </div>

          {/* Stage funnel */}
          {data.stages.length > 0 && (
            <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] p-4">
              <p className="mb-3 text-xs font-medium text-[color:var(--muted-ink)] uppercase tracking-wide">
                Stage Funnel
              </p>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {data.stages.map((stage) => (
                  <div
                    key={stage.name}
                    className="rounded-lg border border-[color:var(--line)] bg-[color:var(--panel-strong)] p-3"
                  >
                    <p className="text-xs font-medium capitalize text-[color:var(--muted-ink)]">
                      {stage.name}
                    </p>
                    <p className="mt-0.5 text-xl font-bold text-[color:var(--ink)]">
                      {stage.count}
                    </p>
                    <p className="text-xs text-[color:var(--muted-ink)]">
                      avg {stage.avg_days.toFixed(1)} days
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </section>
  )
}

// ─── Rep Performance Section ──────────────────────────────────────────────────

function RepPerformanceSection() {
  const [period, setPeriod] = useState('all')
  const { data, isLoading, error } = useRepPerformance(period)

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-[color:var(--ink)]">Rep Performance</h2>
        <div className="w-44">
          <Select options={PERIOD_OPTIONS} value={period} onChange={setPeriod} size="sm" />
        </div>
      </div>

      {isLoading && (
        <div className="animate-pulse h-40 rounded-xl bg-[color:var(--panel-strong)]" />
      )}

      {error && !isLoading && (
        <p className="text-sm text-red-500">Failed to load rep performance data.</p>
      )}

      {data && !isLoading && (
        <div className="overflow-x-auto rounded-xl border border-[color:var(--line)]">
          <table className="w-full text-sm">
            <thead className="bg-[color:var(--panel)] text-left text-xs text-[color:var(--muted-ink)]">
              <tr>
                <th className="px-4 py-3 font-medium">Rep Name</th>
                <th className="px-4 py-3 font-medium text-right">Quotes</th>
                <th className="px-4 py-3 font-medium text-right">Won</th>
                <th className="px-4 py-3 font-medium text-right">Win Rate</th>
                <th className="px-4 py-3 font-medium text-right">Revenue Won</th>
                <th className="px-4 py-3 font-medium text-right">Avg Deal</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[color:var(--line)]">
              {data.reps.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-[color:var(--muted-ink)]">
                    No rep performance data available.
                  </td>
                </tr>
              ) : (
                data.reps.map((rep) => {
                  const winRate = rep.quotes_created > 0
                    ? (rep.won_count / rep.quotes_created) * 100
                    : 0
                  return (
                    <tr key={rep.user_id} className="hover:bg-[color:var(--panel-hover)]">
                      <td className="px-4 py-3 font-medium text-[color:var(--ink)]">
                        {rep.full_name}
                      </td>
                      <td className="px-4 py-3 text-right">{rep.quotes_created}</td>
                      <td className="px-4 py-3 text-right">{rep.won_count}</td>
                      <td className="px-4 py-3 text-right">{winRate.toFixed(1)}%</td>
                      <td className="px-4 py-3 text-right font-medium">{fmt(rep.won_amount)}</td>
                      <td className="px-4 py-3 text-right text-[color:var(--muted-ink)]">
                        {fmt(rep.avg_deal_size)}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

// ─── AnalyticsTab ─────────────────────────────────────────────────────────────

export function AnalyticsTab() {
  const { user } = useAuth()
  const isAdmin = user?.is_admin ?? false

  return (
    <div className="space-y-8 py-2">
      <RevenueSection />
      <PipelineSection />
      {isAdmin && <RepPerformanceSection />}
    </div>
  )
}
