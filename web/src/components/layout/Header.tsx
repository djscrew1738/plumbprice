'use client'

import { useState, useRef, useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Menu, MapPin, LogOut, Settings, ChevronRight, User } from 'lucide-react'
import { getPageMeta, PAGE_META } from './nav'
import { ThemeToggle } from './ThemeToggle'
import { NotificationBell } from './NotificationBell'
import { OutboxBadge } from './OutboxBadge'
import { useAuth } from '@/contexts/AuthContext'
import { Tooltip } from '@/components/ui/Tooltip'
import { Button } from '@/components/ui/Button'
import {
  DropdownMenu,
  DropdownTrigger,
  DropdownContent,
  DropdownItem,
  DropdownSeparator,
} from '@/components/ui/DropdownMenu'

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

  const [scrolled, setScrolled] = useState(false)
  const sentinelRef = useRef<HTMLDivElement>(null)

  // Scroll-aware shadow: use IntersectionObserver on a sentinel at top
  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        setScrolled(!entry.isIntersecting)
      },
      { threshold: 0, rootMargin: '-1px 0px 0px 0px' }
    )
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [])

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  return (
    <>
      {/* Sentinel for scroll detection — placed in document flow before sticky header */}
      <div ref={sentinelRef} className="h-px" aria-hidden="true" />
      <header
        className={`sticky top-0 z-20 border-b border-[color:var(--line)] bg-[color:var(--panel)]/90 backdrop-blur-xl transition-shadow duration-fast ${
          scrolled ? 'shadow-elev-2' : ''
        }`}
        style={{ paddingTop: 'env(safe-area-inset-top)' }}
      >
      <div className="flex h-[var(--header-height)] items-center gap-2 px-3 sm:gap-3 sm:px-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={onMenuClick}
          aria-label="Open navigation"
          className="lg:hidden"
        >
          <Menu size={18} aria-hidden="true" />
        </Button>

        {/* Title + breadcrumb */}
        <div className="min-w-0 flex-1">
          {/* Mobile: just the page title */}
          <h1 className="truncate text-base font-semibold text-[color:var(--ink)] sm:hidden">
            {meta.title}
          </h1>

          {/* sm+: single-line breadcrumb collapsing on overflow */}
          {breadcrumb.length > 1 ? (
            <nav
              aria-label="Breadcrumb"
              className="hidden items-center gap-1.5 sm:flex"
            >
              {breadcrumb.map((crumb, i) => (
                <span key={crumb.href} className="flex min-w-0 items-center gap-1.5">
                  {i > 0 && (
                    <ChevronRight
                      size={12}
                      className="flex-shrink-0 text-[color:var(--muted-ink)] opacity-50"
                      aria-hidden="true"
                    />
                  )}
                  {i < breadcrumb.length - 1 ? (
                    <Link
                      href={crumb.href}
                      className="truncate text-xs font-medium text-[color:var(--muted-ink)] transition-colors hover:text-[color:var(--accent-strong)]"
                    >
                      {crumb.label}
                    </Link>
                  ) : (
                    <span className="truncate text-sm font-semibold text-[color:var(--ink)]">
                      {crumb.label}
                    </span>
                  )}
                </span>
              ))}
            </nav>
          ) : (
            <h1 className="hidden truncate text-lg font-semibold text-[color:var(--ink)] sm:block">
              {meta.title}
            </h1>
          )}
        </div>

        <Tooltip content="Dallas-Fort Worth metro area">
          <div className="hidden items-center gap-2 rounded-full border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 py-1.5 md:flex">
            <MapPin size={12} className="text-[color:var(--accent-strong)]" aria-hidden="true" />
            <span className="text-xs font-medium text-[color:var(--muted-ink)]">DFW</span>
          </div>
        </Tooltip>

        <div className="flex items-center gap-1 sm:gap-2">
          <OutboxBadge />
          <NotificationBell />
          <ThemeToggle />
          <DropdownMenu>
            <Tooltip content={displayName}>
              <DropdownTrigger
                aria-label={`Signed in as ${displayName}`}
                className="flex size-9 items-center justify-center rounded-full bg-[color:var(--accent-soft)] text-sm font-semibold text-[color:var(--accent-strong)] transition-colors hover:bg-[color:var(--accent-strong)] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--canvas)]"
              >
                {initials}
              </DropdownTrigger>
            </Tooltip>
            <DropdownContent align="end" className="w-56 overflow-hidden rounded-2xl">
              <div className="border-b border-[color:var(--line)] px-4 py-3">
                <p className="truncate text-sm font-semibold text-[color:var(--ink)]">{displayName}</p>
                {user?.email && (
                  <p className="truncate text-xs text-[color:var(--muted-ink)]">{user.email}</p>
                )}
                {user?.role && (
                  <span className="mt-1 inline-block rounded-full bg-[color:var(--accent-soft)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[color:var(--accent-strong)]">
                    {user.role}
                  </span>
                )}
              </div>
              <DropdownItem icon={Settings} label="Settings" onClick={() => router.push('/settings')} />
              {user?.role === 'admin' && (
                <DropdownItem icon={User} label="Admin" onClick={() => router.push('/admin')} />
              )}
              <DropdownSeparator />
              <DropdownItem icon={LogOut} label="Sign out" destructive onClick={handleLogout} />
            </DropdownContent>
          </DropdownMenu>
        </div>
      </div>
      </header>
    </>
  )
}
