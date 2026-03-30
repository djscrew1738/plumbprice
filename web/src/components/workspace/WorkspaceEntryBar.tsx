'use client'

import { useEffect, useRef, useState } from 'react'
import { ChevronDown, FileUp, MapPin, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'

export type WorkspaceEntryMode = 'quick-quote' | 'upload-job-files'

interface WorkspaceEntryBarProps {
  county: string
  counties: string[]
  onCountyChange: (county: string) => void
  entryMode: WorkspaceEntryMode
  onEntryModeChange: (mode: WorkspaceEntryMode) => void
}

export function WorkspaceEntryBar({
  county,
  counties,
  onCountyChange,
  entryMode,
  onEntryModeChange,
}: WorkspaceEntryBarProps) {
  const [countyOpen, setCountyOpen] = useState(false)
  const countyRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const closeOnOutsideClick = (event: MouseEvent) => {
      if (countyRef.current && !countyRef.current.contains(event.target as Node)) {
        setCountyOpen(false)
      }
    }

    document.addEventListener('mousedown', closeOnOutsideClick)
    return () => {
      document.removeEventListener('mousedown', closeOnOutsideClick)
    }
  }, [])

  return (
    <header className="px-3 pb-2 pt-3 sm:px-4 sm:pt-4">
      <div className="shell-panel flex flex-wrap items-center gap-2 p-2.5 sm:p-3">
        <div ref={countyRef} className="relative">
          <button
            type="button"
            onClick={() => setCountyOpen(open => !open)}
            className="btn-secondary min-h-0 gap-1.5 rounded-full px-3 py-1.5 text-xs"
            aria-expanded={countyOpen}
            aria-label={`County ${county}`}
          >
            <MapPin size={13} className="text-[color:var(--accent-strong)]" />
            <span>{county} County</span>
            <ChevronDown
              size={12}
              className={cn('transition-transform', countyOpen && 'rotate-180')}
            />
          </button>

          {countyOpen && (
            <div className="absolute left-0 top-full z-30 mt-1.5 min-w-[172px] overflow-hidden rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] shadow-[0_16px_32px_rgba(84,60,39,0.12)]">
              {counties.map(candidate => (
                <button
                  key={candidate}
                  type="button"
                  onClick={() => {
                    onCountyChange(candidate)
                    setCountyOpen(false)
                  }}
                  className={cn(
                    'block w-full px-3.5 py-2 text-left text-xs font-medium transition-colors',
                    candidate === county
                      ? 'bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]'
                      : 'text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]'
                  )}
                >
                  {candidate} County
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="ml-auto flex rounded-full border border-[color:var(--line)] bg-[color:var(--panel-strong)] p-1">
          <button
            type="button"
            onClick={() => onEntryModeChange('quick-quote')}
            className={cn(
              'inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors',
              entryMode === 'quick-quote'
                ? 'bg-[color:var(--panel)] text-[color:var(--ink)] shadow-[0_6px_14px_rgba(84,60,39,0.12)]'
                : 'text-[color:var(--muted-ink)] hover:text-[color:var(--ink)]'
            )}
            aria-pressed={entryMode === 'quick-quote'}
          >
            <Sparkles size={13} />
            Quick Quote
          </button>
          <button
            type="button"
            onClick={() => onEntryModeChange('upload-job-files')}
            className={cn(
              'inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors',
              entryMode === 'upload-job-files'
                ? 'bg-[color:var(--panel)] text-[color:var(--ink)] shadow-[0_6px_14px_rgba(84,60,39,0.12)]'
                : 'text-[color:var(--muted-ink)] hover:text-[color:var(--ink)]'
            )}
            aria-pressed={entryMode === 'upload-job-files'}
          >
            <FileUp size={13} />
            Upload Job Files
          </button>
        </div>
      </div>
    </header>
  )
}
