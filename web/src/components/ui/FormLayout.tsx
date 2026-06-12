'use client'

import { type FormEvent, type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { Button } from './Button'

export interface FormLayoutProps {
  /** Accessible name of the form. */
  title?: string
  /** Optional subtitle/description shown below the title. */
  description?: string
  children: ReactNode
  /** Primary submit button label. */
  submitLabel?: string
  /** Secondary action, e.g. a cancel button or link. */
  secondaryAction?: ReactNode
  /** Full-width error message displayed above actions. */
  error?: string | null
  /** Disabled state for the submit button. */
  isSubmitting?: boolean
  /** Additional classes for the submit button. */
  submitButtonClassName?: string
  /** Additional footer content rendered alongside actions. */
  footer?: ReactNode
  onSubmit?: (e: FormEvent<HTMLFormElement>) => void
  className?: string
}

export function FormLayout({
  title,
  description,
  children,
  submitLabel = 'Submit',
  secondaryAction,
  error,
  isSubmitting = false,
  submitButtonClassName,
  footer,
  onSubmit,
  className,
}: FormLayoutProps) {
  return (
    <form
      onSubmit={onSubmit}
      className={cn('space-y-5', className)}
      aria-label={title}
      noValidate
    >
      {(title || description) && (
        <div className="space-y-1">
          {title && (
            <h2 className="text-lg font-semibold text-[color:var(--ink)]">{title}</h2>
          )}
          {description && (
            <p className="text-sm text-[color:var(--muted-ink)]">{description}</p>
          )}
        </div>
      )}

      <div className="space-y-4">{children}</div>

      {error && (
        <p className="rounded-lg border border-[hsl(var(--danger))]/20 bg-[hsl(var(--danger))]/10 px-3 py-2 text-sm text-[hsl(var(--danger))]" role="alert">
          {error}
        </p>
      )}

      <div className="flex items-center justify-between gap-3 pt-1">
        {secondaryAction && <div>{secondaryAction}</div>}
        <Button
          type="submit"
          disabled={isSubmitting}
          className={cn(secondaryAction ? '' : 'ml-auto', submitButtonClassName)}
        >
          {isSubmitting ? 'Please wait…' : submitLabel}
        </Button>
      </div>

      {footer && <div className="text-xs text-[color:var(--muted-ink)]">{footer}</div>}
    </form>
  )
}
