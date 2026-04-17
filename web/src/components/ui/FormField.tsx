'use client'

import { useId, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

export interface FormFieldProps {
  label: string
  htmlFor?: string
  error?: string
  helperText?: string
  required?: boolean
  children: ReactNode
  className?: string
}

export function FormField({
  label,
  htmlFor,
  error,
  helperText,
  required = false,
  children,
  className,
}: FormFieldProps) {
  const autoId = useId()
  const id = htmlFor ?? autoId

  return (
    <div className={cn('space-y-1.5', className)}>
      <label
        htmlFor={id}
        className="block text-sm font-medium text-[color:var(--ink)]"
      >
        {label}
        {required && (
          <span className="ml-0.5 text-[hsl(var(--danger))]" aria-hidden="true">
            *
          </span>
        )}
      </label>

      {children}

      {error && (
        <p className="text-xs text-[hsl(var(--danger))] mt-1" role="alert">
          {error}
        </p>
      )}
      {!error && helperText && (
        <p className="text-xs text-[color:var(--muted-ink)] mt-1">
          {helperText}
        </p>
      )}
    </div>
  )
}
