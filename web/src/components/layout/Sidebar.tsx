'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronsLeft, ChevronsRight, Keyboard, X } from 'lucide-react'
import { PRIMARY_NAV, SECONDARY_NAV, SYSTEM_NAV, matchesPathname } from './nav'
import { RecentJobsList } from '@/components/workspace/RecentJobsList'
import { Tooltip } from '@/components/ui/Tooltip'
import { Button } from '@/components/ui/Button'
import { OWNER_NAME, PRODUCT_VERSION } from '@/lib/branding'
import { useSidebarPinned } from '@/lib/useSidebarPinned'
import { cn } from '@/lib/utils'

/**
 * Sidebar nav row that adapts to collapsed (icon-only) and expanded states.
 * In collapsed state we wrap the icon in a Tooltip so labels are still
 * keyboard-discoverable.
 */
function NavRow({
  href,
  Icon,
  label,
  active,
  collapsed,
  onClick,
}: {
  href: string
  Icon: React.ComponentType<{ size?: number; 'aria-hidden'?: boolean }>
  label: string
  active: boolean
  collapsed: boolean
  onClick?: () => void
}) {
  const inner = (
    <Link
      href={href}
      onClick={onClick}
      aria-current={active ? 'page' : undefined}
      aria-label={collapsed ? label : undefined}
      className={cn(
        'group relative flex items-center gap-3 rounded-[1rem] text-sm font-medium transition-colors',
        collapsed ? 'h-11 w-11 justify-center' : 'px-3 py-2.5',
        active
          ? 'bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]'
          : 'text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]',
      )}
    >
      {active && !collapsed && (
        <span
          aria-hidden="true"
          className="absolute -left-3 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-[color:var(--accent)]"
        />
      )}
      <Icon size={16} aria-hidden />
      {!collapsed && <span className="truncate">{label}</span>}
    </Link>
  )
  return collapsed ? (
    <Tooltip content={label} side="right">
      {inner}
    </Tooltip>
  ) : (
    inner
  )
}

function SidebarContent({
  onClose,
  showRecentRail = false,
  collapsed = false,
  pinned,
  onTogglePin,
}: {
  onClose?: () => void
  showRecentRail?: boolean
  collapsed?: boolean
  pinned?: boolean
  onTogglePin?: () => void
}) {
  const pathname = usePathname()
  const navRef = useRef<HTMLElement>(null)
  const openShortcuts = () => window.dispatchEvent(new Event('show-shortcuts'))

  const handleNavKeyDown = (e: React.KeyboardEvent) => {
    const nav = navRef.current
    if (!nav) return
    const items = Array.from(nav.querySelectorAll<HTMLElement>('a[href], button:not([disabled])'))
    if (items.length === 0) return
    const idx = items.indexOf(document.activeElement as HTMLElement)

    switch (e.key) {
      case 'ArrowDown': {
        e.preventDefault()
        items[(idx + 1) % items.length]?.focus()
        break
      }
      case 'ArrowUp': {
        e.preventDefault()
        items[(idx - 1 + items.length) % items.length]?.focus()
        break
      }
      case 'Home': {
        e.preventDefault()
        items[0]?.focus()
        break
      }
      case 'End': {
        e.preventDefault()
        items[items.length - 1]?.focus()
        break
      }
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Brand */}
      <div
        className={cn(
          'flex h-[var(--header-height)] items-center border-b border-[color:var(--line)]',
          collapsed ? 'justify-center px-2' : 'justify-between px-4',
        )}
      >
        {collapsed ? (
          <Tooltip content="PlumbPrice AI" side="right">
            <Link
              href="/"
              aria-label="PlumbPrice AI home"
              className="flex h-9 w-9 items-center justify-center rounded-[0.85rem] bg-[color:var(--accent-soft)] text-sm font-bold text-[color:var(--accent-strong)]"
            >
              PP
            </Link>
          </Tooltip>
        ) : (
          <Link href="/" className="min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[color:var(--accent-strong)]">
              PlumbPrice AI
            </p>
            <p className="truncate text-sm font-semibold text-[color:var(--ink)]">
              Estimator
            </p>
          </Link>
        )}
        {onClose && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label="Close navigation"
            className="lg:hidden"
          >
            <X size={16} aria-hidden />
          </Button>
        )}
      </div>

      {/* Nav */}
      <div className="flex min-h-0 flex-1 flex-col">
        {/* eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions */}
        <nav
          ref={navRef}
          aria-label="Sidebar"
          onKeyDown={handleNavKeyDown}
          className={cn('flex-1 space-y-5 overflow-y-auto py-4', collapsed ? 'px-2' : 'px-3')}
        >
          <div className="space-y-1">
            {!collapsed && (
              <p className="px-3 text-[10px] font-bold uppercase tracking-[0.12em] text-[color:var(--muted-ink)]">
                Workspace
              </p>
            )}
            {PRIMARY_NAV.map(({ href, icon: Icon, label }) => (
              <NavRow
                key={href}
                href={href}
                Icon={Icon}
                label={label}
                active={matchesPathname(pathname, href)}
                collapsed={collapsed}
                onClick={onClose}
              />
            ))}
          </div>
          <div className="space-y-1">
            {!collapsed && (
              <p className="px-3 text-[10px] font-bold uppercase tracking-[0.12em] text-[color:var(--muted-ink)]">
                Tools
              </p>
            )}
            {SECONDARY_NAV.map(({ href, icon: Icon, label }) => (
              <NavRow
                key={href}
                href={href}
                Icon={Icon}
                label={label}
                active={matchesPathname(pathname, href)}
                collapsed={collapsed}
                onClick={onClose}
              />
            ))}
          </div>

          <div className="space-y-1">
            {!collapsed && (
              <p className="px-3 text-[10px] font-bold uppercase tracking-[0.12em] text-[color:var(--muted-ink)]">
                System
              </p>
            )}
            {SYSTEM_NAV.map(({ href, icon: Icon, label }) => (
              <NavRow
                key={href}
                href={href}
                Icon={Icon}
                label={label}
                active={matchesPathname(pathname, href)}
                collapsed={collapsed}
                onClick={onClose}
              />
            ))}
          </div>
        </nav>

        {showRecentRail && !collapsed && (
          <div className="border-t border-[color:var(--line)] px-3 py-3">
            <RecentJobsList compact limit={4} />
          </div>
        )}

        {/* Footer: pin toggle + shortcuts hint */}
        <div className={cn('border-t border-[color:var(--line)] py-2', collapsed ? 'px-2' : 'px-3')}>
          {onTogglePin && (
            <Tooltip
              content={pinned ? 'Collapse sidebar' : 'Pin sidebar open'}
              side="right"
            >
              <button
                onClick={onTogglePin}
                aria-label={pinned ? 'Collapse sidebar' : 'Pin sidebar open'}
                aria-pressed={pinned}
                className={cn(
                  'flex items-center gap-2 rounded-[0.85rem] text-xs text-[color:var(--muted-ink)] transition-colors hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--accent)]',
                  collapsed ? 'h-11 w-11 justify-center' : 'w-full px-3 py-2',
                )}
              >
                {pinned ? (
                  <ChevronsLeft size={14} aria-hidden />
                ) : (
                  <ChevronsRight size={14} aria-hidden />
                )}
                {!collapsed && <span>{pinned ? 'Collapse' : 'Pin open'}</span>}
              </button>
            </Tooltip>
          )}
          <Tooltip content="View keyboard shortcuts" side="right">
            <button
              onClick={openShortcuts}
              className={cn(
                'flex items-center gap-2 rounded-[0.85rem] text-xs text-[color:var(--muted-ink)] transition-colors hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--accent)]',
                collapsed ? 'h-11 w-11 justify-center' : 'w-full px-3 py-2',
              )}
              aria-label="View keyboard shortcuts"
            >
              <Keyboard size={13} aria-hidden />
              {!collapsed && (
                <>
                  <span>Shortcuts</span>
                  <kbd className="ml-auto rounded border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-1.5 py-0.5 font-mono text-[10px]">
                    ?
                  </kbd>
                </>
              )}
            </button>
          </Tooltip>
          {!collapsed && (
            <p className="mt-1 px-3 text-center text-[10px] leading-tight text-[color:var(--muted-ink)] opacity-60">
              v{PRODUCT_VERSION} · by {OWNER_NAME}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [pinned, setPinned] = useSidebarPinned()
  const [hovering, setHovering] = useState(false)
  const [focused, setFocused] = useState(false)
  const expandedDesktop = pinned || hovering || focused
  const collapsed = !expandedDesktop

  // Expose the current rail width to the rest of the app via a CSS var so
  // `ClientLayout` can offset its main column without re-rendering on every
  // hover. Only the *pinned* width is reflected — hover-expand visually
  // overlays the content rather than pushing it.
  useEffect(() => {
    document.documentElement.style.setProperty(
      '--sidebar-current',
      pinned ? 'var(--sidebar-expanded)' : 'var(--sidebar-rail)'
    )
  }, [pinned])

  return (
    <>
      {/* Desktop rail */}
      <aside
        aria-label="Main navigation"
        onMouseEnter={() => setHovering(true)}
        onMouseLeave={() => setHovering(false)}
        onFocusCapture={() => setFocused(true)}
        onBlurCapture={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget as Node)) setFocused(false)
        }}
        style={{
          width: collapsed ? 'var(--sidebar-rail)' : 'var(--sidebar-expanded)',
          transition: 'width var(--duration-normal) var(--ease-out)',
          boxShadow: !pinned && expandedDesktop ? 'var(--shadow-lg)' : 'none',
        }}
        className="fixed inset-y-0 left-0 z-40 hidden flex-col border-r border-[color:var(--line)] bg-[color:var(--panel)] lg:flex"
      >
        <SidebarContent
          showRecentRail
          collapsed={collapsed}
          pinned={pinned}
          onTogglePin={() => setPinned(!pinned)}
        />
      </aside>

      {/* Mobile drawer */}
      <AnimatePresence>
        {open && (
          <motion.aside
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 320 }}
            aria-label="Main navigation"
            className="fixed inset-y-0 left-0 z-40 flex w-[var(--sidebar-width,248px)] flex-col border-r border-[color:var(--line)] bg-[color:var(--panel)] lg:hidden"
            style={{ paddingTop: 'env(safe-area-inset-top)' }}
          >
            <SidebarContent onClose={onClose} />
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  )
}
