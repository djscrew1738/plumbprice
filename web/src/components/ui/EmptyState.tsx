'use client'

import { type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { useReducedMotion } from '@/lib/useReducedMotion'

export interface EmptyStateProps {
  icon: ReactNode
  title: string
  description: string
  action?: ReactNode
  className?: string
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className={cn(
        'flex flex-col items-center text-center p-6 md:p-8',
        className,
      )}
    >
      <motion.div
        animate={reduce ? {} : { y: [0, -3, 0] }}
        transition={reduce ? {} : { duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        className="flex size-12 items-center justify-center rounded-2xl bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]"
        aria-hidden="true"
      >
        {icon}
      </motion.div>

      <h3 className="mt-4 text-base font-semibold text-[color:var(--ink)]">
        {title}
      </h3>

      <p className="mt-1 max-w-xs text-sm text-[color:var(--muted-ink)]">
        {description}
      </p>

      {action && <div className="mt-4">{action}</div>}
    </motion.div>
  )
}
