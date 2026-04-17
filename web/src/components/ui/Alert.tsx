'use client'

import { type ReactNode } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import {
  AlertCircle,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  X,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'

/* ------------------------------------------------------------------ */
/*  Variant styles (CVA)                                               */
/* ------------------------------------------------------------------ */

const alertVariants = cva(
  'relative flex items-start gap-3 rounded-xl border px-4 py-3',
  {
    variants: {
      variant: {
        info: 'bg-[hsl(var(--info)/0.08)] border-[hsl(var(--info)/0.2)] text-[hsl(var(--info))]',
        success:
          'bg-[hsl(var(--success)/0.08)] border-[hsl(var(--success)/0.2)] text-[hsl(var(--success))]',
        warning:
          'bg-[hsl(var(--warning)/0.08)] border-[hsl(var(--warning)/0.2)] text-[hsl(var(--warning-foreground))]',
        error:
          'bg-[hsl(var(--danger)/0.08)] border-[hsl(var(--danger)/0.2)] text-[hsl(var(--danger))]',
      },
    },
    defaultVariants: {
      variant: 'info',
    },
  },
)

/* ------------------------------------------------------------------ */
/*  Default icons per variant                                          */
/* ------------------------------------------------------------------ */

const DEFAULT_ICONS: Record<NonNullable<AlertVariant>, LucideIcon> = {
  info: AlertCircle,
  success: CheckCircle2,
  warning: AlertTriangle,
  error: XCircle,
}

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type AlertVariant = VariantProps<typeof alertVariants>['variant']

export interface AlertProps extends VariantProps<typeof alertVariants> {
  title: string
  description?: ReactNode
  dismissible?: boolean
  onDismiss?: () => void
  icon?: LucideIcon
  className?: string
  action?: ReactNode
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function Alert({
  variant = 'info',
  title,
  description,
  dismissible = false,
  onDismiss,
  icon,
  className,
  action,
}: AlertProps) {
  const Icon = icon ?? DEFAULT_ICONS[variant ?? 'info']

  return (
    <div
      role="alert"
      className={cn(alertVariants({ variant }), className)}
    >
      {/* Icon */}
      <Icon size={18} className="shrink-0 mt-0.5" aria-hidden="true" />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold leading-snug">{title}</p>
        {description && (
          <p className="mt-1 text-sm opacity-80 leading-relaxed">{description}</p>
        )}
        {action && <div className="mt-2">{action}</div>}
      </div>

      {/* Dismiss button */}
      {dismissible && (
        <button
          type="button"
          onClick={onDismiss}
          className="shrink-0 rounded-lg p-1 opacity-60 hover:opacity-100 transition-opacity"
          aria-label="Dismiss alert"
        >
          <X size={16} />
        </button>
      )}
    </div>
  )
}

export { alertVariants }
