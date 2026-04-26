import Link from 'next/link'
import { ArrowLeft, CheckCircle2 } from 'lucide-react'

export const metadata = {
  title: 'Changelog — PlumbPrice',
}

interface ChangeEntry {
  category: 'Mobile / PWA' | 'Reliability' | 'AI / Pricing' | 'UX' | 'Platform'
  text: string
}

interface Release {
  version: string
  codename?: string
  date: string
  highlights: ChangeEntry[]
}

const RELEASES: Release[] = [
  {
    version: '2.1.1',
    codename: 'Field-First',
    date: '2026-04',
    highlights: [
      { category: 'Mobile / PWA', text: 'Installable PWA shell with offline fallback and update banner.' },
      { category: 'Mobile / PWA', text: 'On-site photo capture page with priced quick-quotes (≤30s round-trip).' },
      { category: 'Mobile / PWA', text: 'Haptic feedback primitives + pull-to-refresh hook.' },
      { category: 'Reliability', text: 'IP-based rate limits on auth + public proposal viewer.' },
      { category: 'Reliability', text: 'Mobile photo resizer endpoint (?w=) — thumbnails on demand.' },
      { category: 'Reliability', text: 'Coverage gate enforced in CI; alembic-aware test workflow.' },
      { category: 'AI / Pricing', text: 'Golden eval grew from 10 → 30 DFW cases; multi-county acceptance.' },
      { category: 'AI / Pricing', text: 'Cloud fallback when local Ollama tiers circuit-break.' },
      { category: 'UX', text: 'Cmd / Ctrl + K command palette wired up site-wide.' },
      { category: 'UX', text: 'Persistent dark mode toggle in the header.' },
      { category: 'Platform', text: 'TypeScript strict mode tightened; tsc --noEmit gates PRs.' },
      { category: 'Platform', text: '12 new auth/JWT integration tests; 9 new vitest tests.' },
    ],
  },
]

export default function ChangelogPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <Link
        href="/"
        className="mb-6 inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to home
      </Link>

      <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
        PlumbPrice Changelog
      </h1>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
        Major shipped improvements, newest first.
      </p>

      <div className="mt-10 space-y-12">
        {RELEASES.map((r) => (
          <section key={r.version}>
            <header className="flex items-baseline gap-3 border-b border-slate-200 pb-2 dark:border-slate-800">
              <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
                {r.version}
              </h2>
              {r.codename && (
                <span className="text-sm font-medium text-blue-600 dark:text-blue-400">
                  {r.codename}
                </span>
              )}
              <span className="ml-auto text-xs text-slate-500 dark:text-slate-500">{r.date}</span>
            </header>
            <ul className="mt-4 space-y-2">
              {r.highlights.map((h, i) => (
                <li key={i} className="flex items-start gap-3 text-sm">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-emerald-500" aria-hidden />
                  <div>
                    <span className="mr-2 inline-block min-w-[6.5rem] rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                      {h.category}
                    </span>
                    <span className="text-slate-700 dark:text-slate-300">{h.text}</span>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  )
}
