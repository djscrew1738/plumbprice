import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'

export interface PageHeaderProps {
  /** Small uppercase label above the title (e.g. "Estimator"). */
  eyebrow?: ReactNode
  /** Page title. Rendered as an `<h1>`. */
  title: ReactNode
  /** Optional supporting copy under the title. */
  description?: ReactNode
  /** Right-aligned actions (buttons, filters). */
  actions?: ReactNode
  className?: string
}

/**
 * Standard page header. Use directly inside `PageShell` for consistent
 * spacing and typographic rhythm across all pages.
 */
export function PageHeader({ eyebrow, title, description, actions, className }: PageHeaderProps) {
  return (
    <header
      className={cn(
        'mb-[var(--space-section)] flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-6',
        className,
      )}
    >
      <div className="min-w-0 flex-1">
        {eyebrow ? (
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[color:var(--muted-ink)]">
            {eyebrow}
          </div>
        ) : null}
        <h1 className="truncate text-2xl font-semibold text-[color:var(--ink)] sm:text-[28px] sm:leading-tight">
          {title}
        </h1>
        {description ? (
          <p className="mt-1.5 max-w-[60ch] text-sm text-[color:var(--muted-ink)]">{description}</p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex flex-shrink-0 flex-wrap items-center gap-2">{actions}</div>
      ) : null}
    </header>
  )
}
