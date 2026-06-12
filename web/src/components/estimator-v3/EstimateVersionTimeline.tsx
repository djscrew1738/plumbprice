'use client'

import { useState, useEffect, useCallback } from 'react'
import { GitBranch, RotateCcw, ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '@/lib/utils'
import { estimateVersionApiV3, type EstimateVersionItem, type EstimateVersionDiff } from '@/lib/api-v3'
import { haptic } from '@/lib/haptics'

interface Props {
  estimateId: number
}

export function EstimateVersionTimeline({ estimateId }: Props) {
  const [versions, setVersions] = useState<EstimateVersionItem[]>([])
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [selectedDiff, setSelectedDiff] = useState<EstimateVersionDiff | null>(null)
  const [diffLoading, setDiffLoading] = useState<number | null>(null)

  const loadVersions = useCallback(async () => {
    setLoading(true)
    try {
      const res = await estimateVersionApiV3.listVersions(estimateId)
      setVersions(res.data)
    } catch {
      setVersions([])
    } finally {
      setLoading(false)
    }
  }, [estimateId])

  useEffect(() => {
    if (expanded && versions.length === 0) {
      loadVersions()
    }
  }, [expanded, versions.length, loadVersions])

  const handleDiff = async (versionId: number) => {
    if (selectedDiff && selectedDiff.to_version === versionId) {
      setSelectedDiff(null)
      return
    }
    setDiffLoading(versionId)
    try {
      const res = await estimateVersionApiV3.diffVersion(estimateId, versionId)
      setSelectedDiff(res.data)
    } catch {
      setSelectedDiff(null)
    } finally {
      setDiffLoading(null)
    }
  }

  const handleBranch = async () => {
    haptic('tap')
    try {
      await estimateVersionApiV3.branch(estimateId, { notes: 'Branched from chat' })
      // Could show a toast here
    } catch { /* ignore */ }
  }

  return (
    <div className="border-t border-[color:var(--line)]">
      <button
        type="button"
        onClick={() => { haptic('tap'); setExpanded(v => !v) }}
        className="flex w-full items-center justify-between px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] transition-colors"
      >
        <span className="flex items-center gap-1.5">
          <RotateCcw size={12} />
          Version History
        </span>
        {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>

      {expanded && (
        <div className="px-4 pb-3">
          {loading && <p className="text-[11px] text-[color:var(--muted-ink)]">Loading versions…</p>}
          {!loading && versions.length === 0 && (
            <p className="text-[11px] text-[color:var(--muted-ink)]">No saved versions yet.</p>
          )}
          <div className="space-y-2">
            {versions.map((v) => (
              <div key={v.id}>
                <button
                  type="button"
                  onClick={() => handleDiff(v.id)}
                  className={cn(
                    'flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-[11px] transition-colors',
                    selectedDiff?.to_version === v.version_number
                      ? 'bg-[color:var(--accent-soft)]/30 text-[color:var(--accent-strong)]'
                      : 'text-[color:var(--ink)] hover:bg-[color:var(--panel-strong)]'
                  )}
                >
                  <span>v{v.version_number}</span>
                  <span className="text-[color:var(--muted-ink)]">
                    {new Date(v.created_at).toLocaleDateString()}
                  </span>
                </button>
                {diffLoading === v.id && (
                  <p className="px-2.5 py-1 text-[10px] text-[color:var(--muted-ink)]">Computing diff…</p>
                )}
                {selectedDiff?.to_version === v.version_number && (
                  <div className="mt-1 rounded-lg border border-[color:var(--line)] bg-[color:var(--panel-strong)] p-2">
                    <div className="mb-1 flex items-center justify-between text-[10px]">
                      <span className="text-[color:var(--muted-ink)]">
                        v{selectedDiff.from_version} → v{selectedDiff.to_version}
                      </span>
                      <span className={cn(
                        'font-semibold',
                        selectedDiff.total_delta >= 0 ? 'text-amber-600' : 'text-emerald-600'
                      )}>
                        {selectedDiff.total_delta >= 0 ? '+' : ''}${selectedDiff.total_delta.toFixed(2)}
                      </span>
                    </div>
                    {selectedDiff.added_line_items.length > 0 && (
                      <div className="text-[10px] text-emerald-600">
                        +{selectedDiff.added_line_items.length} items added
                      </div>
                    )}
                    {selectedDiff.removed_line_items.length > 0 && (
                      <div className="text-[10px] text-red-500">
                        −{selectedDiff.removed_line_items.length} items removed
                      </div>
                    )}
                    {selectedDiff.modified_line_items.length > 0 && (
                      <div className="text-[10px] text-violet-600">
                        ~{selectedDiff.modified_line_items.length} items changed
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={handleBranch}
            className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-lg border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 py-2 text-[11px] font-medium text-[color:var(--muted-ink)] hover:bg-[color:var(--accent-soft)] hover:text-[color:var(--accent-strong)] transition-colors"
          >
            <GitBranch size={12} />
            Branch this estimate
          </button>
        </div>
      )}
    </div>
  )
}
