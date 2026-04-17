'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { Search, X, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface SearchInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  isLoading?: boolean
  className?: string
  debounceMs?: number
  'aria-label'?: string
}

export function SearchInput({
  value,
  onChange,
  placeholder = 'Search…',
  isLoading = false,
  className,
  debounceMs = 300,
  'aria-label': ariaLabel = 'Search',
}: SearchInputProps) {
  const [internal, setInternal] = useState(value)
  const inputRef = useRef<HTMLInputElement>(null)

  // Sync external value → internal when parent changes it
  useEffect(() => {
    setInternal(value)
  }, [value])

  // Debounced callback to parent
  useEffect(() => {
    if (internal === value) return
    const timer = setTimeout(() => onChange(internal), debounceMs)
    return () => clearTimeout(timer)
  }, [internal, debounceMs, onChange, value])

  const handleClear = useCallback(() => {
    setInternal('')
    onChange('')
    inputRef.current?.focus()
  }, [onChange])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        handleClear()
      }
    },
    [handleClear],
  )

  return (
    <div className={cn('relative', className)}>
      {/* Left icon — spinner or search */}
      <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-[color:var(--muted-ink)]">
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        ) : (
          <Search className="h-4 w-4" aria-hidden="true" />
        )}
      </span>

      <input
        ref={inputRef}
        role="searchbox"
        aria-label={ariaLabel}
        type="text"
        className={cn('input pl-10 pr-10')}
        placeholder={placeholder}
        value={internal}
        onChange={(e) => setInternal(e.target.value)}
        onKeyDown={handleKeyDown}
      />

      {/* Clear button */}
      {internal && (
        <button
          type="button"
          aria-label="Clear search"
          onClick={handleClear}
          className="absolute inset-y-0 right-3 flex items-center text-[color:var(--muted-ink)] transition-colors hover:text-[color:var(--ink)]"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  )
}
