'use client'

import Link from 'next/link'
import { ArrowRight, type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface PrimaryActionCardProps {
  href: string
  title: string
  description: string
  icon: LucideIcon
  className?: string
}

export function PrimaryActionCard({ href, title, description, icon: Icon, className }: PrimaryActionCardProps) {
  return (
    <Link
      href={href}
      className={cn(
        'group card flex items-center gap-3 p-4 transition-colors hover:bg-[color:var(--panel-strong)]',
        className
      )}
    >
      <span className="flex size-10 items-center justify-center rounded-xl bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]">
        <Icon size={18} />
      </span>
      <div className="min-w-0 flex-1">
        <h3 className="text-base font-semibold text-[color:var(--ink)]">{title}</h3>
        <p className="text-sm text-[color:var(--muted-ink)]">{description}</p>
      </div>
      <ArrowRight size={16} className="text-[color:var(--muted-ink)] transition-transform group-hover:translate-x-0.5" />
    </Link>
  )
}
