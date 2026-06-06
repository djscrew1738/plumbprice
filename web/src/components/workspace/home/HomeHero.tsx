'use client'

import Link from 'next/link'
import { ArrowRight, FileUp, Sparkles, History } from 'lucide-react'
import { PrimaryActionTile } from './PrimaryActionTile'
import type { ChatSessionSummary } from '@/lib/api'
import { formatRelativeTime } from '@/lib/utils'

export interface HomeHeroProps {
  greeting: string
  /** Most-recent open session, if any. When provided, surfaces a Resume tile. */
  resumeSession?: ChatSessionSummary | null
}

/**
 * Action-first hero. Two big primary tiles + an optional Resume tile.
 * No marketing copy — gets users straight into work.
 */
export function HomeHero({ greeting, resumeSession }: HomeHeroProps) {
  return (
    <section aria-label="Quick start">
      <div className="mb-4 sm:mb-5">
        <h1 className="text-2xl font-semibold tracking-tight text-[color:var(--ink)] sm:text-3xl">
          {greeting}
        </h1>
        <p className="mt-1 text-sm text-[color:var(--muted-ink)]">
          What would you like to price today?
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4">
        <PrimaryActionTile
          href="/estimator?entry=quick-quote"
          title="New estimate"
          description="Chat-driven pricing in a clean workspace."
          icon={Sparkles}
          tone="default"
        />
        <PrimaryActionTile
          href="/estimator?entry=upload-job-files"
          title="Upload blueprint"
          description="PDF takeoff with automatic fixture detection."
          icon={FileUp}
          tone="muted"
        />
      </div>

      {resumeSession && (
        <Link
          href="/estimator"
          className="group mt-3 flex items-center gap-3 rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] px-4 py-3 transition-colors hover:bg-[color:var(--surface-3)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ring-focus)]"
        >
          <span className="flex size-9 shrink-0 items-center justify-center rounded-[var(--radius-md)] bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]">
            <History size={16} aria-hidden />
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-[color:var(--ink)]">
              Resume — {resumeSession.title ?? `Session #${resumeSession.id}`}
            </p>
            <p className="truncate text-xs text-[color:var(--muted-ink)]">
              {formatRelativeTime(resumeSession.updated_at)}
              {resumeSession.county ? ` · ${resumeSession.county}` : ''}
            </p>
          </div>
          <ArrowRight
            size={16}
            className="text-[color:var(--muted-ink)] transition-transform group-hover:translate-x-0.5"
            aria-hidden
          />
        </Link>
      )}
    </section>
  )
}
