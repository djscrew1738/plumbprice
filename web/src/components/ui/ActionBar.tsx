'use client'

import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'

export function ActionBar({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn('flex flex-wrap items-center gap-2', className)}>
      {children}
    </div>
  )
}

export function ActionBarGroup({
  children,
  align = 'left',
  className,
}: {
  children: ReactNode
  align?: 'left' | 'right'
  className?: string
}) {
  return (
    <div
      className={cn(
        'flex items-center gap-2',
        align === 'right' && 'ml-auto',
        className,
      )}
    >
      {children}
    </div>
  )
}

export function ActionBarDivider({ className }: { className?: string }) {
  return (
    <div
      className={cn('mx-1 h-5 w-px bg-[color:var(--line)]', className)}
      aria-hidden="true"
    />
  )
}
