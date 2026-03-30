'use client'

import { FileUp, Sparkles } from 'lucide-react'
import { PrimaryActionCard } from './PrimaryActionCard'
import { RecentJobsList } from './RecentJobsList'

export function LauncherHome() {
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-5 sm:px-6 lg:px-8">
      <section className="shell-panel p-5 sm:p-6">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">Field Pricing Launcher</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-[color:var(--ink)] sm:text-3xl">
          Start pricing work in two taps.
        </h2>
        <p className="mt-2 max-w-2xl text-sm text-[color:var(--muted-ink)] sm:text-base">
          Run a quick quote from chat or attach documents when you need a fuller job package.
        </p>
      </section>

      <section className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
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

      <section className="mt-5">
        <RecentJobsList heading="Recent jobs" />
      </section>
    </div>
  )
}
