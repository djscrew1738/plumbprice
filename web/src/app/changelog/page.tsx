import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowLeft, CheckCircle2 } from 'lucide-react'
import { BUILT_BY_LINE } from '@/lib/branding'

export const metadata: Metadata = {
  title: 'Changelog – PlumbPrice AI',
  description: 'Major shipped improvements and release notes for PlumbPrice AI.',
}

interface ChangeEntry {
  category: 'Mobile / PWA' | 'Reliability' | 'AI / Pricing' | 'UX' | 'Platform' | 'Motion'
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
    version: '5.2.0',
    codename: 'Motion',
    date: '2026-06-07',
    highlights: [
      { category: 'Motion', text: 'Centralized animation primitives in Motion.tsx: FadeIn, BlurFade, SlideUp, ScaleIn, Reveal, Pressable, CountUp, StaggerContainer, StaggerItem, SlideIn, SmoothPresence, Pulse, HeightAuto, Shimmer.' },
      { category: 'Motion', text: 'Every primitive respects prefers-reduced-motion; no motion is essential for comprehension.' },
      { category: 'UX', text: 'Button spring whileTap feedback and loading cross-fade.' },
      { category: 'UX', text: 'Tabs animated active indicator via layoutId spring.' },
      { category: 'UX', text: 'Select dropdown enter/exit with AnimatePresence.' },
      { category: 'UX', text: 'Toast standardized slide/fade spring transitions.' },
      { category: 'UX', text: 'StatCard hover lift and CountUp value animation.' },
      { category: 'UX', text: 'Public home and launcher home choreographed entrance animations.' },
      { category: 'Platform', text: 'parseCurrencyValue() parses formatted currency strings back to numbers for CountUp animations.' },
      { category: 'Platform', text: 'No new animation dependencies; reuses existing Framer Motion ^12.37.0.' },
      { category: 'Platform', text: 'All routes remain within First Load JS budgets.' },
    ],
  },
  {
    version: '4.1.0',
    codename: 'AI Intelligence Overhaul + Mobile PWA',
    date: '2026-06-06',
    highlights: [
      { category: 'AI / Pricing', text: 'Ferguson OAuth2 client-credentials flow with Redis-cached tokens and legacy API key fallback.' },
      { category: 'AI / Pricing', text: 'Supplier price change alerts when delta exceeds ±10%.' },
      { category: 'AI / Pricing', text: 'Weekly price forecast model and price_trend labels on line items.' },
      { category: 'Reliability', text: 'Actual cost capture with Close Job API and variance analytics dashboard.' },
      { category: 'AI / Pricing', text: 'Pricing correction recommendations with admin approval workflow.' },
      { category: 'AI / Pricing', text: 'LLM fine-tuning pipeline with shadow A/B testing and ML Model Registry.' },
      { category: 'AI / Pricing', text: 'GPT-4V photo-to-estimate with multi-photo sessions and confidence review flags.' },
      { category: 'AI / Pricing', text: 'Advanced blueprint takeoff with scale calibration and structured pipe run routing.' },
      { category: 'Mobile / PWA', text: 'PWA manifest, service worker v4.1.0, and field tech mobile UI.' },
      { category: 'Mobile / PWA', text: 'Field routes: /field, /field/photo, /field/voice, /field/jobs.' },
      { category: 'Mobile / PWA', text: 'GPS county detection and Web Push notifications via VAPID.' },
      { category: 'Platform', text: 'ML worker on dedicated Celery queue, HNSW pgvector index, and Prometheus metrics.' },
    ],
  },
  {
    version: '3.0.0',
    codename: 'AI & Pricing Engine Overhaul',
    date: '2026-05-17',
    highlights: [
      { category: 'AI / Pricing', text: 'Structured LLM outputs via Pydantic parsing with transparent chain-of-thought reasoning.' },
      { category: 'AI / Pricing', text: 'Tool-calling agent v3 with parallel execution and clarification mode.' },
      { category: 'AI / Pricing', text: 'Dynamic market pricing engine with Redis caching and admin CRUD.' },
      { category: 'AI / Pricing', text: 'Blueprint Vision v3 with fixture/room/pipe run detection.' },
      { category: 'Platform', text: 'API v3 router suite: chat, estimates, blueprints, market-pricing, suppliers.' },
    ],
  },
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

      <footer className="mx-auto mt-16 max-w-3xl border-t border-slate-200 pt-6 text-center text-[11px] text-slate-500 dark:border-slate-800 dark:text-slate-600">
        {BUILT_BY_LINE}
      </footer>
    </div>
  )
}
