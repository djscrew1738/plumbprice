'use client'

import React from 'react'
import { motion, type HTMLMotionProps } from 'framer-motion'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'
import { useReducedMotion } from '@/lib/useReducedMotion'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition-all disabled:pointer-events-none disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-[color:var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--canvas)] outline-none',
  {
    variants: {
      variant: {
        primary:
          'min-h-[40px] bg-gradient-to-br from-[color:var(--accent)] to-[color:var(--accent-strong)] text-white [box-shadow:var(--shadow-md)] hover:[box-shadow:var(--shadow-lg)] active:scale-[0.98]',
        secondary:
          'min-h-[40px] bg-[color:var(--panel)] text-[color:var(--ink)] border border-[color:var(--line)] hover:bg-[color:var(--panel-strong)] active:bg-[color:var(--panel-strong)] active:scale-[0.98]',
        ghost:
          'bg-transparent text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]',
        danger:
          'min-h-[40px] bg-[color:var(--danger-soft)] text-[color:var(--danger)] hover:bg-[hsl(var(--danger)/0.2)] border border-[hsl(var(--danger)/0.2)] active:scale-[0.98]',
        success:
          'min-h-[40px] bg-[color:var(--success-soft)] text-[color:var(--success)] hover:bg-[hsl(var(--success-hsl)/0.2)] border border-[hsl(var(--success-hsl)/0.2)] active:scale-[0.98]',
        warning:
          'min-h-[40px] bg-[color:var(--warning-soft)] text-[color:var(--warning)] hover:bg-[hsl(var(--warning-hsl)/0.2)] border border-[hsl(var(--warning-hsl)/0.2)] active:scale-[0.98]',
        neutral:
          'min-h-[40px] bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)] border border-[color:var(--line)] hover:bg-[color:var(--panel)] hover:text-[color:var(--ink)] active:scale-[0.98]',
      },
      size: {
        xs: 'px-2.5 py-1 text-[11px] gap-1.5 rounded-lg',
        sm: 'px-3 py-1.5 text-xs',
        md: 'px-4 py-2.5 text-sm',
        lg: 'px-6 py-3 text-base',
        icon: 'p-2',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
)

export interface ButtonProps extends HTMLMotionProps<'button'>, VariantProps<typeof buttonVariants> {
  isLoading?: boolean
}

export function ButtonImpl({
  className,
  variant,
  size,
  isLoading,
  disabled,
  children,
  type = 'button',
  ...props
}: ButtonProps) {
  const reduce = useReducedMotion()
  const isDisabled = disabled || isLoading

  return (
    <motion.button
      type={type}
      className={cn(buttonVariants({ variant, size, className }))}
      disabled={isDisabled}
      aria-busy={isLoading || undefined}
      whileTap={reduce || isDisabled ? undefined : { scale: 0.98 }}
      transition={{ type: 'spring', damping: 28, stiffness: 320 }}
      {...props}
    >
      {isLoading ? (
        <motion.span
          key="loading"
          initial={reduce ? {} : { opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={reduce ? {} : { opacity: 0, y: -4 }}
          transition={{ duration: 0.15 }}
          className="inline-flex items-center gap-2"
        >
          <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span>Loading…</span>
        </motion.span>
      ) : (
        <motion.span
          key="content"
          initial={reduce ? {} : { opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={reduce ? {} : { opacity: 0, y: 4 }}
          transition={{ duration: 0.15 }}
        >
          {children}
        </motion.span>
      )}
    </motion.button>
  )
}

// Memo prevents re-renders when the parent re-renders with identical props.
const Button = React.memo(ButtonImpl)
Button.displayName = 'Button'
export { Button, buttonVariants }
