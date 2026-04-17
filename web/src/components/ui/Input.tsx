'use client'

import { forwardRef, useId } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const inputVariants = cva(
  'w-full rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] text-[color:var(--ink)] placeholder:text-[color:var(--muted-ink)] transition-all focus:border-[color:var(--accent)] focus:outline-none focus:ring-2 focus:ring-[color:var(--accent)] disabled:cursor-not-allowed disabled:opacity-50',
  {
    variants: {
      size: {
        sm: 'min-h-[32px] text-xs px-2.5 py-1.5',
        md: 'min-h-[40px] text-sm px-3.5 py-2.5',
        lg: 'min-h-[48px] text-base px-4 py-3',
      },
    },
    defaultVariants: {
      size: 'md',
    },
  }
)

const iconPadding = {
  left: { sm: 'pl-8', md: 'pl-10', lg: 'pl-11' },
  right: { sm: 'pr-8', md: 'pr-10', lg: 'pr-11' },
} as const

const iconSize = {
  sm: 'h-3.5 w-3.5',
  md: 'h-4 w-4',
  lg: 'h-5 w-5',
} as const

export interface InputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'>,
    VariantProps<typeof inputVariants> {
  label?: string
  error?: string
  helperText?: string
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      size = 'md',
      label,
      error,
      helperText,
      leftIcon,
      rightIcon,
      id: idProp,
      ...props
    },
    ref
  ) => {
    const autoId = useId()
    const id = idProp ?? autoId
    const s = size ?? 'md'

    return (
      <div className="space-y-1.5">
        {label && (
          <label
            htmlFor={id}
            className="block text-sm font-medium text-[color:var(--ink)]"
          >
            {label}
          </label>
        )}

        <div className="relative">
          {leftIcon && (
            <span
              className={cn(
                'pointer-events-none absolute inset-y-0 left-3 flex items-center text-[color:var(--muted-ink)]',
                iconSize[s]
              )}
            >
              {leftIcon}
            </span>
          )}

          <input
            ref={ref}
            id={id}
            aria-invalid={!!error || undefined}
            aria-describedby={
              error ? `${id}-error` : helperText ? `${id}-helper` : undefined
            }
            className={cn(
              inputVariants({ size }),
              leftIcon && iconPadding.left[s],
              rightIcon && iconPadding.right[s],
              error &&
                'border-[hsl(var(--danger))] focus:border-[hsl(var(--danger))] focus:ring-[hsl(var(--danger))]',
              className
            )}
            {...props}
          />

          {rightIcon && (
            <span
              className={cn(
                'pointer-events-none absolute inset-y-0 right-3 flex items-center text-[color:var(--muted-ink)]',
                iconSize[s]
              )}
            >
              {rightIcon}
            </span>
          )}
        </div>

        {error && (
          <p id={`${id}-error`} className="text-xs text-[hsl(var(--danger))] mt-1" role="alert">
            {error}
          </p>
        )}
        {!error && helperText && (
          <p id={`${id}-helper`} className="text-xs text-[color:var(--muted-ink)] mt-1">
            {helperText}
          </p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'

export { inputVariants }
