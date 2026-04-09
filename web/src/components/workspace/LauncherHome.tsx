'use client'

import { useEffect, useState } from 'react'
import { FileUp, Sparkles, TrendingUp, Wrench, DollarSign, Clock } from 'lucide-react'
import { PrimaryActionCard } from './PrimaryActionCard'
import { RecentJobsList } from './RecentJobsList'
import { estimatesApi, type EstimateListItem } from '@/lib/api'
import { formatCurrency } from '@/lib/utils'

function computeWeeklyStats(jobs: EstimateListItem[]) {
  const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000
  const recent = jobs.filter(j => new Date(j.created_at).getTime() >= cutoff)
  const totalValue = recent.reduce((sum, j) => sum + (j.grand_total ?? 0), 0)
  const avgValue = recent.length > 0 ? totalValue / recent.length : 0
  return { count: recent.length, totalValue, avgValue }
}

function StatCard({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] px-4 py-3">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]">
        <Icon size={16} />
      </span>
      <div className="min-w-0">
        <p className="text-[11px] font-medium text-[color:var(--muted-ink)]">{label}</p>
        <p className="truncate text-sm font-semibold text-[color:var(--ink)]">{value}</p>
      </div>
    </div>
  )
}

export function LauncherHome() {
  const [stats, setStats] = useState<{ count: number; totalValue: number; avgValue: number } | null>(null)

  useEffect(() => {
    let active = true
    estimatesApi.list({ limit: 50 }).then(res => {
      if (active) setStats(computeWeeklyStats(res.data))
    }).catch(() => { /* non-critical */ })
    return () => { active = false }
  }, [])

  const now = new Date()
  const greeting = now.getHours() < 12 ? 'Good morning' : now.getHours() < 17 ? 'Good afternoon' : 'Good evening'

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-5 sm:px-6 lg:px-8">
      {/* Hero panel */}
      <section className="shell-panel p-5 sm:p-6">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">
          Field Pricing Launcher
        </p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-[color:var(--ink)] sm:text-3xl">
          {greeting}. Start pricing work.
        </h2>
        <p className="mt-2 max-w-2xl text-sm text-[color:var(--muted-ink)] sm:text-base">
          Run a quick quote from chat or attach documents when you need a fuller job package.
        </p>
      </section>

      {/* This-week stats */}
      <section className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3" aria-label="This week's activity">
        {stats === null ? (
          <>
            <div className="skeleton rounded-2xl h-[60px]" />
            <div className="skeleton rounded-2xl h-[60px]" />
            <div className="skeleton rounded-2xl h-[60px]" />
          </>
        ) : (
          <>
            <StatCard
              icon={Wrench}
              label="Estimates this week"
              value={stats.count === 0 ? 'None yet' : `${stats.count} estimate${stats.count === 1 ? '' : 's'}`}
            />
            <StatCard
              icon={DollarSign}
              label="Total quoted this week"
              value={stats.totalValue > 0 ? formatCurrency(stats.totalValue) : '—'}
            />
            <StatCard
              icon={TrendingUp}
              label="Average job value"
              value={stats.avgValue > 0 ? formatCurrency(stats.avgValue) : '—'}
            />
          </>
        )}
      </section>

      {/* Quick-action cards */}
      <section className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2" aria-label="Start a new estimate">
        <PrimaryActionCard
          href="/estimator?entry=quick-quote"
          title="Quick Quote"
          description="Jump into chat pricing with a clean workspace."
          icon={Sparkles}
        />
        <PrimaryActionCard
          href="/estimator?entry=upload-job-files"
          title="Upload Job Files"
          description="Open the estimator with a file-first workflow."
          icon={FileUp}
        />
      </section>

      {/* Recent jobs */}
      <section className="mt-5">
        <RecentJobsList heading="Recent jobs" />
      </section>

      {/* Footer hint */}
      <p className="mt-6 flex items-center gap-1.5 text-[11px] text-[color:var(--muted-ink)]">
        <Clock size={11} />
        Prices reflect current DFW market rates · Updated daily
      </p>
    </div>
  )
}

export function LauncherHomeSkeleton() {
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-5 sm:px-6 lg:px-8">
      <div className="shell-panel p-5 sm:p-6">
        <div className="mb-3 h-3 w-32 skeleton rounded" />
        <div className="mb-4 h-8 w-2/3 skeleton rounded" />
        <div className="h-4 w-3/4 skeleton rounded" />
      </div>

      <section className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="skeleton rounded-2xl h-[60px]" />
        ))}
      </section>

      <section className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="skeleton rounded-2xl p-4 h-[72px]" />
        <div className="skeleton rounded-2xl p-4 h-[72px]" />
      </section>

      <section className="mt-5">
        <div className="shell-panel space-y-3 p-4">
          <div className="h-5 w-24 skeleton rounded" />
          <div className="space-y-2">
            <div className="h-16 skeleton rounded-xl" />
            <div className="h-16 skeleton rounded-xl" />
            <div className="h-16 skeleton rounded-xl" />
          </div>
        </div>
      </section>
    </div>
  )
}

