'use client'

import { forwardRef, type ElementType, type ComponentPropsWithoutRef, type ReactNode } from 'react'
import { motion, type HTMLMotionProps } from 'framer-motion'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'
import { useReducedMotion } from '@/lib/useReducedMotion'

const cardVariants = cva(
  'relative overflow-hidden transition-colors',
  {
    variants: {
      variant: {
        default:
          'rounded-[var(--radius-lg)] border border-[color:var(--line)] bg-[color:var(--panel-solid)]',
        strong:
          'rounded-[var(--radius-lg)] border border-[color:var(--line-strong)] bg-[color:var(--panel-strong)]',
        panel:
          'rounded-[var(--radius-xl)] border border-[color:var(--line)] bg-[color:var(--panel)]',
        inset:
          'rounded-[var(--radius-md)] border border-[color:var(--line-subtle)] bg-[color:var(--panel-strong)]',
        glass:
          'rounded-[var(--radius-lg)] border border-[color:var(--line)] bg-[color:var(--panel-solid)]/70 backdrop-blur-xl',
        tonal:
          'rounded-[var(--radius-lg)] border bg-[color:var(--panel-solid)]',
      },
      size: {
        sm: 'rounded-[var(--radius-md)]',
        md: 'rounded-[var(--radius-lg)]',
        lg: 'rounded-[var(--radius-xl)]',
      },
      padding: {
        none: 'p-0',
        sm: 'p-3',
        md: 'p-4 sm:p-5',
        lg: 'p-5 sm:p-6',
      },
      elevation: {
        none: '',
        sm: '[box-shadow:var(--shadow-sm)]',
        md: '[box-shadow:var(--shadow-md)]',
        lg: '[box-shadow:var(--shadow-lg)]',
        xl: '[box-shadow:var(--shadow-xl)]',
      },
      tone: {
        default: 'border-[color:var(--line)]',
        accent: 'border-[color:var(--accent)]/30 bg-[color:var(--accent-soft)]/30',
        success: 'border-emerald-500/30 bg-emerald-50/50 dark:border-emerald-400/30 dark:bg-emerald-950/30',
        warning: 'border-amber-500/30 bg-amber-50/50 dark:border-amber-400/30 dark:bg-amber-950/30',
        danger: 'border-red-500/30 bg-red-50/50 dark:border-red-400/30 dark:bg-red-950/30',
        info: 'border-sky-500/30 bg-sky-50/50 dark:border-sky-400/30 dark:bg-sky-950/30',
      },
      interactive: {
        true: 'cursor-pointer select-none',
        false: '',
      },
    },
    compoundVariants: [
      {
        variant: 'tonal',
        tone: 'default',
        className: 'border-[color:var(--line)]',
      },
      {
        variant: 'default',
        elevation: 'md',
        className: '[box-shadow:var(--shadow-md)]',
      },
      {
        variant: 'panel',
        elevation: 'md',
        className: '[box-shadow:var(--shadow-lg)]',
      },
    ],
    defaultVariants: {
      variant: 'default',
      size: 'md',
      padding: 'md',
      elevation: 'none',
      tone: 'default',
      interactive: false,
    },
  }
)

export interface CardProps
  extends Omit<HTMLMotionProps<'div'>, 'color'>,
    VariantProps<typeof cardVariants> {
  as?: ElementType
  children?: ReactNode
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      className,
      variant,
      size,
      padding,
      elevation,
      tone,
      interactive,
      as,
      children,
      ...props
    },
    ref
  ) => {
    const reduceMotion = useReducedMotion()
    const classes = cn(cardVariants({ variant, size, padding, elevation, tone, interactive }), className)

    if (interactive) {
      return (
        <motion.div
          ref={ref as React.Ref<HTMLDivElement>}
          className={classes}
          whileHover={reduceMotion ? undefined : { y: -2, boxShadow: 'var(--shadow-lg)' }}
          whileTap={reduceMotion ? undefined : { scale: 0.995 }}
          transition={{ type: 'spring', stiffness: 400, damping: 30 }}
          {...props}
        >
          {children}
        </motion.div>
      )
    }

    const Component = as || 'div'
    return (
      <Component ref={ref as React.Ref<HTMLDivElement>} className={classes} {...props}>
        {children}
      </Component>
    )
  }
)
Card.displayName = 'Card'

type CardWithSubcomponents = typeof Card & {
  Header: typeof CardHeader
  Body: typeof CardBody
  Footer: typeof CardFooter
  Title: typeof CardTitle
  Description: typeof CardDescription
  Actions: typeof CardActions
  Media: typeof CardMedia
}

// ---------------------------------------------------------------------------
// Layout subcomponents
// ---------------------------------------------------------------------------

export interface CardHeaderProps extends ComponentPropsWithoutRef<'div'> {
  separated?: boolean
}

export function CardHeader({ className, separated, ...props }: CardHeaderProps) {
  return (
    <div
      className={cn(
        'flex items-start justify-between gap-3',
        separated && 'border-b border-[color:var(--line)] pb-4 mb-4',
        className
      )}
      {...props}
    />
  )
}

export function CardBody({ className, ...props }: ComponentPropsWithoutRef<'div'>) {
  return <div className={cn('flex-1', className)} {...props} />
}

export interface CardFooterProps extends ComponentPropsWithoutRef<'div'> {
  separated?: boolean
}

export function CardFooter({ className, separated, ...props }: CardFooterProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-between gap-3',
        separated && 'border-t border-[color:var(--line)] pt-4 mt-4',
        className
      )}
      {...props}
    />
  )
}

export function CardTitle({ className, children, ...props }: ComponentPropsWithoutRef<'h3'>) {
  return (
    <h3
      className={cn('text-sm font-semibold text-[color:var(--ink)] sm:text-base', className)}
      {...props}
    >
      {children}
    </h3>
  )
}

export function CardDescription({ className, children, ...props }: ComponentPropsWithoutRef<'p'>) {
  return (
    <p
      className={cn('text-xs text-[color:var(--muted-ink)] sm:text-sm', className)}
      {...props}
    >
      {children}
    </p>
  )
}

export function CardActions({ className, ...props }: ComponentPropsWithoutRef<'div'>) {
  return <div className={cn('ml-auto flex items-center gap-2', className)} {...props} />
}

export function CardMedia({ className, ...props }: ComponentPropsWithoutRef<'div'>) {
  return <div className={cn('-mx-5 -mt-5 sm:-mx-6 sm:-mt-6', className)} {...props} />
}

const CardWithSubcomponents = Object.assign(Card, {
  Header: CardHeader,
  Body: CardBody,
  Footer: CardFooter,
  Title: CardTitle,
  Description: CardDescription,
  Actions: CardActions,
  Media: CardMedia,
}) as CardWithSubcomponents

export { CardWithSubcomponents as Card }
