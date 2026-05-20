'use client'

import { useQueries } from '@tanstack/react-query'
import Link from 'next/link'
import { FileUp, MessageSquare, Users } from 'lucide-react'
import { Skeleton } from '@/components/ui/Skeleton'
import { PageShell, Stack } from '@/components/layout/shell'
import { HomeHero, KpiStrip, ActivityPanel, InsightsPanel, type KpiItem } from './home'
import { estimatesApi, sessionsApi, outcomesApi, type EstimateListItem } from '@/lib/api'
import { formatCurrency } from '@/lib/utils'
import { RECENT_CUTOFF_MS } from '@/lib/constants'

/* ── Helpers ─────────────────────────────────────── */

function computeWeeklyStats(jobs: EstimateListItem[]) {
  const cutoff = Date.now() - RECENT_CUTOFF_MS
  const recent = jobs.filter((j) => new Date(j.created_at).getTime() >= cutoff)
  const totalValue = recent.reduce((sum, j) => sum + (j.grand_total ?? 0), 0)
  const avgValue = recent.length > 0 ? totalValue / recent.length : 0
  const pendingSent = jobs.filter((j) => j.status === 'sent').length
  const expired = jobs.filter(
    (j) => j.is_expired && j.status !== 'accepted' && j.status !== 'rejected',
  ).length
  return { count: recent.length, totalValue, avgValue, pendingSent, expired }
}

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function computeDailyActivity(jobs: EstimateListItem[]) {
  const cutoff = Date.now() - RECENT_CUTOFF_MS
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

function getGreeting(date: Date) {
  const h = date.getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

/* ── Component ───────────────────────────────────── */

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

  const stats = estimatesData
    ? computeWeeklyStats(estimatesData.data)
    : estimatesQuery.isError
      ? { count: 0, totalValue: 0, avgValue: 0, pendingSent: 0, expired: 0 }
      : null
  const dailyActivity = estimatesData ? computeDailyActivity(estimatesData.data) : null
  const sessions = sessionsData?.data ?? null
  const outcomeStats = outcomeStatsData?.data ?? null

  const isQueriesLoading = estimatesQuery.isLoading || sessionsQuery.isLoading
  const estimatesList = estimatesData?.data ?? []
  const sessionsList = sessionsData?.data ?? []
  const isEmpty =
    !isQueriesLoading && estimatesList.length === 0 && sessionsList.length === 0

  const greeting = getGreeting(new Date())
  const resumeSession = sessionsList[0] ?? null

  const kpis: KpiItem[] | null = stats
    ? [
        { label: 'Estimates · 7d', value: stats.count.toString(), hint: 'Last 7 days' },
        {
          label: 'Quoted · 7d',
          value: stats.totalValue > 0 ? formatCurrency(stats.totalValue) : '—',
        },
        {
          label: 'Avg job value',
          value: stats.avgValue > 0 ? formatCurrency(stats.avgValue) : '—',
        },
        {
          label: 'Awaiting reply',
          value: stats.pendingSent.toString(),
          href: '/estimates?status=sent',
          tone: stats.pendingSent > 0 ? 'warning' : 'default',
        },
        {
          label: 'Win rate',
          value:
            outcomeStats === null
              ? '—'
              : outcomeStats.win_rate === null
                ? `${outcomeStats.total}`
                : `${Math.round(outcomeStats.win_rate * 100)}%`,
          hint:
            outcomeStats && outcomeStats.win_rate !== null
              ? `${outcomeStats.won}/${outcomeStats.total}`
              : 'All time',
          tone: 'success',
        },
      ]
    : null

  return (
    <PageShell>
      <Stack gap="lg">
        <HomeHero greeting={greeting} resumeSession={resumeSession} />

        {kpis === null ? (
          <Skeleton variant="card" className="h-[88px] rounded-[var(--radius-lg)]" />
        ) : (
          <KpiStrip items={kpis} />
        )}

        {isEmpty && <GettingStarted />}

        <ActivityPanel sessions={sessions} isSessionsLoading={sessionsQuery.isLoading} />

        {stats && (
          <InsightsPanel expiredCount={stats.expired} dailyActivity={dailyActivity} />
        )}
      </Stack>
    </PageShell>
  )
}

function GettingStarted() {
  const cards = [
    {
      icon: MessageSquare,
      title: 'Ask a pricing question',
      description: 'Jump into AI-powered chat for any plumbing job.',
      href: '/estimator',
    },
    {
      icon: FileUp,
      title: 'Upload a blueprint',
      description: 'PDF plans → automatic fixture detection and takeoff.',
      href: '/blueprints',
    },
    {
      icon: Users,
      title: 'Invite your team',
      description: 'Collaborate on estimates and projects together.',
      href: '/settings',
    },
  ]
  return (
    <section
      aria-label="Getting started"
      className="rounded-[var(--radius-xl)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-1)] p-4 shadow-[var(--shadow-sm)]"
    >
      <h2 className="mb-3 text-sm font-semibold text-[color:var(--ink)]">Getting started</h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {cards.map((card) => (
          <Link
            key={card.href}
            href={card.href}
            className="group flex flex-col gap-3 rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] p-4 transition-colors hover:bg-[color:var(--surface-3)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ring-focus)]"
          >
            <span className="flex size-9 items-center justify-center rounded-[var(--radius-md)] bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]">
              <card.icon size={16} aria-hidden />
            </span>
            <div>
              <p className="text-sm font-semibold text-[color:var(--ink)]">{card.title}</p>
              <p className="mt-0.5 text-xs text-[color:var(--muted-ink)]">{card.description}</p>
            </div>
          </Link>
        ))}
      </div>
    </section>
  )
}

export function LauncherHomeSkeleton() {
  return (
    <PageShell>
      <Stack gap="lg">
        <div>
          <Skeleton variant="text" className="mb-2 h-8 w-64" />
          <Skeleton variant="text" className="h-4 w-48" />
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4">
            <Skeleton variant="card" className="h-[120px] rounded-[var(--radius-xl)]" />
            <Skeleton variant="card" className="h-[120px] rounded-[var(--radius-xl)]" />
          </div>
        </div>
        <Skeleton variant="card" className="h-[88px] rounded-[var(--radius-lg)]" />
        <Skeleton variant="card" className="h-[200px] rounded-[var(--radius-xl)]" />
      </Stack>
    </PageShell>
  )
}
