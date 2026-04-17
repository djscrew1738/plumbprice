'use client'

import { forwardRef, useId, useCallback, useRef, useEffect } from 'react'
import { cn } from '@/lib/utils'

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
  helperText?: string
  showCount?: boolean
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      className,
      label,
      error,
      helperText,
      maxLength,
      showCount = false,
      id: idProp,
      onChange,
      value,
      defaultValue,
      ...props
    },
    ref
  ) => {
    const autoId = useId()
    const id = idProp ?? autoId
    const internalRef = useRef<HTMLTextAreaElement | null>(null)

    const setRefs = useCallback(
      (node: HTMLTextAreaElement | null) => {
        internalRef.current = node
        if (typeof ref === 'function') ref(node)
        else if (ref) (ref as React.MutableRefObject<HTMLTextAreaElement | null>).current = node
      },
      [ref]
    )

    const resize = useCallback(() => {
      const el = internalRef.current
      if (!el) return
      el.style.height = 'auto'
      el.style.height = `${el.scrollHeight}px`
    }, [])

    // Resize on mount and when value changes
    useEffect(() => {
      resize()
    }, [value, resize])

    const handleChange = useCallback(
      (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        resize()
        onChange?.(e)
      },
      [onChange, resize]
    )

    const currentLength =
      typeof value === 'string'
        ? value.length
        : typeof defaultValue === 'string'
          ? defaultValue.length
          : internalRef.current?.value.length ?? 0

    return (
      <div className="space-y-1.5">
        {label && (
          <label
            htmlFor={id}
            className="block text-sm font-medium text-[color:var(--ink)]"
          >
            {label}
          </label>
        )}

        <textarea
          ref={setRefs}
          id={id}
          aria-invalid={!!error || undefined}
          aria-describedby={
            error ? `${id}-error` : helperText ? `${id}-helper` : undefined
          }
          maxLength={maxLength}
          value={value}
          defaultValue={defaultValue}
          onChange={handleChange}
          className={cn(
            'min-h-[80px] w-full resize-none rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] px-3.5 py-2.5 text-sm text-[color:var(--ink)] placeholder:text-[color:var(--muted-ink)] transition-all focus:border-[color:var(--accent)] focus:outline-none focus:ring-2 focus:ring-[color:var(--accent)] disabled:cursor-not-allowed disabled:opacity-50',
            error &&
              'border-[hsl(var(--danger))] focus:border-[hsl(var(--danger))] focus:ring-[hsl(var(--danger))]',
            className
          )}
          {...props}
        />

        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
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

          {showCount && maxLength != null && (
            <span
              className={cn(
                'shrink-0 text-xs mt-1',
                currentLength >= maxLength
                  ? 'text-[hsl(var(--danger))]'
                  : 'text-[color:var(--muted-ink)]'
              )}
            >
              {currentLength}/{maxLength}
            </span>
          )}
        </div>
      </div>
    )
  }
)

Textarea.displayName = 'Textarea'
