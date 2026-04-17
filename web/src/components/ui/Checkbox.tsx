'use client'

import { useId, useRef, useEffect } from 'react'
import { cn } from '@/lib/utils'

export interface CheckboxProps {
  label: string
  checked: boolean
  onChange: (checked: boolean) => void
  indeterminate?: boolean
  disabled?: boolean
  description?: string
  className?: string
  id?: string
}

export function Checkbox({
  label,
  checked,
  onChange,
  indeterminate = false,
  disabled = false,
  description,
  className,
  id: idProp,
}: CheckboxProps) {
  const autoId = useId()
  const id = idProp ?? autoId
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.indeterminate = indeterminate
    }
  }, [indeterminate])

  return (
    <label
      htmlFor={id}
      className={cn(
        'group flex items-start gap-2.5 select-none',
        disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer',
        className
      )}
    >
      {/* Hidden native checkbox for accessibility */}
      <input
        ref={inputRef}
        id={id}
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="sr-only peer"
        aria-describedby={description ? `${id}-desc` : undefined}
      />

      {/* Custom visual */}
      <span
        aria-hidden="true"
        className={cn(
          'mt-0.5 flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-md border transition-all',
          checked || indeterminate
            ? 'border-[color:var(--accent)] bg-[color:var(--accent)]'
            : 'border-[color:var(--line)] bg-[color:var(--panel)] group-hover:border-[color:var(--accent)]',
          'peer-focus-visible:ring-2 peer-focus-visible:ring-[color:var(--accent)] peer-focus-visible:ring-offset-2 peer-focus-visible:ring-offset-[hsl(var(--background))]'
        )}
      >
        {checked && !indeterminate && (
          <svg
            className="h-3 w-3 text-white"
            viewBox="0 0 12 12"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M2.5 6l2.5 2.5 4.5-5" />
          </svg>
        )}
        {indeterminate && (
          <svg
            className="h-3 w-3 text-white"
            viewBox="0 0 12 12"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
          >
            <path d="M3 6h6" />
          </svg>
        )}
      </span>

      {/* Text */}
      <span className="flex flex-col">
        <span className="text-sm font-medium text-[color:var(--ink)] leading-tight">
          {label}
        </span>
        {description && (
          <span
            id={`${id}-desc`}
            className="mt-0.5 text-xs text-[color:var(--muted-ink)] leading-snug"
          >
            {description}
          </span>
        )}
      </span>
    </label>
  )
}
