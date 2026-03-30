'use client'

import { Layers } from 'lucide-react'
import { PageIntro } from '@/components/layout/PageIntro'

export default function Blueprints() {
  return (
    <div className="min-h-full">
      <div className="mx-auto w-full max-w-5xl px-4 py-5 sm:px-6 lg:px-8">
        <PageIntro
          eyebrow="Blueprints"
          title="Blueprint takeoffs are not available yet."
          description="This route is a planned entry point for PDF-based fixture detection and quantity extraction."
        />
        <section className="shell-panel-strong mt-4 p-12 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-blue-500/20 bg-blue-500/10">
            <Layers size={32} className="text-blue-700" />
          </div>
          <h2 className="mb-2 text-xl font-semibold text-[color:var(--ink)]">Placeholder destination</h2>
          <p className="mx-auto max-w-md text-[color:var(--muted-ink)]">
            No upload workflow is wired yet. When this feature is built, it will open a blueprint-first flow instead of mock content.
          </p>
        </section>
      </div>
    </div>
  )
}
