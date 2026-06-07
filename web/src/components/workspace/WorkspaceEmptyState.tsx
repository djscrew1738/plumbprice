'use client'

import { memo } from 'react'
import { Sparkles, ArrowRight } from 'lucide-react'
import type { WorkspaceMode } from './WorkspaceModeSwitcher'

interface WorkspaceEmptyStateProps {
  mode: WorkspaceMode
  suggestions: { short: string; full: string; hint?: string }[]
  onSuggestionClick: (text: string) => void
}

const MODE_COPY: Record<WorkspaceMode, { headline: string; subheadline: string }> = {
  repair: {
    headline: 'What repair do you need to price?',
    subheadline: 'Describe the job and get an instant estimate with line-item breakdown.',
  },
  blueprint: {
    headline: 'Upload plans for takeoff pricing',
    subheadline: 'Attach blueprints or photos and the AI will detect fixtures, pipe runs, and scope.',
  },
  floorplan: {
    headline: 'Describe the floorplan and fixtures',
    subheadline: 'Guide the AI through room counts, fixture types, and finish levels for rough-in and finish pricing.',
  },
}

export const WorkspaceEmptyState = memo(function WorkspaceEmptyState({
  mode,
  suggestions,
  onSuggestionClick,
}: WorkspaceEmptyStateProps) {
  const copy = MODE_COPY[mode]

  return (
    <div className="flex flex-col items-center justify-center gap-6 px-4 py-10 text-center">
      {/* Illustration */}
      <div className="relative">
        <div className="flex size-20 items-center justify-center rounded-[1.75rem] bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]">
          <Sparkles size={32} aria-hidden="true" />
        </div>
        <div className="absolute -right-1 -top-1 flex size-6 items-center justify-center rounded-full bg-[color:var(--accent)] text-white">
          <span className="text-xs font-bold">AI</span>
        </div>
      </div>

      {/* Text */}
      <div className="max-w-sm">
        <h2 className="text-display-md font-display text-[color:var(--ink)]">
          {copy.headline}
        </h2>
        <p className="mt-2 text-body text-[color:var(--muted-ink)]">
          {copy.subheadline}
        </p>
      </div>

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="flex w-full max-w-md flex-col gap-2">
          <p className="text-eyebrow uppercase text-[color:var(--muted-ink)]">Try asking</p>
          {suggestions.slice(0, 4).map((s) => (
            <button
              key={s.short}
              onClick={() => onSuggestionClick(s.full)}
              className="group flex items-center justify-between rounded-[1.25rem] border border-[color:var(--line)] bg-[color:var(--panel-solid)] px-4 py-3 text-left transition-all hover:bg-[color:var(--panel-strong)] hover:border-[color:var(--line-strong)] active:scale-[0.99]"
            >
              <span>
                <span className="block text-sm font-medium text-[color:var(--ink)]">{s.short}</span>
                {s.hint && (
                  <span className="mt-0.5 block text-xs text-[color:var(--muted-ink)]">{s.hint}</span>
                )}
              </span>
              <ArrowRight
                size={16}
                className="shrink-0 text-[color:var(--muted-ink)] opacity-0 transition-all group-hover:opacity-100 group-hover:translate-x-0.5"
                aria-hidden="true"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  )
})
