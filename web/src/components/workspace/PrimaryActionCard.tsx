'use client'

import { memo } from 'react'
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

export const PrimaryActionCard = memo(function PrimaryActionCard({ href, title, description, icon: Icon, className }: PrimaryActionCardProps) {
  return (
    <Link
      href={href}
      className={cn(
        'group card relative overflow-hidden flex items-center gap-3 p-5 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:bg-[hsl(var(--panel-hsl)/0.8)]',
        'before:absolute before:inset-0 before:bg-gradient-to-br before:from-[hsl(var(--accent-hsl)/0.15)] before:to-transparent before:opacity-0 before:transition-opacity hover:before:opacity-100',
        className
      )}
    >
      <span className="relative z-10 flex size-12 items-center justify-center rounded-2xl bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)] shadow-sm transition-transform group-hover:scale-110">
        <Icon size={22} />
      </span>
      <div className="relative z-10 min-w-0 flex-1">
        <h3 className="text-base font-bold text-[color:var(--ink)]">{title}</h3>
        <p className="mt-0.5 text-sm leading-snug text-[color:var(--muted-ink)]">{description}</p>
      </div>
      <ArrowRight size={18} className="relative z-10 text-[color:var(--accent)] opacity-0 -translate-x-2 transition-all group-hover:opacity-100 group-hover:translate-x-0" />
    </Link>
  )
})
