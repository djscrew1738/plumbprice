'use client'

import Link from 'next/link'
import { ArrowRight, CheckCircle2, FileUp, MessageSquare, ShieldCheck } from 'lucide-react'
import { BrandFooter } from '@/components/layout/BrandFooter'
import { BlurFade, SlideUp, StaggerContainer, StaggerItem } from '@/components/ui/Motion'

const valueProps = [
  {
    icon: MessageSquare,
    title: 'Price jobs from chat',
    description: 'Turn field notes into line-item estimates without spreadsheet cleanup.',
  },
  {
    icon: FileUp,
    title: 'Upload plans and documents',
    description: 'Bring in blueprints, photos, and attachments to build faster estimates.',
  },
  {
    icon: ShieldCheck,
    title: 'Keep every price traceable',
    description: 'Tie each estimate back to supplier pricing, labor templates, and markup logic.',
  },
]

export function PublicHome() {
  return (
    <main className="min-h-dvh bg-[#060606] text-white">
      <div className="relative isolate overflow-hidden">
        <div
          className="pointer-events-none absolute left-1/2 top-24 h-[34rem] w-[34rem] -translate-x-1/2 rounded-full blur-[120px]"
          style={{ background: 'radial-gradient(circle, hsl(var(--accent-hsl) / 0.18) 0%, transparent 72%)' }}
        />

        <div className="mx-auto flex min-h-dvh max-w-6xl flex-col px-6 py-8 sm:px-8 lg:px-10">
          <BlurFade delay={0.05} duration={0.5}>
            <header className="flex items-center justify-between gap-4">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-[color:var(--accent)]">
                  PlumbPrice AI
                </p>
                <p className="mt-1 text-sm text-zinc-400">Field pricing for DFW plumbing teams</p>
              </div>
              <Link
                href="/login"
                className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-white transition-colors hover:border-white/20 hover:bg-white/10"
              >
                Sign in
                <ArrowRight size={15} aria-hidden />
              </Link>
            </header>
          </BlurFade>

          <div className="relative z-10 flex flex-1 items-center py-12 sm:py-16">
            <div className="grid w-full gap-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(20rem,0.9fr)] lg:items-center">
              <section className="max-w-2xl">
                <BlurFade delay={0.1} duration={0.5}>
                  <div className="inline-flex items-center gap-2 rounded-full border border-[color:var(--accent)]/25 bg-[color:var(--accent)]/10 px-3 py-1 text-xs font-semibold text-[color:var(--accent)]">
                    <CheckCircle2 size={14} aria-hidden />
                    Deterministic pricing with supplier-backed traceability
                  </div>
                </BlurFade>

                <SlideUp delay={0.15} duration={0.5}>
                  <h1 className="mt-6 text-balance text-4xl font-extrabold tracking-tight text-white sm:text-5xl">
                    Move from field notes to traceable plumbing estimates faster.
                  </h1>
                </SlideUp>

                <BlurFade delay={0.2} duration={0.5}>
                  <p className="mt-5 max-w-xl text-base leading-7 text-zinc-300 sm:text-lg">
                    Sign in to open your workspace, review recent jobs, and price new work from chat,
                    documents, or blueprints.
                  </p>
                </BlurFade>

                <BlurFade delay={0.25} duration={0.5}>
                  <div className="mt-8 flex flex-wrap gap-3">
                    <Link
                      href="/login"
                      className="inline-flex items-center gap-2 rounded-2xl bg-[color:var(--accent)] px-5 py-3 text-sm font-semibold text-white transition-transform hover:-translate-y-0.5"
                    >
                      Open workspace
                      <ArrowRight size={16} aria-hidden />
                    </Link>
                    <Link
                      href="/forgot-password"
                      className="inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition-colors hover:border-white/20 hover:bg-white/10"
                    >
                      Reset password
                    </Link>
                  </div>
                </BlurFade>
              </section>

              <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6 shadow-2xl shadow-black/30 backdrop-blur">
                <BlurFade delay={0.3} duration={0.5}>
                  <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-zinc-400">
                    What you get after sign-in
                  </h2>
                </BlurFade>
                <StaggerContainer
                  stagger={0.08}
                  initialDelay={0.35}
                  className="mt-6 space-y-4"
                >
                  {valueProps.map(({ icon: Icon, title, description }) => (
                    <StaggerItem key={title}>
                      <div className="rounded-2xl border border-white/8 bg-black/20 p-4 transition-colors hover:border-white/15 hover:bg-black/30">
                        <div className="flex items-start gap-3">
                          <span className="mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-2xl bg-[color:var(--accent)]/15 text-[color:var(--accent)]">
                            <Icon size={18} aria-hidden />
                          </span>
                          <div>
                            <h3 className="text-sm font-semibold text-white">{title}</h3>
                            <p className="mt-1 text-sm leading-6 text-zinc-300">{description}</p>
                          </div>
                        </div>
                      </div>
                    </StaggerItem>
                  ))}
                </StaggerContainer>
              </section>
            </div>
          </div>

          <BlurFade delay={0.55} duration={0.5}>
            <BrandFooter className="relative z-10 mt-8 pb-2" />
          </BlurFade>
        </div>
      </div>
    </main>
  )
}
