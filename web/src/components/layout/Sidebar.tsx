'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { PRIMARY_NAV, SECONDARY_NAV, matchesPathname } from './nav'
import { RecentJobsList } from '@/components/workspace/RecentJobsList'

function SidebarContent({ onClose, showRecentRail = false }: { onClose?: () => void; showRecentRail?: boolean }) {
  const pathname = usePathname()

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex h-[72px] items-center justify-between border-b border-[color:var(--line)] px-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">
            PlumbPrice AI
          </p>
          <p className="text-sm font-semibold text-[color:var(--ink)]">Field Pricing Shell</p>
        </div>
        {onClose && (
          <button onClick={onClose} className="rounded-[1rem] p-2 text-[color:var(--muted-ink)] lg:hidden">
            <X size={16} />
          </button>
        )}
      </div>
      <div className="flex min-h-0 flex-1 flex-col">
        <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
          <div className="space-y-1">
            <p className="px-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">
              Workspace
            </p>
            {PRIMARY_NAV.map(({ href, icon: Icon, label }) => {
              const active = matchesPathname(pathname, href)

              return (
                <Link
                  key={href}
                  href={href}
                  onClick={onClose}
                  className={`flex items-center gap-3 rounded-[1.25rem] px-3 py-3 text-sm font-medium transition-colors ${
                    active
                      ? 'bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]'
                      : 'text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]'
                  }`}
                >
                  <Icon size={16} />
                  <span>{label}</span>
                </Link>
              )
            })}
          </div>
          <div className="space-y-1">
            <p className="px-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">
              Utilities
            </p>
            {SECONDARY_NAV.map(({ href, icon: Icon, label }) => {
              const active = matchesPathname(pathname, href)

              return (
                <Link
                  key={href}
                  href={href}
                  onClick={onClose}
                  className={`flex items-center gap-3 rounded-[1.25rem] px-3 py-3 text-sm font-medium transition-colors ${
                    active
                      ? 'bg-[color:var(--panel-strong)] text-[color:var(--ink)]'
                      : 'text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]'
                  }`}
                >
                  <Icon size={16} />
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
      </div>
    </div>
  )
}

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <>
      <aside
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
