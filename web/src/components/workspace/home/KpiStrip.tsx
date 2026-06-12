'use client'

import Link from 'next/link'
import { ArrowUpRight } from 'lucide-react'
import { BlurFade, CountUp, StaggerContainer, StaggerItem } from '@/components/ui/Motion'
import { cn, parseCurrencyValue } from '@/lib/utils'

export interface KpiItem {
  label: string
  value: string
  /** Subtle context line (e.g. "Last 7 days"). */
  hint?: string
  /** Optional href turns the KPI into a tappable link. */
  href?: string
  /** Optional emphasis tone for the value. */
  tone?: 'default' | 'warning' | 'success'
}

export interface KpiStripProps {
  items: KpiItem[]
  className?: string
}

function KpiValue({ value }: { value: string }) {
  const parsed = parseCurrencyValue(value)
  if (parsed !== null) {
    return (
      <CountUp
        value={parsed}
        duration={0.8}
        formatter={(n) => `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
      />
    )
  }
  const numeric = parseFloat(value.replace(/[^0-9.]/g, ''))
  if (!Number.isNaN(numeric) && value.trim().length > 0) {
    const suffix = value.replace(/[0-9.,]/g, '').trim()
    return (
      <CountUp
        value={numeric}
        duration={0.8}
        formatter={(n) => `${Math.round(n)}${suffix ? ` ${suffix}` : ''}`}
      />
    )
  }
  return <>{value}</>
}

/**
 * Compact, icon-free KPI strip. Replaces the previous icon-heavy stat-card grid.
 * Horizontal scroll on mobile, evenly distributed on `sm+`.
 */
export function KpiStrip({ items, className }: KpiStripProps) {
  return (
    <BlurFade delay={0.2} duration={0.4}>
      <StaggerContainer
        as="div"
        stagger={0.05}
        initialDelay={0.22}
        className={cn(
          'flex w-full snap-x snap-mandatory gap-2 overflow-x-auto rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-1)] p-1.5 shadow-[var(--shadow-sm)] sm:grid sm:auto-cols-fr sm:grid-flow-col sm:overflow-visible',
          className,
        )}
        role="list"
        aria-label="Key metrics"
      >
        {items.map((item) => {
          const Tag: React.ElementType = item.href ? Link : 'div'
          const linkProps = item.href ? { href: item.href } : {}
          return (
            <StaggerItem key={item.label}>
              <Tag
                {...linkProps}
                role="listitem"
                className={cn(
                  'group block min-w-[10rem] snap-start rounded-[var(--radius-md)] px-3 py-2 sm:min-w-0',
                  item.href &&
                    'transition-colors hover:bg-[color:var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ring-focus)]',
                )}
              >
                <p className="flex items-center gap-1 text-[11px] font-medium uppercase tracking-wide text-[color:var(--muted-ink)]">
                  {item.label}
                  {item.href && (
                    <ArrowUpRight
                      size={11}
                      className="opacity-0 transition-opacity group-hover:opacity-100"
                      aria-hidden
                    />
                  )}
                </p>
                <p
                  className={cn(
                    'mt-0.5 text-lg font-semibold tabular-nums leading-tight sm:text-xl',
                    item.tone === 'warning' && 'text-[hsl(var(--warning))]',
                    item.tone === 'success' && 'text-[color:var(--accent-strong)]',
                    (!item.tone || item.tone === 'default') && 'text-[color:var(--ink)]',
                  )}
                >
                  <KpiValue value={item.value} />
                </p>
                {item.hint && (
                  <p className="text-[11px] text-[color:var(--muted-ink)]">{item.hint}</p>
                )}
              </Tag>
            </StaggerItem>
          )
        })}
      </StaggerContainer>
    </BlurFade>
  )
}
