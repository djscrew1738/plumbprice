import { type HTMLAttributes, type ReactNode, forwardRef } from 'react'
import { cn } from '@/lib/utils'

type Width = 'narrow' | 'default' | 'wide' | 'full'

const widthClass: Record<Width, string> = {
  narrow: 'max-w-[720px]',
  default: 'max-w-[var(--content-max-width)]',
  wide: 'max-w-[1440px]',
  full: 'max-w-none',
}

export interface PageShellProps extends HTMLAttributes<HTMLElement> {
  /** Container max-width. Defaults to the global content max-width. */
  width?: Width
  /** Render as `<div>` instead of `<main>`. Used for nested shells. */
  asDiv?: boolean
  /** Disable horizontal padding (full-bleed pages like the estimator). */
  bleed?: boolean
  children: ReactNode
}

/**
 * Top-level page wrapper. Provides consistent max-width, horizontal padding,
 * vertical rhythm, and safe-area handling. Use this on every page so density
 * stays consistent across the app.
 */
export const PageShell = forwardRef<HTMLElement, PageShellProps>(function PageShell(
  { className, width = 'default', asDiv, bleed, children, ...rest },
  ref,
) {
  const Comp: 'main' | 'div' = asDiv ? 'div' : 'main'
  return (
    <Comp
      ref={ref as never}
      className={cn(
        'mx-auto w-full',
        widthClass[width],
        !bleed && 'px-[var(--space-page-x)]',
        'py-[var(--space-page-y)]',
        className,
      )}
      {...rest}
    >
      {children}
    </Comp>
  )
})
