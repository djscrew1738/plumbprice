'use client'

import { memo } from 'react'
import { motion, type Variants } from 'framer-motion'
import { useQueries } from '@tanstack/react-query'
import Link from 'next/link'
import { FileUp, Sparkles, TrendingUp, Wrench, DollarSign, Clock, MessageSquare, Target, BarChart3, Users, AlertTriangle, Send } from 'lucide-react'
import { PrimaryActionCard } from './PrimaryActionCard'
import { RecentJobsList } from './RecentJobsList'
import { Skeleton } from '@/components/ui/Skeleton'
import { BarChart } from '@/components/ui/BarChart'
import { estimatesApi, sessionsApi, outcomesApi, type EstimateListItem } from '@/lib/api'
import { formatCurrency, formatRelativeTime } from '@/lib/utils'

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
  const pendingSent = jobs.filter(j => j.status === 'sent').length
  const expired = jobs.filter(j => j.is_expired && j.status !== 'accepted' && j.status !== 'rejected').length
  return { count: recent.length, totalValue, avgValue, pendingSent, expired }
}

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function computeDailyActivity(jobs: EstimateListItem[]) {
  const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000
  const counts = new Array<number>(7).fill(0)
  for (const j of jobs) {
    const ts = new Date(j.created_at).getTime()
    if (ts >= cutoff) {
      const day = (new Date(j.created_at).getDay() + 6) % 7 // Mon=0
      counts[day]++
    }
  }
  return DAY_LABELS.map((label, i) => ({ label, value: counts[i] }))
}

const StatCard = memo(function StatCard({ icon: Icon, label, value, subText }: { icon: React.ElementType; label: string; value: string; subText?: string }) {
  return (
    <motion.div
      variants={fadeUp}
      className="flex items-center gap-2.5 rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] px-3 py-2.5 sm:gap-3 sm:px-4 sm:py-3"
    >
      <span className="flex size-8 shrink-0 items-center justify-center rounded-xl bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)] sm:size-9">
        <Icon size={15} />
      </span>
      <div className="min-w-0">
        <p className="truncate text-[10px] font-medium text-[color:var(--muted-ink)] sm:text-[11px]">{label}</p>
        <p className="truncate text-sm font-semibold text-[color:var(--ink)]">{value}</p>
        {subText && <p className="truncate text-[10px] text-gray-500 sm:text-xs">{subText}</p>}
      </div>
    </motion.div>
  )
})

export function LauncherHome() {
  const [estimatesQuery, sessionsQuery, outcomeStatsQuery] = useQueries({
    queries: [
      { queryKey: ['estimates'], queryFn: () => estimatesApi.list() },
      { queryKey: ['sessions'], queryFn: () => sessionsApi.list(5) },
      { queryKey: ['outcome-stats'], queryFn: () => outcomesApi.stats(), staleTime: 60_000 },
    ],
  })
  const estimatesData = estimatesQuery.data
  const sessionsData = sessionsQuery.data
  const outcomeStatsData = outcomeStatsQuery.data
  const EMPTY_STATS = { count: 0, totalValue: 0, avgValue: 0, pendingSent: 0, expired: 0 }
  const stats = estimatesData
    ? computeWeeklyStats(estimatesData.data)
    : estimatesQuery.isError
      ? EMPTY_STATS
      : null
  const dailyActivity = estimatesData ? computeDailyActivity(estimatesData.data) : null
  const sessions = sessionsData?.data ?? null
  const outcomeStats = outcomeStatsData?.data ?? null

  const isQueriesLoading = estimatesQuery.isLoading || sessionsQuery.isLoading
  const estimatesList = estimatesData?.data ?? []
  const sessionsList = sessionsData?.data ?? []
  const isEmpty = !isQueriesLoading && estimatesList.length === 0 && sessionsList.length === 0

  const now = new Date()
  const greeting = now.getHours() < 12 ? 'Good morning' : now.getHours() < 17 ? 'Good afternoon' : 'Good evening'

  const gettingStartedCards = [
    {
      icon: MessageSquare,
      title: 'Ask a pricing question',
      description: 'Jump into AI-powered chat pricing for any plumbing job.',
      href: '/estimator',
    },
    {
      icon: FileUp,
      title: 'Upload a blueprint',
      description: 'Upload PDF plans for automatic fixture detection and takeoff.',
      href: '/blueprints',
    },
    {
      icon: Users,
      title: 'Invite your team',
      description: 'Add teammates to collaborate on estimates and projects.',
      href: '/settings',
    },
  ]

  return (
    <div className="content-container py-4 pb-[calc(env(safe-area-inset-bottom)+0.5rem)] sm:py-5">
      {/* Hero panel */}
      <section className="shell-panel p-4 sm:p-6">
        <p className="text-[11px] font-bold text-[color:var(--accent-strong)]">
          Estimator Dashboard
        </p>
        <h2 className="mt-2 text-xl font-bold leading-tight tracking-tight text-[color:var(--ink)] sm:text-3xl">
          {greeting}. Ready to price a job?
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[color:var(--muted-ink)] sm:text-base">
          Start a quick quote via chat or upload job files for a comprehensive pricing package.
        </p>
      </section>

      {/* Getting Started — shown only when no estimates AND no sessions */}
      {isEmpty && (
        <motion.section
          className="mt-4"
          aria-label="Getting started"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <div className="shell-panel p-4">
            <h2 className="mb-3 border-b border-[color:var(--line)] pb-2 text-xs font-bold uppercase tracking-wider text-[color:var(--ink)]">
              Getting Started
            </h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              {gettingStartedCards.map(card => (
                <Link
                  key={card.href}
                  href={card.href}
                  className="group flex flex-col gap-3 rounded-xl border border-[color:var(--line)] bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:bg-[color:var(--panel)]"
                >
                  <span className="flex size-10 items-center justify-center rounded-xl bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]">
                    <card.icon size={18} />
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-[color:var(--ink)]">{card.title}</p>
                    <p className="mt-0.5 text-xs text-[color:var(--muted-ink)]">{card.description}</p>
                  </div>
                  <span className="mt-auto inline-flex items-center rounded-lg bg-[color:var(--accent-soft)] px-3 py-1.5 text-xs font-semibold text-[color:var(--accent-strong)] transition-colors group-hover:bg-[color:var(--accent-strong)] group-hover:text-white">
                    Get started →
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </motion.section>
      )}

      {/* This-week stats */}
      <section className="mt-4 grid grid-cols-2 gap-2.5 sm:gap-3 lg:grid-cols-3 xl:grid-cols-5" aria-label="This week's activity">
        {stats === null ? (
          <>
            <Skeleton variant="stat-card" />
            <Skeleton variant="stat-card" />
            <Skeleton variant="stat-card" />
            <Skeleton variant="stat-card" />
            <Skeleton variant="stat-card" />
          </>
        ) : (
          <motion.div
            className="col-span-full grid grid-cols-2 gap-2.5 sm:gap-3 lg:grid-cols-3 xl:grid-cols-5"
            variants={staggerContainer}
            initial="hidden"
            animate="show"
          >
            <StatCard
              icon={Wrench}
              label="Estimates this week"
              value={stats.count === 0 ? 'None yet' : `${stats.count} estimate${stats.count === 1 ? '' : 's'}`}
              subText="Last 7 days"
            />
            <StatCard
              icon={DollarSign}
              label="Total quoted this week"
              value={stats.totalValue > 0 ? formatCurrency(stats.totalValue) : '—'}
              subText="Last 7 days"
            />
            <StatCard
              icon={TrendingUp}
              label="Avg job value"
              value={stats.avgValue > 0 ? formatCurrency(stats.avgValue) : '—'}
              subText="This week"
            />
            <StatCard
              icon={Send}
              label="Awaiting reply"
              value={stats.pendingSent === 0 ? 'None' : `${stats.pendingSent} proposal${stats.pendingSent === 1 ? '' : 's'}`}
              subText="Proposals sent"
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
              subText="All time"
            />
          </motion.div>
        )}
      </section>

      {/* Expired estimates attention banner */}
      {stats !== null && stats.expired > 0 && (
        <motion.div
          className="mt-4 flex items-center gap-3 rounded-2xl border border-[hsl(var(--warning)/0.4)] bg-[hsl(var(--warning)/0.08)] px-4 py-3"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
        >
          <AlertTriangle size={15} className="shrink-0 text-[hsl(var(--warning))]" />
          <p className="text-sm text-[color:var(--ink)]">
            <span className="font-semibold">{stats.expired} estimate{stats.expired === 1 ? '' : 's'} expired</span>
            {' '}and still open — consider following up or refreshing the quote.
          </p>
          <Link href="/estimates?status=expired" className="ml-auto shrink-0 text-xs font-semibold text-[hsl(var(--warning))] hover:underline">
            View →
          </Link>
        </motion.div>
      )}

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

      {/* Weekly activity chart */}
      {dailyActivity && dailyActivity.some(d => d.value > 0) && (
        <motion.section
          className="mt-4"
          aria-label="Weekly activity"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.15 }}
        >
          <div className="shell-panel p-4">
            <div className="mb-3 flex items-center gap-2 border-b border-[color:var(--line)] pb-2">
              <BarChart3 size={14} className="text-[color:var(--accent-strong)]" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-[color:var(--ink)]">
                Estimates This Week
              </h2>
            </div>
            <BarChart data={dailyActivity} height={180} barColor="var(--accent-strong)" />
          </div>
        </motion.section>
      )}

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
                <Link
                  href="/estimator"
                  className="flex min-h-[44px] items-center justify-between rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] px-3 py-2 transition-colors hover:bg-[color:var(--panel-strong)]"
                >
                  <div className="min-w-0">
                    <p className="truncate text-xs font-medium text-[color:var(--ink)]">
                      {s.title ?? `Session #${s.id}`}
                    </p>
                    <p className="text-[11px] text-[color:var(--muted-ink)]">
                      {formatRelativeTime(s.updated_at)}
                      {s.county ? ` · ${s.county}` : ''}
                    </p>
                  </div>
                  <MessageSquare size={13} className="shrink-0 text-[color:var(--muted-ink)]" />
                </Link>
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

      <section className="mt-4 grid grid-cols-2 gap-2.5 sm:gap-3 lg:grid-cols-3 xl:grid-cols-5">
        <Skeleton variant="stat-card" count={5} />
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
