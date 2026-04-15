'use client'

import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface PageIntroProps {
  eyebrow?: string
  title: string
  description?: string
  actions?: ReactNode
  children?: ReactNode
  className?: string
}

export function PageIntro({
  eyebrow,
  title,
  description,
  actions,
  children,
  className,
}: PageIntroProps) {
  return (
    <section className={cn('shell-panel p-5 sm:p-6', className)}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          {eyebrow && (
            <p className="text-[11px] font-bold text-[color:var(--accent-strong)]">
              {eyebrow}
            </p>
          )}
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-[color:var(--ink)] sm:text-3xl">
            {title}
          </h2>
          {description && (
            <p className="mt-2 max-w-2xl text-sm text-[color:var(--muted-ink)] sm:text-base">
              {description}
            </p>
          )}
        </div>

        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>

      {children && (
        <div className="mt-4 border-t border-[color:var(--line)] pt-4">
          {children}
        </div>
      )}
    </section>
  )
}
