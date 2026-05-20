import { type HTMLAttributes, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

type Gap = 'xs' | 'sm' | 'md' | 'lg' | 'xl'

const gapClass: Record<Gap, string> = {
  xs: 'gap-1',
  sm: 'gap-2',
  md: 'gap-4',
  lg: 'gap-6',
  xl: 'gap-8',
}

export interface StackProps extends HTMLAttributes<HTMLDivElement> {
  gap?: Gap
  children: ReactNode
}

/** Vertical layout helper. */
export function Stack({ gap = 'md', className, children, ...rest }: StackProps) {
  return (
    <div className={cn('flex flex-col', gapClass[gap], className)} {...rest}>
      {children}
    </div>
  )
}

export interface InlineProps extends HTMLAttributes<HTMLDivElement> {
  gap?: Gap
  wrap?: boolean
  align?: 'start' | 'center' | 'end' | 'baseline'
  justify?: 'start' | 'center' | 'end' | 'between'
  children: ReactNode
}

const alignClass = {
  start: 'items-start',
  center: 'items-center',
  end: 'items-end',
  baseline: 'items-baseline',
}
const justifyClass = {
  start: 'justify-start',
  center: 'justify-center',
  end: 'justify-end',
  between: 'justify-between',
}

/** Horizontal layout helper. */
export function Inline({
  gap = 'sm',
  wrap,
  align = 'center',
  justify = 'start',
  className,
  children,
  ...rest
}: InlineProps) {
  return (
    <div
      className={cn(
        'flex',
        wrap && 'flex-wrap',
        gapClass[gap],
        alignClass[align],
        justifyClass[justify],
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  )
}

export interface GridProps extends HTMLAttributes<HTMLDivElement> {
  /** Responsive column count. Number = same at all breakpoints. */
  cols?: number | { base?: number; sm?: number; md?: number; lg?: number; xl?: number }
  gap?: Gap
  children: ReactNode
}

// Static maps so Tailwind JIT can find every class. Do NOT compose
// these names dynamically — `grid-cols-${n}` would not be detected.
const baseCols: Record<number, string> = {
  1: 'grid-cols-1',
  2: 'grid-cols-2',
  3: 'grid-cols-3',
  4: 'grid-cols-4',
  5: 'grid-cols-5',
  6: 'grid-cols-6',
  12: 'grid-cols-12',
}
const smCols: Record<number, string> = {
  1: 'sm:grid-cols-1',
  2: 'sm:grid-cols-2',
  3: 'sm:grid-cols-3',
  4: 'sm:grid-cols-4',
  5: 'sm:grid-cols-5',
  6: 'sm:grid-cols-6',
  12: 'sm:grid-cols-12',
}
const mdCols: Record<number, string> = {
  1: 'md:grid-cols-1',
  2: 'md:grid-cols-2',
  3: 'md:grid-cols-3',
  4: 'md:grid-cols-4',
  5: 'md:grid-cols-5',
  6: 'md:grid-cols-6',
  12: 'md:grid-cols-12',
}
const lgCols: Record<number, string> = {
  1: 'lg:grid-cols-1',
  2: 'lg:grid-cols-2',
  3: 'lg:grid-cols-3',
  4: 'lg:grid-cols-4',
  5: 'lg:grid-cols-5',
  6: 'lg:grid-cols-6',
  12: 'lg:grid-cols-12',
}
const xlCols: Record<number, string> = {
  1: 'xl:grid-cols-1',
  2: 'xl:grid-cols-2',
  3: 'xl:grid-cols-3',
  4: 'xl:grid-cols-4',
  5: 'xl:grid-cols-5',
  6: 'xl:grid-cols-6',
  12: 'xl:grid-cols-12',
}

/** Responsive CSS grid helper. */
export function Grid({ cols = 1, gap = 'md', className, children, ...rest }: GridProps) {
  const colClasses =
    typeof cols === 'number'
      ? baseCols[cols] ?? baseCols[1]
      : cn(
          baseCols[cols.base ?? 1] ?? baseCols[1],
          cols.sm && smCols[cols.sm],
          cols.md && mdCols[cols.md],
          cols.lg && lgCols[cols.lg],
          cols.xl && xlCols[cols.xl],
        )
  return (
    <div className={cn('grid', colClasses, gapClass[gap], className)} {...rest}>
      {children}
    </div>
  )
}
