'use client'

import { useMemo, useCallback } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface PaginationProps {
  currentPage: number
  totalPages: number
  onPageChange: (page: number) => void
  pageSize?: number
  totalItems?: number
  className?: string
}

/* ------------------------------------------------------------------ */
/*  Page range builder (1 ... 4 5 6 ... 10 pattern)                    */
/* ------------------------------------------------------------------ */

type PageItem = number | 'ellipsis-start' | 'ellipsis-end'

function getPageRange(current: number, total: number): PageItem[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1)
  }

  const pages: PageItem[] = []

  // Always show first page
  pages.push(1)

  if (current <= 4) {
    // Near the start: 1 2 3 4 5 ... N
    for (let i = 2; i <= 5; i++) pages.push(i)
    pages.push('ellipsis-end')
  } else if (current >= total - 3) {
    // Near the end: 1 ... N-4 N-3 N-2 N-1 N
    pages.push('ellipsis-start')
    for (let i = total - 4; i < total; i++) pages.push(i)
  } else {
    // Middle: 1 ... C-1 C C+1 ... N
    pages.push('ellipsis-start')
    pages.push(current - 1)
    pages.push(current)
    pages.push(current + 1)
    pages.push('ellipsis-end')
  }

  // Always show last page
  pages.push(total)

  return pages
}

/* ------------------------------------------------------------------ */
/*  Button sub-component                                               */
/* ------------------------------------------------------------------ */

interface PageBtnProps {
  page: number
  active: boolean
  onClick: (page: number) => void
}

function PageBtn({ page, active, onClick }: PageBtnProps) {
  return (
    <button
      type="button"
      onClick={() => onClick(page)}
      aria-current={active ? 'page' : undefined}
      aria-label={`Page ${page}`}
      className={cn(
        'inline-flex items-center justify-center min-w-[36px] h-9 rounded-lg text-sm font-medium transition-colors outline-none',
        'focus-visible:ring-2 focus-visible:ring-[color:var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[hsl(var(--background))]',
        active
          ? 'bg-[color:var(--accent)] text-white'
          : 'text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)]',
      )}
    >
      {page}
    </button>
  )
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function Pagination({
  currentPage,
  totalPages,
  onPageChange,
  pageSize,
  totalItems,
  className,
}: PaginationProps) {
  const pages = useMemo(() => getPageRange(currentPage, totalPages), [currentPage, totalPages])

  const handlePrev = useCallback(() => {
    if (currentPage > 1) onPageChange(currentPage - 1)
  }, [currentPage, onPageChange])

  const handleNext = useCallback(() => {
    if (currentPage < totalPages) onPageChange(currentPage + 1)
  }, [currentPage, totalPages, onPageChange])

  if (totalPages <= 1) return null

  // "Showing X-Y of Z" calculation
  const showingText =
    totalItems != null && pageSize != null
      ? (() => {
          const start = (currentPage - 1) * pageSize + 1
          const end = Math.min(currentPage * pageSize, totalItems)
          return `Showing ${start}\u2013${end} of ${totalItems}`
        })()
      : null

  return (
    <nav aria-label="Pagination" className={cn('flex items-center justify-between gap-4', className)}>
      {/* Items summary */}
      {showingText && (
        <p className="text-sm text-[color:var(--muted-ink)] hidden sm:block">{showingText}</p>
      )}

      <div className="flex items-center gap-1 ml-auto">
        {/* Previous */}
        <button
          type="button"
          onClick={handlePrev}
          disabled={currentPage <= 1}
          aria-label="Previous page"
          className={cn(
            'inline-flex items-center justify-center min-w-[36px] h-9 rounded-lg text-sm transition-colors outline-none',
            'focus-visible:ring-2 focus-visible:ring-[color:var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[hsl(var(--background))]',
            'text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)]',
            'disabled:pointer-events-none disabled:opacity-40',
          )}
        >
          <ChevronLeft size={16} />
        </button>

        {/* Page buttons */}
        {pages.map((item, idx) =>
          typeof item === 'number' ? (
            <PageBtn
              key={item}
              page={item}
              active={item === currentPage}
              onClick={onPageChange}
            />
          ) : (
            <span
              key={item + '-' + idx}
              aria-hidden="true"
              className="inline-flex items-center justify-center min-w-[36px] h-9 text-sm text-[color:var(--muted-ink)] select-none"
            >
              &hellip;
            </span>
          ),
        )}

        {/* Next */}
        <button
          type="button"
          onClick={handleNext}
          disabled={currentPage >= totalPages}
          aria-label="Next page"
          className={cn(
            'inline-flex items-center justify-center min-w-[36px] h-9 rounded-lg text-sm transition-colors outline-none',
            'focus-visible:ring-2 focus-visible:ring-[color:var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[hsl(var(--background))]',
            'text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)]',
            'disabled:pointer-events-none disabled:opacity-40',
          )}
        >
          <ChevronRight size={16} />
        </button>
      </div>
    </nav>
  )
}
