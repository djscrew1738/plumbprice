'use client'

import { Search, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { prettyCategory } from '@/lib/formatters'

interface SupplierSearchAndFiltersProps {
  search: string
  onSearchChange: (value: string) => void
  categories: string[]
  activeCategory: string
  onCategoryChange: (value: string) => void
}

export function SupplierSearchAndFilters({
  search,
  onSearchChange,
  categories,
  activeCategory,
  onCategoryChange,
}: SupplierSearchAndFiltersProps) {
  return (
    <>
      <div className="relative">
        <Search size={14} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-[color:var(--muted-ink)]" />
        <input
          value={search}
          onChange={e => onSearchChange(e.target.value)}
          placeholder="Search items…"
          className="input w-full py-2.5 pl-9 pr-9"
        />
        {search && (
          <button onClick={() => onSearchChange('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-[color:var(--muted-ink)] transition-colors hover:text-[color:var(--ink)]" aria-label="Clear search">
            <X size={14} />
          </button>
        )}
      </div>

      {categories.length > 0 && (
        <div className="scrollbar-hide flex items-center gap-1.5 overflow-x-auto pb-0.5">
          <button
            onClick={() => onCategoryChange('all')}
            aria-label="Show all categories"
            aria-pressed={activeCategory === 'all'}
            className={cn(
              'shrink-0 rounded-full border px-2.5 py-1 text-[11px] font-semibold transition-all',
              activeCategory === 'all'
                ? 'border-[color:var(--accent)] bg-[color:var(--accent)] text-white'
                : 'border-[color:var(--line)] bg-[color:var(--panel)] text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]',
            )}
          >
            All
          </button>
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => onCategoryChange(cat)}
              aria-label={`Filter by ${prettyCategory(cat)}`}
              aria-pressed={activeCategory === cat}
              className={cn(
                'shrink-0 whitespace-nowrap rounded-full border px-2.5 py-1 text-[11px] font-semibold transition-all',
                activeCategory === cat
                  ? 'border-[color:var(--accent)] bg-[color:var(--accent)] text-white'
                  : 'border-[color:var(--line)] bg-[color:var(--panel)] text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]',
              )}
            >
              {prettyCategory(cat)}
            </button>
          ))}
        </div>
      )}
    </>
  )
}
