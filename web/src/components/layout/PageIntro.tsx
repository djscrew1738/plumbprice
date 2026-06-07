'use client'

import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface PageIntroProps {
  icon?: LucideIcon
  eyebrow?: string
  title: string
  description?: string
  actions?: ReactNode
  children?: ReactNode
  className?: string
  variant?: 'default' | 'compact'
}

export function PageIntro({
  icon: Icon,
  eyebrow,
  title,
  description,
  actions,
  children,
  className,
  variant = 'default',
}: PageIntroProps) {
  const isCompact = variant === 'compact'

  return (
    <section
      className={cn(
        'shell-panel',
        isCompact ? 'p-4' : 'p-5 sm:p-6',
        className
      )}
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="flex items-start gap-4">
          {Icon && (
            <div
              className={cn(
                'flex shrink-0 items-center justify-center rounded-[1.25rem] bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]',
                isCompact ? 'size-10' : 'size-12'
              )}
            >
              <Icon size={isCompact ? 16 : 18} aria-hidden="true" />
            </div>
          )}
          <div className="min-w-0">
            {eyebrow && (
              <p className={cn(
                'uppercase text-[color:var(--muted-ink)]',
                isCompact ? 'text-[10px] font-bold tracking-[0.14em]' : 'text-eyebrow'
              )}>
                {eyebrow}
              </p>
            )}
            <h1
              className={cn(
                'font-bold text-[color:var(--ink)]',
                isCompact ? 'mt-1 text-xl' : 'mt-2 text-2xl font-display sm:text-display-lg tracking-tight'
              )}
            >
              {title}
            </h1>
            {description && (
              <p className={cn(
                'mt-2 max-w-2xl text-[color:var(--muted-ink)]',
                isCompact ? 'text-sm' : 'text-body'
              )}>
                {description}
              </p>
            )}
          </div>
        </div>
        {actions && <div className="flex shrink-0 items-start gap-2 md:pt-6">{actions}</div>}
      </div>
      {children}
    </section>
  )
}
