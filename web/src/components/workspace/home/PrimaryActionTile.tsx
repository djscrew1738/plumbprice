'use client'

import Link from 'next/link'
import { ArrowRight, type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface PrimaryActionTileProps {
  href: string
  title: string
  description: string
  icon: LucideIcon
  /** Visual emphasis. `default` = filled accent; `muted` = neutral surface. */
  tone?: 'default' | 'muted'
  className?: string
}

/**
 * Large, finger-friendly call-to-action tile used in the home Hero.
 * Designed to be the first thing a returning estimator interacts with.
 */
export function PrimaryActionTile({
  href,
  title,
  description,
  icon: Icon,
  tone = 'default',
  className,
}: PrimaryActionTileProps) {
  return (
    <Link
      href={href}
      className={cn(
        'group relative flex min-h-[120px] flex-col justify-between gap-4 overflow-hidden rounded-[var(--radius-xl)] border p-5 transition-all duration-200 sm:p-6',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ring-focus)] focus-visible:ring-offset-2 focus-visible:ring-offset-[hsl(var(--background))]',
        tone === 'default'
          ? 'border-transparent bg-gradient-to-br from-[color:var(--accent)] to-[color:var(--accent-strong)] text-white shadow-[var(--shadow-md)] hover:shadow-[var(--shadow-lg)]'
          : 'border-[color:var(--border-subtle)] bg-[color:var(--surface-1)] text-[color:var(--ink)] shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)]',
        className,
      )}
    >
      <span
        className={cn(
          'flex size-11 items-center justify-center rounded-[var(--radius-md)] transition-transform duration-200 group-hover:scale-105',
          tone === 'default'
            ? 'bg-white/15 text-white'
            : 'bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]',
        )}
      >
        <Icon size={22} aria-hidden />
      </span>
      <div className="min-w-0">
        <h3 className="text-base font-semibold sm:text-lg">{title}</h3>
        <p
          className={cn(
            'mt-1 text-sm',
            tone === 'default' ? 'text-white/85' : 'text-[color:var(--muted-ink)]',
          )}
        >
          {description}
        </p>
      </div>
      <ArrowRight
        size={18}
        className={cn(
          'absolute right-5 top-5 transition-transform duration-200 group-hover:translate-x-0.5 sm:right-6 sm:top-6',
          tone === 'default' ? 'text-white/85' : 'text-[color:var(--muted-ink)]',
        )}
        aria-hidden
      />
    </Link>
  )
}
