'use client'

import { FileUp, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Select, type SelectOption } from '@/components/ui/Select'

export type WorkspaceEntryMode = 'quick-quote' | 'upload-job-files'

/** DFW counties grouped by subregion for the searchable selector */
const COUNTY_OPTIONS: SelectOption[] = [
  { value: 'Dallas', label: 'Dallas County — Central DFW' },
  { value: 'Tarrant', label: 'Tarrant County — Fort Worth' },
  { value: 'Collin', label: 'Collin County — North DFW' },
  { value: 'Denton', label: 'Denton County — North DFW' },
  { value: 'Rockwall', label: 'Rockwall County — East DFW' },
  { value: 'Parker', label: 'Parker County — West DFW' },
]

interface WorkspaceEntryBarProps {
  county: string
  counties: string[]
  onCountyChange: (county: string) => void
  entryMode: WorkspaceEntryMode
  onEntryModeChange: (mode: WorkspaceEntryMode) => void
}

export function WorkspaceEntryBar({
  county,
  onCountyChange,
  entryMode,
  onEntryModeChange,
}: WorkspaceEntryBarProps) {
  return (
    <header className="px-3 pb-2 pt-3 sm:px-4 sm:pt-4">
      <div className="shell-panel flex flex-wrap items-center gap-2 p-2.5 sm:p-3">
        <div className="w-[220px]">
          <Select
            options={COUNTY_OPTIONS}
            value={county}
            onChange={onCountyChange}
            placeholder="Select county…"
            searchable
            size="sm"
          />
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
