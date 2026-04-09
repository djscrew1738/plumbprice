'use client'

import { usePathname } from 'next/navigation'
import { Menu, MapPin } from 'lucide-react'
import { getPageMeta } from './nav'
import { ThemeToggle } from './ThemeToggle'
import { useAuth } from '@/contexts/AuthContext'

function getUserInitials(name: string | undefined, email: string | undefined): string {
  if (name) {
    const parts = name.trim().split(/\s+/)
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    return parts[0].slice(0, 2).toUpperCase()
  }
  if (email) return email[0].toUpperCase()
  return '?'
}

export function Header({ onMenuClick }: { onMenuClick: () => void }) {
  const pathname = usePathname()
  const meta = getPageMeta(pathname)
  const { user } = useAuth()
  const initials = getUserInitials(user?.full_name, user?.email)
  const displayName = user?.full_name ?? user?.email ?? 'User'

  return (
    <header
      className="sticky top-0 z-20 border-b border-[color:var(--line)] bg-[color:var(--panel)]/95 backdrop-blur-xl"
      style={{ paddingTop: 'env(safe-area-inset-top)' }}
    >
      <div className="flex h-[68px] items-center gap-3 px-4">
        <button
          onClick={onMenuClick}
          className="rounded-[1rem] p-2 text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] lg:hidden"
          aria-label="Open navigation"
        >
          <Menu size={18} />
        </button>
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">
            {meta.eyebrow}
          </p>
          <h1 className="truncate text-lg font-semibold text-[color:var(--ink)]">{meta.title}</h1>
        </div>
        <div className="hidden items-center gap-2 rounded-full border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 py-1.5 sm:flex">
          <MapPin size={12} className="text-[color:var(--accent-strong)]" />
          <span className="text-xs font-medium text-[color:var(--muted-ink)]">DFW</span>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <button
            title={displayName}
            aria-label={`Signed in as ${displayName}`}
            className="flex size-9 items-center justify-center rounded-full bg-[color:var(--accent-soft)] text-sm font-semibold text-[color:var(--accent-strong)] cursor-default select-none"
          >
            {initials}
          </button>
        </div>
      </div>
    </header>
  )
}
