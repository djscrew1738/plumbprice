'use client'

import { motion, type Variants } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { FileUp, Sparkles, TrendingUp, Wrench, DollarSign, Clock, MessageSquare, Target } from 'lucide-react'
import { PrimaryActionCard } from './PrimaryActionCard'
import { RecentJobsList } from './RecentJobsList'
import { Skeleton } from '@/components/ui/Skeleton'
import { estimatesApi, sessionsApi, outcomesApi, type EstimateListItem } from '@/lib/api'
import { formatCurrency } from '@/lib/utils'
import { formatDistanceToNow } from 'date-fns'

/* ── Animation helpers ───────────────────────────── */

const staggerContainer: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07 } },
}

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3, ease: 'easeOut' } },
}

/* ── Helpers ─────────────────────────────────────── */

function computeWeeklyStats(jobs: EstimateListItem[]) {
  const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000
  const recent = jobs.filter(j => new Date(j.created_at).getTime() >= cutoff)
  const totalValue = recent.reduce((sum, j) => sum + (j.grand_total ?? 0), 0)
  const avgValue = recent.length > 0 ? totalValue / recent.length : 0
  return { count: recent.length, totalValue, avgValue }
}

function StatCard({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <motion.div
      variants={fadeUp}
      className="flex items-center gap-3 rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] px-4 py-3"
    >
      <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]">
        <Icon size={16} />
      </span>
      <div className="min-w-0">
        <p className="text-[11px] font-medium text-[color:var(--muted-ink)]">{label}</p>
        <p className="truncate text-sm font-semibold text-[color:var(--ink)]">{value}</p>
      </div>
    </motion.div>
  )
}

export function LauncherHome() {
  const { data: estimatesData } = useQuery({
    queryKey: ['estimates'],
    queryFn: () => estimatesApi.list(),
  })
  const { data: sessionsData } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => sessionsApi.list(5),
  })
  const { data: outcomeStatsData } = useQuery({
    queryKey: ['outcome-stats'],
    queryFn: () => outcomesApi.stats(),
    staleTime: 60_000,
  })
  const stats = estimatesData ? computeWeeklyStats(estimatesData.data) : null
  const sessions = sessionsData?.data ?? null
  const outcomeStats = outcomeStatsData?.data ?? null

  const now = new Date()
  const greeting = now.getHours() < 12 ? 'Good morning' : now.getHours() < 17 ? 'Good afternoon' : 'Good evening'

  return (
    <div className="content-container py-5">
      {/* Hero panel */}
      <section className="shell-panel p-5 sm:p-6">
        <p className="text-[11px] font-bold text-[color:var(--accent-strong)]">
          Estimator Dashboard
        </p>
        <h2 className="mt-2 text-2xl font-bold tracking-tight text-[color:var(--ink)] sm:text-3xl">
          {greeting}. Ready to price a job?
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[color:var(--muted-ink)] sm:text-base">
          Start a quick quote via chat or upload job files for a comprehensive pricing package.
        </p>
      </section>

      {/* This-week stats */}
      <section className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="This week's activity">
        {stats === null ? (
          <>
            <Skeleton variant="stat-card" />
            <Skeleton variant="stat-card" />
            <Skeleton variant="stat-card" />
            <Skeleton variant="stat-card" />
          </>
        ) : (
          <motion.div
            className="col-span-full grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4"
            variants={staggerContainer}
            initial="hidden"
            animate="show"
          >
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
            <StatCard
              icon={Target}
              label="Win rate (all time)"
              value={
                outcomeStats === null
                  ? '—'
                  : outcomeStats.win_rate === null
                    ? `${outcomeStats.total} recorded`
                    : `${Math.round(outcomeStats.win_rate * 100)}% (${outcomeStats.won}/${outcomeStats.total})`
              }
            />
          </motion.div>
        )}
      </section>

      {/* Quick-action cards */}
      <motion.section
        className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2"
        aria-label="Start a new estimate"
        variants={staggerContainer}
        initial="hidden"
        animate="show"
      >
        <motion.div variants={fadeUp}>
          <PrimaryActionCard
            href="/estimator?entry=quick-quote"
            title="Quick Quote"
            description="Jump into chat pricing with a clean workspace."
            icon={Sparkles}
          />
        </motion.div>
        <motion.div variants={fadeUp}>
          <PrimaryActionCard
            href="/estimator?entry=upload-job-files"
            title="Upload Job Files"
            description="Open the estimator with a file-first workflow."
            icon={FileUp}
          />
        </motion.div>
      </motion.section>

      {/* Recent jobs */}
      <section className="mt-5">
        <RecentJobsList heading="Recent jobs" />
      </section>

      {/* Recent chat sessions */}
      {sessions && sessions.length > 0 && (
        <section className="mt-4 shell-panel p-4">
          <h2 className="mb-3 border-b border-[color:var(--line)] pb-2 text-xs font-bold uppercase tracking-wider text-[color:var(--ink)]">
            Recent Sessions
          </h2>
          <ul className="space-y-1.5">
            {sessions.map(s => (
              <li key={s.id}>
                <a
                  href="/estimator"
                  className="flex items-center justify-between rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] px-3 py-2 transition-colors hover:bg-[color:var(--panel-strong)]"
                >
                  <div className="min-w-0">
                    <p className="truncate text-xs font-medium text-[color:var(--ink)]">
                      {s.title ?? `Session #${s.id}`}
                    </p>
                    <p className="text-[11px] text-[color:var(--muted-ink)]">
                      {formatDistanceToNow(new Date(s.updated_at), { addSuffix: true })}
                      {s.county ? ` · ${s.county}` : ''}
                    </p>
                  </div>
                  <MessageSquare size={13} className="shrink-0 text-[color:var(--muted-ink)]" />
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}

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
    <div className="content-container py-5">
      <div className="shell-panel p-5 sm:p-6">
        <Skeleton variant="text" className="mb-3 h-3 w-32" />
        <Skeleton variant="text" className="mb-4 h-8 w-2/3" />
        <Skeleton variant="text" className="h-4 w-3/4" />
      </div>

      <section className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Skeleton variant="stat-card" count={3} />
      </section>

      <section className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Skeleton variant="card" className="h-[72px]" />
        <Skeleton variant="card" className="h-[72px]" />
      </section>

      <section className="mt-5">
        <div className="shell-panel space-y-3 p-4">
          <Skeleton variant="text" className="h-5 w-24" />
          <Skeleton variant="card" count={3} className="h-16 rounded-xl" />
        </div>
      </section>
    </div>
  )
}

