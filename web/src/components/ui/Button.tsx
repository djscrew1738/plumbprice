'use client'

import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition-all disabled:pointer-events-none disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-[color:var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[hsl(var(--background))] outline-none',
  {
    variants: {
      variant: {
        primary:
          'min-h-[40px] bg-gradient-to-br from-[color:var(--accent)] to-[color:var(--accent-strong)] text-white hover:shadow-[0_6px_18px_hsl(var(--accent-hsl)/0.36)] active:scale-[0.98] shadow-[0_4px_12px_hsl(var(--accent-hsl)/0.28)]',
        secondary:
          'min-h-[40px] bg-[color:var(--panel)] text-[color:var(--ink)] border border-[color:var(--line)] hover:bg-[color:var(--panel-strong)] active:bg-[color:var(--panel-strong)] active:scale-[0.98]',
        ghost:
          'bg-transparent text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]',
        danger:
          'min-h-[40px] bg-[hsl(var(--danger)/0.1)] text-[hsl(var(--danger))] hover:bg-[hsl(var(--danger)/0.2)] border border-[hsl(var(--danger)/0.2)] active:scale-[0.98]',
      },
      size: {
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

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean
}

export function Button({
  className,
  variant,
  size,
  isLoading,
  disabled,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(buttonVariants({ variant, size, className }))}
      disabled={disabled || isLoading}
      aria-busy={isLoading || undefined}
      {...props}
    >
      {isLoading ? (
        <>
          <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span>Loading…</span>
        </>
      ) : (
        children
      )}
    </button>
  )
}

export { buttonVariants }
