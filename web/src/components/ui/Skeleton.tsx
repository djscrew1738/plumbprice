'use client'

import { cn } from '@/lib/utils'

/* ── Types ───────────────────────────────────────── */

export type SkeletonVariant =
  | 'text'
  | 'card'
  | 'table-row'
  | 'avatar'
  | 'stat-card'
  | 'line'

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Visual variant with sensible default dimensions. */
  variant?: SkeletonVariant
  /** Extra Tailwind classes for custom sizing / overrides. */
  className?: string
  /** Repeat this skeleton N times (stagger via SkeletonGroup). */
  count?: number
  /** Enable shimmer animation (default true). Respects prefers-reduced-motion via CSS. */
  animate?: boolean
}

/* ── Variant class map ───────────────────────────── */

const variantClasses: Record<SkeletonVariant, string> = {
  text: 'h-4 w-full rounded',
  card: 'h-32 w-full rounded-2xl',
  'table-row': 'h-12 w-full rounded-lg',
  avatar: 'h-10 w-10 rounded-full',
  'stat-card': 'h-[60px] w-full rounded-2xl',
  line: 'h-4 w-full rounded',
}

/** Base stagger delay per item (seconds). */
const STAGGER_STEP = 0.12

/* ── Skeleton ────────────────────────────────────── */

export function Skeleton({
  variant = 'line',
  className,
  count,
  animate = true,
  style,
  ...rest
}: SkeletonProps) {
  if (count && count > 1) {
    return <SkeletonGroup count={count} variant={variant} animate={animate} className={className} {...rest} />
  }

  return (
    <div
      className={cn(
        variantClasses[variant],
        animate && 'skeleton',
        !animate && 'bg-[hsl(var(--muted))]',
        className,
      )}
      style={style}
      aria-hidden="true"
      {...rest}
    />
  )
}

/* ── SkeletonGroup ───────────────────────────────── */

export interface SkeletonGroupProps extends Omit<SkeletonProps, 'count'> {
  /** Number of skeletons to render. */
  count: number
}

export function SkeletonGroup({
  count,
  variant = 'line',
  animate = true,
  className,
  style,
  ...rest
}: SkeletonGroupProps) {
  return (
    <div className="flex flex-col gap-2" role="status" aria-label="Loading…">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={cn(
            variantClasses[variant],
            animate && 'skeleton',
            !animate && 'bg-[hsl(var(--muted))]',
            className,
          )}
          style={{
            animationDelay: animate ? `${i * STAGGER_STEP}s` : undefined,
            ...style,
          }}
          aria-hidden="true"
          {...rest}
        />
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  )
}

/* ── Legacy named skeletons (backward-compatible) ── */

export function PageSkeleton() {
  return (
    <div className="p-4">
      <Skeleton variant="text" className="mb-4 h-8 w-1/3 rounded-lg" />
      <div className="space-y-3">
        <Skeleton variant="card" className="h-16 rounded-xl" />
        <Skeleton variant="card" className="h-16 rounded-xl" />
        <Skeleton variant="card" className="h-16 rounded-xl" />
        <Skeleton variant="card" className="h-16 rounded-xl" />
      </div>
    </div>
  )
}

export function ListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton flex h-16 w-full items-center gap-3 rounded-xl p-3">
          <Skeleton variant="avatar" className="h-10 w-10 rounded-lg" />
          <div className="flex-1 space-y-2">
            <Skeleton variant="text" className="h-3 w-2/3" />
            <Skeleton variant="text" className="h-2 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  )
}

export function CardSkeleton() {
  return (
    <div className="skeleton rounded-2xl p-4">
      <Skeleton variant="text" className="mb-3 h-5 w-1/2" />
      <Skeleton variant="text" className="h-3 w-full" />
      <Skeleton variant="text" className="mt-2 h-3 w-2/3" />
    </div>
  )
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-1">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton flex h-12 items-center justify-between rounded-lg px-4">
          <Skeleton variant="text" className="h-4 w-1/4" />
          <Skeleton variant="text" className="h-4 w-1/6" />
          <Skeleton variant="text" className="h-4 w-1/6" />
        </div>
      ))}
    </div>
  )
}

export function ChatSkeleton() {
  return (
    <div className="flex flex-col gap-4 p-3">
      <div className="flex gap-3">
        <Skeleton variant="avatar" className="h-6 w-6" />
        <div className="flex-1 space-y-2">
          <Skeleton variant="text" className="h-4 w-full rounded-lg" />
          <Skeleton variant="text" className="h-4 w-3/4 rounded-lg" />
        </div>
      </div>
      <div className="ml-auto flex gap-3">
        <div className="h-4 max-w-[80%] skeleton rounded-lg rounded-bl-sm bg-[color:var(--accent)] px-4 py-2" />
      </div>
    </div>
  )
}

export function EmptyStateSkeleton() {
  return (
    <div className="flex h-[400px] flex-col items-center justify-center gap-4">
      <Skeleton variant="card" className="h-16 w-16 rounded-2xl" />
      <Skeleton variant="text" className="h-4 w-48" />
      <Skeleton variant="text" className="h-3 w-72" />
    </div>
  )
}
