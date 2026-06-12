'use client'

import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'

export interface FormSectionProps {
  title?: string
  description?: string
  children: ReactNode
  className?: string
}

export function FormSection({ title, description, children, className }: FormSectionProps) {
  return (
    <fieldset className={cn('space-y-4', className)}>
      {(title || description) && (
        <legend className="mb-2 w-full space-y-1">
          {title && (
            <span className="block text-sm font-semibold text-[color:var(--ink)]">{title}</span>
          )}
          {description && (
            <span className="block text-xs text-[color:var(--muted-ink)]">{description}</span>
          )}
        </legend>
      )}
      {children}
    </fieldset>
  )
}
