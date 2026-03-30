'use client'

import { FileOutput } from 'lucide-react'
import { PageIntro } from '@/components/layout/PageIntro'

export default function Proposals() {
  return (
    <div className="min-h-full">
      <div className="mx-auto w-full max-w-5xl px-4 py-5 sm:px-6 lg:px-8">
        <PageIntro
          eyebrow="Proposals"
          title="Proposal generation is not live yet."
          description="This page is reserved for customer-ready proposal exports generated from saved estimates."
        />
        <section className="shell-panel-strong mt-4 p-12 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-emerald-500/20 bg-emerald-500/10">
            <FileOutput size={32} className="text-emerald-700" />
          </div>
          <h2 className="mb-2 text-xl font-semibold text-[color:var(--ink)]">Placeholder destination</h2>
          <p className="mx-auto max-w-md text-[color:var(--muted-ink)]">
            PDF proposal assembly is not implemented yet. Once shipped, this view will surface real proposal runs and export controls.
          </p>
        </section>
      </div>
    </div>
  )
}
