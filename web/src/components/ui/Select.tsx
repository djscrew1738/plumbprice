'use client'

import {
  useState,
  useRef,
  useEffect,
  useCallback,
  useId,
  type ReactNode,
} from 'react'
import { ChevronDown, X, Search } from 'lucide-react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

/* ── Trigger variants ──────────────────────────────── */

const triggerVariants = cva(
  'flex w-full items-center justify-between gap-2 rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] text-[color:var(--ink)] transition-all focus:border-[color:var(--accent)] focus:outline-none focus:ring-2 focus:ring-[color:var(--accent)] disabled:cursor-not-allowed disabled:opacity-50',
  {
    variants: {
      size: {
        sm: 'min-h-[32px] text-xs px-2.5 py-1.5',
        md: 'min-h-[40px] text-sm px-3.5 py-2.5',
        lg: 'min-h-[48px] text-base px-4 py-3',
      },
    },
    defaultVariants: { size: 'md' },
  }
)

/* ── Types ─────────────────────────────────────────── */

export interface SelectOption {
  value: string
  label: string
  icon?: ReactNode
}

export interface SelectProps extends VariantProps<typeof triggerVariants> {
  label?: string
  error?: string
  helperText?: string
  options: SelectOption[]
  value?: string
  onChange?: (value: string) => void
  placeholder?: string
  searchable?: boolean
  clearable?: boolean
  disabled?: boolean
  className?: string
  id?: string
}

/* ── Component ─────────────────────────────────────── */

export function Select({
  label,
  error,
  helperText,
  options,
  value,
  onChange,
  placeholder = 'Select…',
  searchable = false,
  clearable = false,
  size = 'md',
  disabled = false,
  className,
  id: idProp,
}: SelectProps) {
  const autoId = useId()
  const id = idProp ?? autoId
  const listboxId = `${id}-listbox`

  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [highlightIdx, setHighlightIdx] = useState(-1)

  const wrapperRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLUListElement>(null)

  const selected = options.find((o) => o.value === value)

  const filtered = search
    ? options.filter((o) =>
        o.label.toLowerCase().includes(search.toLowerCase())
      )
    : options

  // Close on outside click
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  // Focus search input when opened
  useEffect(() => {
    if (open && searchable) {
      requestAnimationFrame(() => searchRef.current?.focus())
    }
    if (open) {
      // Pre-highlight the currently selected option
      const idx = filtered.findIndex((o) => o.value === value)
      setHighlightIdx(idx >= 0 ? idx : 0)
    }
    if (!open) setSearch('')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  // Scroll highlighted option into view
  useEffect(() => {
    if (!open || highlightIdx < 0) return
    const list = listRef.current
    const item = list?.children[searchable ? highlightIdx + 1 : highlightIdx] as HTMLElement | undefined
    item?.scrollIntoView({ block: 'nearest' })
  }, [highlightIdx, open, searchable])

  const pick = useCallback(
    (val: string) => {
      onChange?.(val)
      setOpen(false)
    },
    [onChange]
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!open) {
        if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(e.key)) {
          e.preventDefault()
          setOpen(true)
        }
        return
      }

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setHighlightIdx((i) => (i + 1) % filtered.length)
          break
        case 'ArrowUp':
          e.preventDefault()
          setHighlightIdx((i) => (i - 1 + filtered.length) % filtered.length)
          break
        case 'Enter':
          e.preventDefault()
          if (filtered[highlightIdx]) pick(filtered[highlightIdx].value)
          break
        case 'Escape':
          e.preventDefault()
          setOpen(false)
          break
      }
    },
    [open, filtered, highlightIdx, pick]
  )

  return (
    <div className={cn('space-y-1.5', className)} ref={wrapperRef}>
      {label && (
        <label
          htmlFor={id}
          className="block text-sm font-medium text-[color:var(--ink)]"
        >
          {label}
        </label>
      )}

      {/* Trigger */}
      <button
        type="button"
        id={id}
        role="combobox"
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-controls={listboxId}
        aria-invalid={!!error || undefined}
        aria-describedby={
          error ? `${id}-error` : helperText ? `${id}-helper` : undefined
        }
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={handleKeyDown}
        className={cn(
          triggerVariants({ size }),
          error &&
            'border-[hsl(var(--danger))] focus:border-[hsl(var(--danger))] focus:ring-[hsl(var(--danger))]',
        )}
      >
        <span
          className={cn(
            'flex items-center gap-2 truncate',
            !selected && 'text-[color:var(--muted-ink)]'
          )}
        >
          {selected?.icon}
          {selected?.label ?? placeholder}
        </span>

        <span className="flex shrink-0 items-center gap-1">
          {clearable && selected && (
            <span
              role="button"
              tabIndex={-1}
              aria-label="Clear selection"
              onClick={(e) => {
                e.stopPropagation()
                onChange?.('')
              }}
              className="rounded p-0.5 text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
            >
              <X className="h-3.5 w-3.5" />
            </span>
          )}
          <ChevronDown
            aria-hidden="true"
            className={cn(
              'h-4 w-4 text-[color:var(--muted-ink)] transition-transform',
              open && 'rotate-180'
            )}
          />
        </span>
      </button>

      {/* Dropdown */}
      <div
        className={cn(
          'relative z-50 transition-all duration-150',
          open
            ? 'opacity-100 pointer-events-auto'
            : 'opacity-0 pointer-events-none'
        )}
      >
        <ul
          ref={listRef}
          id={listboxId}
          role="listbox"
          aria-label={label ?? 'Options'}
          className="absolute left-0 right-0 top-1 max-h-60 overflow-auto rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] py-1 shadow-2xl"
        >
          {searchable && (
            <li className="sticky top-0 border-b border-[color:var(--line)] bg-[color:var(--panel)] px-2 py-1.5">
              <div className="relative">
                <Search className="pointer-events-none absolute inset-y-0 left-2 my-auto h-3.5 w-3.5 text-[color:var(--muted-ink)]" aria-hidden="true" />
                <input
                  ref={searchRef}
                  type="text"
                  aria-label="Search options"
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value)
                    setHighlightIdx(0)
                  }}
                  onKeyDown={handleKeyDown}
                  className="w-full rounded-lg bg-[color:var(--panel-strong)] py-1.5 pl-7 pr-2 text-xs text-[color:var(--ink)] placeholder:text-[color:var(--muted-ink)] outline-none"
                  placeholder="Search…"
                />
              </div>
            </li>
          )}

          {filtered.length === 0 && (
            <li className="px-3.5 py-2 text-sm text-[color:var(--muted-ink)]">
              No results
            </li>
          )}

          {filtered.map((opt, idx) => (
            <li
              key={opt.value}
              role="option"
              aria-selected={opt.value === value}
              data-highlighted={idx === highlightIdx || undefined}
              onMouseEnter={() => setHighlightIdx(idx)}
              onClick={() => pick(opt.value)}
              className={cn(
                'flex cursor-pointer items-center gap-2 px-3.5 py-2 text-sm transition-colors',
                idx === highlightIdx && 'bg-[color:var(--panel-strong)]',
                opt.value === value
                  ? 'font-medium text-[color:var(--accent-strong)]'
                  : 'text-[color:var(--ink)]'
              )}
            >
              {opt.icon}
              {opt.label}
            </li>
          ))}
        </ul>
      </div>

      {error && (
        <p id={`${id}-error`} className="text-xs text-[hsl(var(--danger))] mt-1" role="alert">
          {error}
        </p>
      )}
      {!error && helperText && (
        <p id={`${id}-helper`} className="text-xs text-[color:var(--muted-ink)] mt-1">
          {helperText}
        </p>
      )}
    </div>
  )
}

export { triggerVariants }
