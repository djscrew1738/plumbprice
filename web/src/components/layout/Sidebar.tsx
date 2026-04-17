'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { AnimatePresence, motion } from 'framer-motion'
import { Keyboard, X } from 'lucide-react'
import { PRIMARY_NAV, SECONDARY_NAV, matchesPathname } from './nav'
import { RecentJobsList } from '@/components/workspace/RecentJobsList'
import { Tooltip } from '@/components/ui/Tooltip'

function SidebarContent({ onClose, showRecentRail = false }: { onClose?: () => void; showRecentRail?: boolean }) {
  const pathname = usePathname()

  const openShortcuts = () => window.dispatchEvent(new Event('show-shortcuts'))

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex h-[72px] items-center justify-between border-b border-[color:var(--line)] px-4">
        <div>
          <p className="text-[11px] font-bold text-[color:var(--accent-strong)]">
            PlumbPrice AI
          </p>
          <p className="text-sm font-bold text-[color:var(--ink)]">Estimator Dashboard</p>
        </div>
        {onClose && (
          <button onClick={onClose} className="rounded-[1rem] p-2 text-[color:var(--muted-ink)] lg:hidden" aria-label="Close navigation">
            <X size={16} aria-hidden="true" />
          </button>
        )}
      </div>
      <div className="flex min-h-0 flex-1 flex-col">
        <nav aria-label="Sidebar" className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
          <div className="space-y-1">
            <p className="px-3 text-[11px] font-bold text-[color:var(--muted-ink)]">
              Workspace
            </p>
            {PRIMARY_NAV.map(({ href, icon: Icon, label }) => {
              const active = matchesPathname(pathname, href)

              return (
                <Link
                  key={href}
                  href={href}
                  onClick={onClose}
                  aria-current={active ? 'page' : undefined}
                  className={`flex items-center gap-3 rounded-[1.25rem] px-3 py-3 text-sm font-medium transition-colors ${
                    active
                      ? 'bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]'
                      : 'text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]'
                  }`}
                >
                  <Icon size={16} aria-hidden="true" />
                  <span>{label}</span>
                </Link>
              )
            })}
          </div>
          <div className="space-y-1">
            <p className="px-3 text-[11px] font-bold text-[color:var(--muted-ink)]">
              Utilities
            </p>
            {SECONDARY_NAV.map(({ href, icon: Icon, label }) => {
              const active = matchesPathname(pathname, href)

              return (
                <Link
                  key={href}
                  href={href}
                  onClick={onClose}
                  aria-current={active ? 'page' : undefined}
                  className={`flex items-center gap-3 rounded-[1.25rem] px-3 py-3 text-sm font-medium transition-colors ${
                    active
                      ? 'bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]'
                      : 'text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]'
                  }`}
                >
                  <Icon size={16} aria-hidden="true" />
                  <span>{label}</span>
                </Link>
              )
            })}
          </div>
        </nav>

        {showRecentRail && (
          <div className="border-t border-[color:var(--line)] px-3 py-4">
            <RecentJobsList compact limit={4} />
          </div>
        )}

        {/* Keyboard shortcut hint */}
        <div className="border-t border-[color:var(--line)] px-3 py-3">
          <Tooltip content="View keyboard shortcuts" side="right">
            <button
              onClick={openShortcuts}
              className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-xs text-[color:var(--muted-ink)] transition-colors hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]"
              aria-label="View keyboard shortcuts"
            >
              <Keyboard size={13} aria-hidden="true" />
              <span>Keyboard shortcuts</span>
              <kbd className="ml-auto rounded border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-1.5 py-0.5 font-mono text-[10px]">?</kbd>
            </button>
          </Tooltip>
        </div>
      </div>
    </div>
  )
}

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <>
      <aside
        aria-label="Main navigation"
        className="hidden lg:flex fixed inset-y-0 left-0 w-[var(--sidebar-width,248px)] bg-[color:var(--panel)] border-r border-[color:var(--line)] z-40 flex-col"
      >
        <SidebarContent showRecentRail />
      </aside>

      <AnimatePresence>
        {open && (
          <motion.aside
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 320 }}
            aria-label="Main navigation"
            className="fixed inset-y-0 left-0 w-[var(--sidebar-width,248px)] bg-[color:var(--panel)] border-r border-[color:var(--line)] z-40 flex flex-col lg:hidden"
            style={{ paddingTop: 'env(safe-area-inset-top)' }}
          >
            <SidebarContent onClose={onClose} />
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  )
}
