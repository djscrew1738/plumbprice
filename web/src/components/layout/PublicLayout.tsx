'use client'

import { type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { Droplets } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card } from '@/components/ui/Card'
import { BrandFooter } from './BrandFooter'

export interface PublicLayoutProps {
  /** Page title shown below the logo. */
  title: string
  /** Optional subtitle shown under the title. */
  subtitle?: string
  children: ReactNode
  /** Extra content rendered below the card (links, footnotes, etc.). */
  footer?: ReactNode
  /** Override default container width. */
  className?: string
  /** Reduce top logo/header spacing for compact flows. */
  compact?: boolean
}

/**
 * Centered public-page shell used for login, password reset, invite accept,
 * and other unauthenticated flows.
 *
 * Provides the gradient background, brand header, and card container so
 * individual auth forms only need to worry about form fields.
 */
export function PublicLayout({
  title,
  subtitle,
  children,
  footer,
  className,
  compact = false,
}: PublicLayoutProps) {
  return (
    <div className="relative flex min-h-dvh items-center justify-center bg-[color:var(--canvas)] p-4">
      {/* Subtle ambient accent glow */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div
          className="absolute left-1/2 top-1/3 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full blur-[120px]"
          style={{
            background:
              'radial-gradient(circle, hsl(var(--accent-hsl) / 0.12) 0%, transparent 70%)',
          }}
        />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className={cn('relative z-10 w-full max-w-sm', className)}
      >
        <div className={cn('flex flex-col items-center text-center', compact ? 'mb-6' : 'mb-8')}>
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-[color:var(--accent)] to-[color:var(--accent-strong)] shadow-[0_4px_20px_var(--accent-glow)]">
            <Droplets size={26} className="text-[color:var(--ink-inverse)]" />
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-[color:var(--ink)]">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-1 text-sm text-[color:var(--muted-ink)]">{subtitle}</p>
          )}
        </div>

        <Card variant="panel" padding="lg">
          {children}
        </Card>

        {footer}

        <BrandFooter className="mt-5" />
      </motion.div>
    </div>
  )
}
