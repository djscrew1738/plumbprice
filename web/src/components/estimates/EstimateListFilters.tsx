'use client'

import { useRef, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, RefreshCw, Download, ArrowUpDown, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { SearchInput } from '@/components/ui/SearchInput'
import { Tooltip } from '@/components/ui/Tooltip'

const FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'service', label: 'Service' },
  { value: 'construction', label: 'Construction' },
  { value: 'commercial', label: 'Commercial' },
]

const STATUS_FILTERS = [
  { value: 'all',      label: 'All statuses' },
  { value: 'draft',    label: 'Draft'        },
  { value: 'sent',     label: 'Sent'         },
  { value: 'accepted', label: 'Accepted'     },
  { value: 'rejected', label: 'Rejected'     },
  { value: 'expired',  label: 'Expired'      },
]

type SortKey = 'newest' | 'oldest' | 'highest' | 'lowest'

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: 'newest',  label: 'Newest first'  },
  { value: 'oldest',  label: 'Oldest first'  },
  { value: 'highest', label: 'Highest value' },
  { value: 'lowest',  label: 'Lowest value'  },
]

export type { SortKey }
export { SORT_OPTIONS }

interface EstimateListFiltersProps {
  filter: string
  onFilterChange: (value: string) => void
  statusFilter: string
  onStatusFilterChange: (value: string) => void
  expiredOnly: boolean
  onExpiredOnlyChange: (value: boolean) => void
  search: string
  onSearchChange: (value: string) => void
  sortBy: SortKey
  onSortChange: (value: SortKey) => void
  loading: boolean
  onExport: () => void
  onRefresh: () => void
  onNew: () => void
}

export function EstimateListFilters({
  filter,
  onFilterChange,
  statusFilter,
  onStatusFilterChange,
  expiredOnly,
  onExpiredOnlyChange,
  search,
  onSearchChange,
  sortBy,
  onSortChange,
  loading,
  onExport,
  onRefresh,
  onNew,
}: EstimateListFiltersProps) {
  return (
    <div className="sticky top-[calc(var(--header-height)+0.5rem)] z-10 mt-4 rounded-[1.25rem] border border-[color:var(--line)] bg-[color:var(--panel)]/80 px-4 py-2.5 backdrop-blur-xl">
      <div className="mx-auto max-w-5xl space-y-2.5">
        <div className="flex items-center justify-between gap-3">
          {/* Filter pills — job type */}
          <div className="scrollbar-hide flex items-center gap-1.5 overflow-x-auto">
            {FILTERS.map(f => (
              <button
                key={f.value}
                onClick={() => onFilterChange(f.value)}
                aria-pressed={filter === f.value}
                className={cn(
                  'whitespace-nowrap rounded-full px-3 py-1.5 text-xs font-semibold transition-all',
                  filter === f.value
                    ? 'bg-[color:var(--accent)] text-white'
                    : 'border border-[color:var(--line)] bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]',
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Tooltip content="Export visible estimates as CSV">
              <button
                onClick={onExport}
                className="flex items-center gap-1.5 rounded-xl px-2.5 py-2 text-[color:var(--muted-ink)] transition-colors hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]"
                aria-label="Export CSV"
              >
                <Download size={15} />
                <span className="hidden text-xs font-medium sm:inline">Export</span>
              </button>
            </Tooltip>
            <button
              onClick={onRefresh}
              className="rounded-xl p-2 text-[color:var(--muted-ink)] transition-colors hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]"
              aria-label="Refresh estimates"
            >
              <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
            </button>
            <Tooltip content="New estimate (N)">
              <button onClick={onNew} className="btn-primary px-3 py-2" aria-label="New estimate">
                <Plus size={15} /><span className="hidden sm:inline">New</span>
              </button>
            </Tooltip>
          </div>
        </div>

        {/* Search + sort row */}
        <div className="flex gap-2">
          <SearchInput
            value={search}
            onChange={onSearchChange}
            placeholder="Search by title, county, or status…"
            className="flex-1"
            aria-label="Search estimates"
          />
          <SortDropdown value={sortBy} onChange={onSortChange} />
        </div>

        {/* Status filter chips */}
        <div className="scrollbar-hide flex items-center gap-1.5 overflow-x-auto">
          {STATUS_FILTERS.map(s => {
            const isActive = s.value === 'expired' ? expiredOnly : (!expiredOnly && statusFilter === s.value)
            return (
              <button
                key={s.value}
                onClick={() => {
                  if (s.value === 'expired') {
                    onExpiredOnlyChange(true)
                    onStatusFilterChange('all')
                  } else {
                    onExpiredOnlyChange(false)
                    onStatusFilterChange(s.value)
                  }
                }}
                aria-pressed={isActive}
                className={cn(
                  'rounded-full border px-2.5 py-1 text-[11px] font-semibold whitespace-nowrap transition-all',
                  isActive
                    ? s.value === 'draft'    ? 'border-[color:var(--ink)] bg-[color:var(--ink)] text-[color:var(--background)]'
                      : s.value === 'sent'   ? 'border-[hsl(var(--info))] bg-[hsl(var(--info))] text-[hsl(var(--info-foreground))]'
                      : s.value === 'accepted' ? 'border-[hsl(var(--success))] bg-[hsl(var(--success))] text-[hsl(var(--success-foreground))]'
                      : s.value === 'rejected' ? 'border-[hsl(var(--danger))] bg-[hsl(var(--danger))] text-[hsl(var(--danger-foreground))]'
                      : s.value === 'expired' ? 'border-[hsl(var(--warning))] bg-[hsl(var(--warning))] text-[hsl(var(--warning-foreground))]'
                      : 'border-[color:var(--accent)] bg-[color:var(--accent)] text-white'
                    : 'border-[color:var(--line)] bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)] hover:text-[color:var(--ink)]',
                )}
              >
                {s.label}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}

interface SortDropdownProps {
  value: SortKey
  onChange: (value: SortKey) => void
}

const SortDropdown = ({ value, onChange }: SortDropdownProps) => {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const currentLabel = SORT_OPTIONS.find(o => o.value === value)?.label ?? 'Sort'

  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 whitespace-nowrap rounded-xl border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 py-2 text-xs font-medium text-[color:var(--muted-ink)] transition-all hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]"
      >
        <ArrowUpDown size={13} />
        <span className="hidden sm:inline">{currentLabel}</span>
        <ChevronDown size={11} className={cn('text-[color:var(--muted-ink)] transition-transform', open && 'rotate-180')} />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.96 }}
            transition={{ duration: 0.12 }}
            className="absolute right-0 top-full z-20 mt-1.5 min-w-[152px] overflow-hidden rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] shadow-2xl"
          >
            {SORT_OPTIONS.map(o => (
              <button
                key={o.value}
                onClick={() => { onChange(o.value); setOpen(false) }}
                className={cn(
                  'w-full px-3.5 py-2 text-left text-xs font-medium transition-colors',
                  o.value === value
                    ? 'bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]'
                    : 'text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]',
                )}
              >
                {o.label}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
