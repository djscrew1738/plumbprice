'use client'

import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition-all duration-150 disabled:pointer-events-none disabled:opacity-40',
  {
    variants: {
      variant: {
        primary:
          'bg-[color:var(--accent)] text-white hover:bg-[color:var(--accent-strong)] active:bg-[color:var(--accent-strong)] shadow-[0_6px_14px_rgba(183,96,43,0.25)]',
        secondary:
          'bg-[color:var(--panel)] text-[color:var(--ink)] border border-[color:var(--line)] hover:bg-[color:var(--panel-strong)] active:bg-[color:var(--panel-strong)]',
        ghost:
          'bg-transparent text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]',
        danger:
          'bg-red-500/10 text-red-600 hover:bg-red-500/20 border border-red-500/20',
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
      {...props}
    >
      {isLoading ? (
        <>
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
          <span>Loading...</span>
        </>
      ) : (
        children
      )}
    </button>
  )
}
