'use client'

import { useState, useRef, useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Menu, MapPin, LogOut, Settings, ChevronRight } from 'lucide-react'
import { getPageMeta, PAGE_META } from './nav'
import { ThemeToggle } from './ThemeToggle'
import { NotificationBell } from './NotificationBell'
import { useAuth } from '@/contexts/AuthContext'
import { Tooltip } from '@/components/ui/Tooltip'

function getUserInitials(name: string | undefined, email: string | undefined): string {
  if (name) {
    const parts = name.trim().split(/\s+/)
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    return parts[0].slice(0, 2).toUpperCase()
  }
  if (email) return email[0].toUpperCase()
  return '?'
}

function buildBreadcrumb(pathname: string): { label: string; href: string }[] {
  const crumbs: { label: string; href: string }[] = [{ label: 'Home', href: '/' }]
  if (pathname === '/' || pathname === '') return crumbs

  const segments = pathname.split('/').filter(Boolean)
  let accumulated = ''
  for (const seg of segments) {
    accumulated += '/' + seg
    const meta = PAGE_META[accumulated]
    crumbs.push({
      label: meta?.title ?? seg.charAt(0).toUpperCase() + seg.slice(1),
      href: accumulated,
    })
  }
  return crumbs
}

export function Header({ onMenuClick }: { onMenuClick: () => void }) {
  const pathname = usePathname()
  const router = useRouter()
  const meta = getPageMeta(pathname)
  const { user, logout } = useAuth()
  const initials = getUserInitials(user?.full_name, user?.email)
  const displayName = user?.full_name ?? user?.email ?? 'User'
  const breadcrumb = buildBreadcrumb(pathname)

  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Close dropdown on outside click
  useEffect(() => {
    if (!menuOpen) return
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [menuOpen])

  // Close on Escape and handle arrow key navigation
  useEffect(() => {
    if (!menuOpen) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setMenuOpen(false)
        return
      }
      if (!menuRef.current) return
      const items = Array.from(
        menuRef.current.querySelectorAll<HTMLElement>('[role="menuitem"]'),
      )
      if (items.length === 0) return
      const idx = items.indexOf(document.activeElement as HTMLElement)
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        items[Math.min(idx + 1, items.length - 1)]?.focus()
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        items[Math.max(idx - 1, 0)]?.focus()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [menuOpen])

  const handleLogout = () => {
    setMenuOpen(false)
    logout()
    router.push('/login')
  }

  return (
    <header
      className="sticky top-0 z-20 border-b border-[color:var(--line)] bg-[color:var(--panel)]/95 backdrop-blur-xl"
      style={{ paddingTop: 'env(safe-area-inset-top)' }}
    >
      <div className="flex h-[var(--header-height)] items-center gap-3 px-4">
        <button
          onClick={onMenuClick}
          className="rounded-[1rem] p-2 text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] lg:hidden"
          aria-label="Open navigation"
        >
          <Menu size={18} aria-hidden="true" />
        </button>
        <div className="min-w-0 flex-1">
          <Link href="/" className="group inline-block">
            <p className="text-[11px] font-bold text-[color:var(--accent-strong)] transition-colors group-hover:text-[color:var(--accent-strong)]">
              PlumbPrice AI
            </p>
            <h1 className="truncate text-lg font-bold text-[color:var(--ink)] group-hover:text-[color:var(--accent-strong)] transition-colors">
              {meta.title}
            </h1>
          </Link>
          {breadcrumb.length > 1 && (
            <nav aria-label="Breadcrumb" className="hidden sm:flex items-center gap-1 mt-0.5">
              {breadcrumb.map((crumb, i) => (
                <span key={crumb.href} className="flex items-center gap-1">
                  {i > 0 && <ChevronRight size={10} className="text-[color:var(--muted-ink)] opacity-50" aria-hidden="true" />}
                  {i < breadcrumb.length - 1 ? (
                    <Link
                      href={crumb.href}
                      className="text-[10px] text-[color:var(--muted-ink)] hover:text-[color:var(--accent-strong)] transition-colors"
                    >
                      {crumb.label}
                    </Link>
                  ) : (
                    <span className="text-[10px] font-medium text-[color:var(--muted-ink)]">
                      {crumb.label}
                    </span>
                  )}
                </span>
              ))}
            </nav>
          )}
        </div>
        <Tooltip content="Dallas-Fort Worth metro area">
          <div
            className="hidden items-center gap-2 rounded-full border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 py-1.5 sm:flex"
          >
            <MapPin size={12} className="text-[color:var(--accent-strong)]" aria-hidden="true" />
            <span className="text-xs font-medium text-[color:var(--muted-ink)]">DFW</span>
          </div>
        </Tooltip>
        <div className="flex items-center gap-2">
          <NotificationBell />
          <ThemeToggle />
          <div className="relative" ref={menuRef}>
            <Tooltip content={displayName}>
              <button
                onClick={() => setMenuOpen(prev => !prev)}
                aria-label={`Signed in as ${displayName}`}
                aria-expanded={menuOpen}
                aria-haspopup="true"
                className="flex size-9 items-center justify-center rounded-full bg-[color:var(--accent-soft)] text-sm font-semibold text-[color:var(--accent-strong)] cursor-pointer select-none transition-colors hover:bg-[color:var(--accent-strong)] hover:text-white"
              >
                {initials}
              </button>
            </Tooltip>
            {menuOpen && (
              <div role="menu" aria-label="User menu" className="absolute right-0 top-full mt-2 w-56 rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] shadow-lg overflow-hidden z-50">
                <div className="border-b border-[color:var(--line)] px-4 py-3">
                  <p className="text-sm font-semibold text-[color:var(--ink)] truncate">{displayName}</p>
                  {user?.email && (
                    <p className="text-xs text-[color:var(--muted-ink)] truncate">{user.email}</p>
                  )}
                  {user?.role && (
                    <span className="mt-1 inline-block rounded-full bg-[color:var(--accent-soft)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[color:var(--accent-strong)]">
                      {user.role}
                    </span>
                  )}
                </div>
                <div className="py-1">
                  <Link
                    href="/admin"
                    role="menuitem"
                    tabIndex={0}
                    onClick={() => setMenuOpen(false)}
                    className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-[color:var(--ink)] transition-colors hover:bg-[color:var(--panel-strong)]"
                  >
                    <Settings size={15} aria-hidden="true" />
                    <span>Settings</span>
                  </Link>
                  <button
                    role="menuitem"
                    tabIndex={0}
                    onClick={handleLogout}
                    className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-red-500 transition-colors hover:bg-red-50 dark:hover:bg-red-500/10"
                  >
                    <LogOut size={15} aria-hidden="true" />
                    <span>Sign out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
