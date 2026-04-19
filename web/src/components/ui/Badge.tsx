import { memo } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-full border font-semibold leading-none',
  {
    variants: {
      variant: {
        success:
          'border-[hsl(var(--success)/0.2)] bg-[hsl(var(--success)/0.1)] text-[hsl(var(--success))]',
        warning:
          'border-[hsl(var(--warning)/0.2)] bg-[hsl(var(--warning)/0.1)] text-[hsl(var(--warning-foreground))]',
        danger:
          'border-[hsl(var(--danger)/0.2)] bg-[hsl(var(--danger)/0.1)] text-[hsl(var(--danger))]',
        info: 'border-[hsl(var(--info)/0.2)] bg-[hsl(var(--info)/0.1)] text-[hsl(var(--info))]',
        neutral:
          'border-[color:var(--line)] bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)]',
        accent:
          'border-[color:var(--accent)]/20 bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]',
      },
      size: {
        sm: 'text-[11px] px-2 py-0.5',
        md: 'text-xs px-2.5 py-1',
      },
    },
    defaultVariants: {
      variant: 'neutral',
      size: 'sm',
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  dot?: boolean
}

export const Badge = memo(function Badge({ className, variant, size, dot, role = 'status', children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(badgeVariants({ variant, size, className }))}
      role={role}
      {...props}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />}
      {children}
    </span>
  )
})

export { badgeVariants }
