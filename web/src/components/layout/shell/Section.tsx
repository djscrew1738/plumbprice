import { type HTMLAttributes, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

export interface SectionProps extends Omit<HTMLAttributes<HTMLElement>, 'title'> {
  title?: ReactNode
  description?: ReactNode
  actions?: ReactNode
  children: ReactNode
}

/**
 * Labeled content section with consistent vertical rhythm.
 * Use for grouping related blocks inside a `PageShell`.
 */
export function Section({
  title,
  description,
  actions,
  children,
  className,
  ...rest
}: SectionProps) {
  return (
    <section className={cn('mb-[var(--space-section)] last:mb-0', className)} {...rest}>
      {(title || actions) && (
        <div className="mb-3 flex items-end justify-between gap-3">
          <div className="min-w-0">
            {title ? (
              <h2 className="text-base font-semibold text-[color:var(--ink)]">{title}</h2>
            ) : null}
            {description ? (
              <p className="mt-0.5 text-xs text-[color:var(--muted-ink)]">{description}</p>
            ) : null}
          </div>
          {actions ? <div className="flex flex-shrink-0 items-center gap-2">{actions}</div> : null}
        </div>
      )}
      {children}
    </section>
  )
}
