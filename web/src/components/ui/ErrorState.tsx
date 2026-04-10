'use client'

import { AlertTriangle } from 'lucide-react'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/Button'
import { cn } from '@/lib/utils'

export interface ErrorStateProps {
  message: string
  onRetry?: () => void
  code?: string | number
  className?: string
}

export function ErrorState({
  message,
  onRetry,
  code,
  className,
}: ErrorStateProps) {
  return (
    <motion.div
      role="alert"
      aria-live="polite"
      initial={{ opacity: 0, x: -4 }}
      animate={{ opacity: 1, x: [0, -3, 3, -2, 2, 0] }}
      transition={{ duration: 0.45, ease: 'easeOut' }}
      className={cn(
        'flex flex-col items-center text-center p-6 md:p-8',
        className,
      )}
    >
      <div className="flex size-12 items-center justify-center rounded-2xl bg-[hsl(var(--danger)/0.1)] text-[hsl(var(--danger))]">
        <AlertTriangle className="size-6" aria-hidden="true" />
      </div>

      <p className="mt-4 max-w-xs text-sm text-[color:var(--muted-ink)]">
        {message}
      </p>

      {code != null && (
        <span className="mt-2 inline-block rounded-md bg-[color:var(--panel)] px-2 py-0.5 text-xs text-[color:var(--muted-ink)] border border-[color:var(--line)]">
          Code: {code}
        </span>
      )}

      {onRetry && (
        <div className="mt-4">
          <Button variant="secondary" size="sm" onClick={onRetry}>
            Retry
          </Button>
        </div>
      )}
    </motion.div>
  )
}
