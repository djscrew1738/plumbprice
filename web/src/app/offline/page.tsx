'use client'

import { CloudOff } from 'lucide-react'

export default function OfflinePage() {
  return (
    <div className="flex min-h-[60dvh] flex-col items-center justify-center gap-6 px-4 text-center">
      <div className="rounded-2xl bg-[hsl(var(--warning)/0.1)] p-5">
        <CloudOff size={48} className="text-[hsl(var(--warning))]" />
      </div>

      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-[color:var(--ink)]">
          You&apos;re offline
        </h1>
        <p className="text-sm text-[color:var(--muted-ink)] max-w-xs">
          Check your internet connection and try again.
        </p>
      </div>

      <button
        type="button"
        onClick={() => window.location.reload()}
        className="rounded-xl bg-[hsl(var(--primary))] px-6 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90"
      >
        Retry
      </button>
    </div>
  )
}
