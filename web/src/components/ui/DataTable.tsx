'use client'

import { type ReactNode, useCallback } from 'react'
import { ChevronUp, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Skeleton } from './Skeleton'
import { VirtualList } from './VirtualList'

/* ── Types ───────────────────────────────────────── */

export interface Column<T> {
  key: string
  header: string
  render?: (row: T) => ReactNode
  sortable?: boolean
  width?: string
  align?: 'left' | 'center' | 'right'
  className?: string
}

export interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  keyExtractor: (row: T) => string | number
  sortKey?: string
  sortDir?: 'asc' | 'desc'
  onSort?: (key: string) => void
  loading?: boolean
  emptyMessage?: string
  onRowClick?: (row: T) => void
  rowClassName?: (row: T) => string
  className?: string
  stickyHeader?: boolean
  virtualized?: boolean
  virtualRowHeight?: number
  virtualContainerHeight?: number
}

/* ── Alignment helpers ───────────────────────────── */

const alignCell: Record<string, string> = {
  left: 'text-left',
  center: 'text-center',
  right: 'text-right',
}

/* ── Skeleton rows ───────────────────────────────── */

function SkeletonRows({ columns, count = 5 }: { columns: Column<unknown>[]; count?: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <tr key={i}>
          {columns.map((col) => (
            <td key={col.key} className="px-4 py-3">
              <Skeleton variant="text" className="h-4 w-3/4" />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}

function SkeletonCards({ columns, count = 5 }: { columns: Column<unknown>[]; count?: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-4 space-y-2"
        >
          {columns.map((col) => (
            <div key={col.key} className="flex items-center justify-between gap-2">
              <Skeleton variant="text" className="h-3 w-20" />
              <Skeleton variant="text" className="h-4 w-1/2" />
            </div>
          ))}
        </div>
      ))}
    </>
  )
}

/* ── Sort header ─────────────────────────────────── */

function SortIndicator({ active, dir }: { active: boolean; dir?: 'asc' | 'desc' }) {
  if (!active) {
    return (
      <span className="ml-1 inline-flex flex-col opacity-0 group-hover:opacity-40 transition-opacity" aria-hidden="true">
        <ChevronUp className="h-3 w-3 -mb-1" />
        <ChevronDown className="h-3 w-3" />
      </span>
    )
  }
  return (
    <span className="ml-1 inline-flex text-[color:var(--accent)]" aria-hidden="true">
      {dir === 'asc' ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
    </span>
  )
}

/* ── DataTable ───────────────────────────────────── */

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  sortKey,
  sortDir,
  onSort,
  loading = false,
  emptyMessage = 'No data to display',
  onRowClick,
  rowClassName,
  className,
  stickyHeader = false,
  virtualized = false,
  virtualRowHeight = 48,
  virtualContainerHeight = 600,
}: DataTableProps<T>) {
  const isEmpty = !loading && data.length === 0

  const getCellValue = (row: T, col: Column<T>) => {
    if (col.render) return col.render(row)
    return String((row as Record<string, unknown>)[col.key] ?? '')
  }

  const renderVirtualRow = useCallback((row: T) => (
    <tr
      key={keyExtractor(row)}
      className={cn(
        'border-t border-[color:var(--line)] hover:bg-[color:var(--panel-strong)] transition-colors flex',
        onRowClick && 'cursor-pointer',
        rowClassName?.(row),
      )}
      onClick={onRowClick ? () => onRowClick(row) : undefined}
    >
      {columns.map((col) => (
        <td
          key={col.key}
          className={cn(
            'px-4 py-3 text-sm text-[color:var(--ink)] flex-1',
            alignCell[col.align ?? 'left'],
            col.className,
          )}
          style={col.width ? { width: col.width, flex: 'none' } : undefined}
        >
          {getCellValue(row, col)}
        </td>
      ))}
    </tr>
  // eslint-disable-next-line react-hooks/exhaustive-deps
  ), [columns, keyExtractor, onRowClick, rowClassName])

  return (
    <div className={cn('w-full', className)}>
      {/* ── Desktop table ── */}
      <div className="hidden lg:block overflow-x-auto rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] shadow-[0_16px_32px_rgba(84,60,39,0.05)]">
        <table className={cn('w-full border-collapse', virtualized && 'table-fixed')}>
          <thead>
            <tr className={cn(
              'bg-[color:var(--panel-strong)]',
              stickyHeader && 'sticky top-0 z-10',
            )}>
              {columns.map((col) => {
                const isSortable = col.sortable && onSort
                const isActive = sortKey === col.key
                return (
                  <th
                    key={col.key}
                    scope="col"
                    className={cn(
                      'px-4 py-3 text-[10px] font-bold text-[color:var(--muted-ink)] uppercase tracking-widest select-none',
                      alignCell[col.align ?? 'left'],
                      isSortable && 'cursor-pointer group hover:text-[color:var(--ink)] transition-colors',
                      col.className,
                    )}
                    style={col.width ? { width: col.width } : undefined}
                    onClick={isSortable ? () => onSort(col.key) : undefined}
                    onKeyDown={isSortable ? (e: React.KeyboardEvent) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        onSort!(col.key)
                      }
                    } : undefined}
                    tabIndex={isSortable ? 0 : undefined}
                    role={isSortable ? 'columnheader' : undefined}
                    aria-sort={isActive ? (sortDir === 'asc' ? 'ascending' : 'descending') : undefined}
                  >
                    <span className="inline-flex items-center">
                      {col.header}
                      {isSortable && <SortIndicator active={isActive} dir={sortDir} />}
                    </span>
                  </th>
                )
              })}
            </tr>
          </thead>
          {!virtualized && (
          <tbody>
            {loading ? (
              <SkeletonRows columns={columns as Column<unknown>[]} />
            ) : isEmpty ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-12 text-center text-sm text-[color:var(--muted-ink)]"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              data.map((row) => (
                <tr
                  key={keyExtractor(row)}
                  className={cn(
                    'border-t border-[color:var(--line)] hover:bg-[color:var(--panel-strong)] transition-colors',
                    onRowClick && 'cursor-pointer',
                    rowClassName?.(row),
                  )}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={cn(
                        'px-4 py-3 text-sm text-[color:var(--ink)]',
                        alignCell[col.align ?? 'left'],
                        col.className,
                      )}
                    >
                      {getCellValue(row, col)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
          )}
        </table>
        {virtualized && !loading && !isEmpty && (
          <VirtualList
            items={data}
            itemHeight={virtualRowHeight}
            containerHeight={virtualContainerHeight}
            renderItem={renderVirtualRow}
          />
        )}
      </div>

      {/* ── Mobile card list ── */}
      <div className="lg:hidden space-y-3">
        {loading ? (
          <SkeletonCards columns={columns as Column<unknown>[]} />
        ) : isEmpty ? (
          <div className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] px-4 py-12 text-center text-sm text-[color:var(--muted-ink)]">
            {emptyMessage}
          </div>
        ) : (
          data.map((row) => (
            <div
              key={keyExtractor(row)}
              className={cn(
                'rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] shadow-[0_16px_32px_rgba(84,60,39,0.05)] p-4 space-y-2',
                onRowClick && 'cursor-pointer hover:bg-[color:var(--panel-strong)] transition-colors',
                rowClassName?.(row),
              )}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
            >
              {columns.map((col) => (
                <div key={col.key} className="flex items-start justify-between gap-2">
                  <span className="text-[10px] font-bold text-[color:var(--muted-ink)] uppercase tracking-widest shrink-0 pt-0.5">
                    {col.header}
                  </span>
                  <span className={cn(
                    'text-sm text-[color:var(--ink)] text-right',
                    col.className,
                  )}>
                    {getCellValue(row, col)}
                  </span>
                </div>
              ))}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
