'use client'

import { type ReactNode } from 'react'
import Link from 'next/link'
import { ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { PAGE_META } from '@/components/layout/nav'

/* ------------------------------------------------------------------ */
/*  BreadcrumbRoot                                                     */
/* ------------------------------------------------------------------ */

export interface BreadcrumbRootProps {
  children: ReactNode
  className?: string
}

export function BreadcrumbRoot({ children, className }: BreadcrumbRootProps) {
  return (
    <nav aria-label="Breadcrumb" className={className}>
      <ol className="flex items-center gap-1.5">{children}</ol>
    </nav>
  )
}

/* ------------------------------------------------------------------ */
/*  BreadcrumbItem                                                     */
/* ------------------------------------------------------------------ */

export interface BreadcrumbItemProps {
  href?: string
  current?: boolean
  children: ReactNode
  className?: string
}

export function BreadcrumbItem({
  href,
  current = false,
  children,
  className,
}: BreadcrumbItemProps) {
  const baseClass = cn(
    'text-sm transition-colors',
    current
      ? 'text-[color:var(--ink)] font-semibold'
      : 'text-[color:var(--muted-ink)] hover:text-[color:var(--ink)]',
    className,
  )

  return (
    <li className="inline-flex items-center" aria-current={current ? 'page' : undefined}>
      {href && !current ? (
        <Link href={href} className={baseClass}>
          {children}
        </Link>
      ) : (
        <span className={baseClass}>{children}</span>
      )}
    </li>
  )
}

/* ------------------------------------------------------------------ */
/*  BreadcrumbSeparator                                                */
/* ------------------------------------------------------------------ */

export interface BreadcrumbSeparatorProps {
  className?: string
}

export function BreadcrumbSeparator({ className }: BreadcrumbSeparatorProps) {
  return (
    <li aria-hidden="true" className={cn('text-[color:var(--muted-ink)]', className)}>
      <ChevronRight size={12} />
    </li>
  )
}

/* ------------------------------------------------------------------ */
/*  buildBreadcrumbs helper                                            */
/* ------------------------------------------------------------------ */

export interface BreadcrumbEntry {
  label: string
  href: string
}

/**
 * Parse a pathname into an array of breadcrumb entries.
 * Uses PAGE_META to resolve human-readable labels for known routes,
 * and falls back to capitalised path segments for dynamic routes.
 */
export function buildBreadcrumbs(pathname: string): BreadcrumbEntry[] {
  const crumbs: BreadcrumbEntry[] = [{ label: 'Home', href: '/' }]

  if (pathname === '/') return crumbs

  const segments = pathname.split('/').filter(Boolean)
  let accumulated = ''

  for (const segment of segments) {
    accumulated += `/${segment}`
    const meta = PAGE_META[accumulated]
    const label = meta
      ? meta.title
      : segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, ' ')
    crumbs.push({ label, href: accumulated })
  }

  return crumbs
}
