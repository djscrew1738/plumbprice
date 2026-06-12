'use client'

import { useState } from 'react'
import Link from 'next/link'
import { MessageSquare } from 'lucide-react'
import * as Tabs from '@radix-ui/react-tabs'
import { RecentJobsList } from '../RecentJobsList'
import { Skeleton } from '@/components/ui/Skeleton'
import { BlurFade, StaggerContainer, StaggerItem } from '@/components/ui/Motion'
import type { ChatSessionSummary } from '@/lib/api'
import { cn, formatRelativeTime } from '@/lib/utils'
import { useMinBreakpoint } from '@/lib/useBreakpoint'

export interface ActivityPanelProps {
  sessions: ChatSessionSummary[] | null
  isSessionsLoading: boolean
}

function SessionsList({ sessions, isLoading }: { sessions: ChatSessionSummary[] | null; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton variant="card" className="h-14 rounded-[var(--radius-md)]" />
        <Skeleton variant="card" className="h-14 rounded-[var(--radius-md)]" />
        <Skeleton variant="card" className="h-14 rounded-[var(--radius-md)]" />
      </div>
    )
  }

  if (!sessions || sessions.length === 0) {
    return (
      <p className="rounded-[var(--radius-md)] border border-dashed border-[color:var(--border-subtle)] px-4 py-6 text-center text-xs text-[color:var(--muted-ink)]">
        No chat sessions yet. Start a quick quote to see them here.
      </p>
    )
  }

  return (
    <StaggerContainer as="ul" stagger={0.04} className="space-y-1.5">
      {sessions.map((s) => (
        <StaggerItem key={s.id}>
          <li>
            <Link
              href="/estimator"
              className="flex min-h-[44px] items-center justify-between rounded-[var(--radius-md)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-1)] px-3 py-2 transition-colors hover:bg-[color:var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ring-focus)]"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-[color:var(--ink)]">
                  {s.title ?? `Session #${s.id}`}
                </p>
                <p className="text-[11px] text-[color:var(--muted-ink)]">
                  {formatRelativeTime(s.updated_at)}
                  {s.county ? ` · ${s.county}` : ''}
                </p>
              </div>
              <MessageSquare size={14} className="shrink-0 text-[color:var(--muted-ink)]" aria-hidden />
            </Link>
          </li>
        </StaggerItem>
      ))}
    </StaggerContainer>
  )
}

/**
 * Recent jobs and Recent chat sessions.
 * Side-by-side on `lg+`, tabbed on smaller viewports.
 */
export function ActivityPanel({ sessions, isSessionsLoading }: ActivityPanelProps) {
  const isWide = useMinBreakpoint('lg')
  const [tab, setTab] = useState<'jobs' | 'sessions'>('jobs')

  if (isWide) {
    return (
      <BlurFade delay={0.3} duration={0.4}>
        <section className="grid grid-cols-2 gap-4" aria-label="Recent activity">
          <div className="rounded-[var(--radius-xl)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-1)] p-4 shadow-[var(--shadow-sm)]">
            <h2 className="mb-3 text-sm font-semibold text-[color:var(--ink)]">Recent jobs</h2>
            <RecentJobsList compact heading="" />
          </div>
          <div className="rounded-[var(--radius-xl)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-1)] p-4 shadow-[var(--shadow-sm)]">
            <h2 className="mb-3 text-sm font-semibold text-[color:var(--ink)]">Recent sessions</h2>
            <SessionsList sessions={sessions} isLoading={isSessionsLoading} />
          </div>
        </section>
      </BlurFade>
    )
  }

  return (
    <BlurFade delay={0.3} duration={0.4}>
      <section
        className="rounded-[var(--radius-xl)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-1)] p-4 shadow-[var(--shadow-sm)]"
        aria-label="Recent activity"
      >
        <Tabs.Root value={tab} onValueChange={(v) => setTab(v as 'jobs' | 'sessions')}>
          <Tabs.List
            className="mb-3 inline-flex items-center gap-1 rounded-[var(--radius-md)] bg-[color:var(--surface-2)] p-1"
            aria-label="Activity tabs"
          >
            {[
              { value: 'jobs', label: 'Jobs' },
              { value: 'sessions', label: 'Sessions' },
            ].map((t) => (
              <Tabs.Trigger
                key={t.value}
                value={t.value}
                className={cn(
                  'rounded-[var(--radius-sm)] px-3 py-1.5 text-xs font-semibold text-[color:var(--muted-ink)] transition-colors',
                  'data-[state=active]:bg-[color:var(--surface-1)] data-[state=active]:text-[color:var(--ink)] data-[state=active]:shadow-[var(--shadow-sm)]',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ring-focus)]',
                )}
              >
                {t.label}
              </Tabs.Trigger>
            ))}
          </Tabs.List>
          {tab === 'jobs' && (
            <Tabs.Content value="jobs" className="focus-visible:outline-none">
              <RecentJobsList compact heading="" />
            </Tabs.Content>
          )}
          {tab === 'sessions' && (
            <Tabs.Content value="sessions" className="focus-visible:outline-none">
              <SessionsList sessions={sessions} isLoading={isSessionsLoading} />
            </Tabs.Content>
          )}
        </Tabs.Root>
      </section>
    </BlurFade>
  )
}
