'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { History, GitCompare } from 'lucide-react'
import { estimatesApi } from '@/lib/api'
import { Badge } from '@/components/ui/Badge'
import { Tooltip } from '@/components/ui/Tooltip'
import { EmptyState } from '@/components/ui/EmptyState'
import { cn } from '@/lib/utils'

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface EstimateVersion {
  id: string
  version_number: number
  created_at: string
  change_summary?: string | null
  is_current?: boolean
}

export interface VersionTimelineProps {
  estimateId: number
  onSelectVersion: (versionId: string) => void
  onCompare: (v1: string, v2: string) => void
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function relativeTime(dateStr: string): string {
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diffMs = now - then
  const seconds = Math.floor(diffMs / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (days > 0) return `${days} day${days === 1 ? '' : 's'} ago`
  if (hours > 0) return `${hours} hour${hours === 1 ? '' : 's'} ago`
  if (minutes > 0) return `${minutes} min${minutes === 1 ? '' : 's'} ago`
  return 'just now'
}

function formatFullDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function VersionTimeline({
  estimateId,
  onSelectVersion,
  onCompare,
}: VersionTimelineProps) {
  const [compareSelection, setCompareSelection] = useState<string[]>([])

  const { data, isLoading, isError } = useQuery({
    queryKey: ['estimates', estimateId, 'versions'],
    queryFn: () => estimatesApi.getVersions(estimateId),
    select: (res) => (res.data ?? res) as EstimateVersion[],
  })

  const versions = data ?? []

  const toggleCompare = (versionId: string) => {
    setCompareSelection((prev) => {
      if (prev.includes(versionId)) return prev.filter((v) => v !== versionId)
      if (prev.length >= 2) return [prev[1], versionId]
      return [...prev, versionId]
    })
  }

  const handleCompare = () => {
    if (compareSelection.length === 2) {
      onCompare(compareSelection[0], compareSelection[1])
      setCompareSelection([])
    }
  }

  /* ---- Loading skeleton ---- */
  if (isLoading) {
    return (
      <div className="space-y-4 p-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex gap-3">
            <div className="skeleton h-3 w-3 rounded-full shrink-0 mt-1" />
            <div className="flex-1 space-y-2">
              <div className="skeleton h-4 w-24 rounded-lg" />
              <div className="skeleton h-3 w-40 rounded-lg" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  /* ---- Error ---- */
  if (isError) {
    return (
      <div className="p-4 text-sm text-[color:var(--muted-ink)]">
        Could not load version history.
      </div>
    )
  }

  /* ---- Empty ---- */
  if (versions.length === 0) {
    return (
      <EmptyState
        icon={<History size={22} />}
        title="No previous versions"
        description="Version history will appear here once changes are saved."
      />
    )
  }

  return (
    <div className="space-y-1">
      {/* Compare action bar */}
      {compareSelection.length === 2 && (
        <div className="flex items-center gap-2 px-4 py-2 mb-2 rounded-xl bg-[color:var(--accent-soft)] border border-[color:var(--accent)]/20">
          <GitCompare size={14} className="text-[color:var(--accent-strong)]" />
          <span className="text-xs text-[color:var(--accent-strong)] font-medium flex-1">
            2 versions selected
          </span>
          <button
            onClick={handleCompare}
            className="text-xs font-semibold px-3 py-1 rounded-lg bg-[color:var(--accent)] text-white hover:opacity-90 transition-opacity"
          >
            Compare
          </button>
          <button
            onClick={() => setCompareSelection([])}
            className="text-xs text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
          >
            Clear
          </button>
        </div>
      )}

      {/* Timeline */}
      <div className="relative pl-5">
        {/* Connecting line */}
        <div className="absolute left-[7px] top-3 bottom-3 border-l-2 border-[color:var(--line)]" />

        {versions.map((version, idx) => {
          const isCurrent = version.is_current || idx === 0
          const isSelected = compareSelection.includes(version.id)

          return (
            <div key={version.id} className="relative flex items-start gap-3 pb-4 last:pb-0">
              {/* Dot */}
              <div
                className={cn(
                  'relative z-10 mt-1 h-3 w-3 rounded-full shrink-0 ring-2',
                  isCurrent
                    ? 'bg-[color:var(--accent)] ring-[color:var(--accent)]/30'
                    : 'bg-[color:var(--panel-strong)] ring-[color:var(--line)]',
                )}
              />

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <button
                    onClick={() => onSelectVersion(version.id)}
                    className="text-sm font-semibold text-[color:var(--ink)] hover:text-[color:var(--accent-strong)] transition-colors"
                  >
                    v{version.version_number}
                  </button>
                  {isCurrent && (
                    <Badge variant="accent" size="sm">Current</Badge>
                  )}
                  <Tooltip content={formatFullDate(version.created_at)}>
                    <span className="text-[11px] text-[color:var(--muted-ink)]">
                      {relativeTime(version.created_at)}
                    </span>
                  </Tooltip>
                </div>

                {version.change_summary && (
                  <p className="mt-0.5 text-xs text-[color:var(--muted-ink)] line-clamp-2">
                    {version.change_summary}
                  </p>
                )}

                {/* Compare toggle */}
                <button
                  onClick={() => toggleCompare(version.id)}
                  className={cn(
                    'mt-1.5 text-[11px] font-medium px-2 py-0.5 rounded-md transition-colors',
                    isSelected
                      ? 'bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]'
                      : 'text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] hover:bg-white/[0.05]',
                  )}
                >
                  {isSelected ? '✓ Selected' : 'Select to compare'}
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
