'use client'

import {
  createContext,
  useContext,
  useId,
  useCallback,
  type ReactNode,
} from 'react'
import { cn } from '@/lib/utils'

/* ── Context ───────────────────────────────────────── */

interface RadioGroupCtx {
  name: string
  value: string
  onChange: (value: string) => void
}

const Ctx = createContext<RadioGroupCtx | null>(null)

function useRadioGroup() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('RadioItem must be used inside RadioGroup')
  return ctx
}

/* ── RadioGroup ────────────────────────────────────── */

export interface RadioGroupProps {
  label?: string
  value: string
  onChange: (value: string) => void
  children: ReactNode
  orientation?: 'horizontal' | 'vertical'
  className?: string
}

export function RadioGroup({
  label,
  value,
  onChange,
  children,
  orientation = 'vertical',
  className,
}: RadioGroupProps) {
  const groupId = useId()

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      const el = e.currentTarget
      const radios = Array.from(
        el.querySelectorAll<HTMLInputElement>('input[type="radio"]:not(:disabled)')
      )
      const current = radios.findIndex((r) => r.value === value)
      if (current < 0) return

      let next = -1
      if (
        (e.key === 'ArrowDown' && orientation === 'vertical') ||
        (e.key === 'ArrowRight' && orientation === 'horizontal')
      ) {
        e.preventDefault()
        next = (current + 1) % radios.length
      } else if (
        (e.key === 'ArrowUp' && orientation === 'vertical') ||
        (e.key === 'ArrowLeft' && orientation === 'horizontal')
      ) {
        e.preventDefault()
        next = (current - 1 + radios.length) % radios.length
      }

      if (next >= 0) {
        const radio = radios[next]
        radio.focus()
        onChange(radio.value)
      }
    },
    [value, onChange, orientation]
  )

  return (
    <Ctx.Provider value={{ name: groupId, value, onChange }}>
      <fieldset className={cn('space-y-1.5', className)}>
        {label && (
          <legend className="text-sm font-medium text-[color:var(--ink)] mb-1.5">
            {label}
          </legend>
        )}

        <div
          role="radiogroup"
          aria-label={label}
          onKeyDown={handleKeyDown}
          className={cn(
            'flex',
            orientation === 'vertical'
              ? 'flex-col gap-2'
              : 'flex-row flex-wrap gap-4'
          )}
        >
          {children}
        </div>
      </fieldset>
    </Ctx.Provider>
  )
}

/* ── RadioItem ─────────────────────────────────────── */

export interface RadioItemProps {
  value: string
  label: string
  description?: string
  disabled?: boolean
  className?: string
}

export function RadioItem({
  value,
  label,
  description,
  disabled = false,
  className,
}: RadioItemProps) {
  const { name, value: selected, onChange } = useRadioGroup()
  const id = useId()
  const isSelected = value === selected

  return (
    <label
      htmlFor={id}
      className={cn(
        'group flex items-start gap-2.5 select-none',
        disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer',
        className
      )}
    >
      <input
        id={id}
        type="radio"
        name={name}
        value={value}
        checked={isSelected}
        disabled={disabled}
        onChange={() => onChange(value)}
        className="sr-only peer"
        aria-describedby={description ? `${id}-desc` : undefined}
      />

      {/* Custom circle */}
      <span
        aria-hidden="true"
        className={cn(
          'mt-0.5 flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full border transition-all',
          isSelected
            ? 'border-[color:var(--accent)] bg-[color:var(--accent)]'
            : 'border-[color:var(--line)] bg-[color:var(--panel)] group-hover:border-[color:var(--accent)]',
          'peer-focus-visible:ring-2 peer-focus-visible:ring-[color:var(--accent)] peer-focus-visible:ring-offset-2 peer-focus-visible:ring-offset-[hsl(var(--background))]'
        )}
      >
        {isSelected && (
          <span className="h-2 w-2 rounded-full bg-white" />
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
