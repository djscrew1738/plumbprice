'use client'

import { useEffect } from 'react'
import Link from 'next/link'
import { ChevronRight, X, LogOut } from 'lucide-react'
import { MORE_LINKS } from './nav'
import { useFocusTrap, useTrapFocusOutside } from '@/lib/useFocusTrap'
import { useAuth } from '@/contexts/AuthContext'
import { motion, AnimatePresence } from 'framer-motion'
import { haptic } from '@/lib/haptics'
import { Button } from '@/components/ui/Button'

type MoreSheetProps = {
  open: boolean
  onClose: () => void
}

export function MoreSheet({ open, onClose }: MoreSheetProps) {
  const containerRef = useFocusTrap(open)
  useTrapFocusOutside(open, onClose)
  const { user, logout } = useAuth()

  const displayName = user?.full_name ?? user?.email ?? 'User'
  const userInitial = displayName.charAt(0).toUpperCase()

  useEffect(() => {
    if (!open) return
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = previousOverflow
    }
  }, [open, onClose])

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            aria-hidden="true"
            data-testid="more-sheet-overlay"
            className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm lg:hidden"
            onClick={onClose}
          />

          <motion.div
            ref={containerRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="more-sheet-title"
            className="fixed inset-x-0 bottom-0 z-50 flex justify-center px-3 pb-[max(env(safe-area-inset-bottom),12px)] pt-6 lg:hidden"
            style={{ maxHeight: '87dvh' }}
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 32, stiffness: 320 }}
          >
            <div
              className="bottom-sheet flex w-full max-w-md flex-col overflow-hidden"
              style={{ maxHeight: '87dvh' }}
            >
              {/* Handle */}
              <div className="flex items-center justify-center pt-3 pb-1">
                <div className="h-1.5 w-11 rounded-full bg-[color:var(--line)]" />
              </div>

              {/* Header */}
              <div className="flex items-start justify-between gap-4 border-b border-[color:var(--line)] px-5 py-4">
                <div>
                  <p className="text-eyebrow uppercase text-[color:var(--accent-strong)]">
                    PlumbPrice AI
                  </p>
                  <h2 id="more-sheet-title" className="mt-1 text-lg font-semibold text-[color:var(--ink)]">
                    More destinations
                  </h2>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onClose}
                  aria-label="Close more destinations"
                  className="rounded-[1rem]"
                >
                  <X size={18} />
                </Button>
              </div>

              {/* User profile */}
              {user && (
                <div className="flex items-center gap-3 border-b border-[color:var(--line)] px-5 py-4">
                  <div className="flex size-10 items-center justify-center rounded-[1rem] bg-[color:var(--accent-soft)] text-sm font-bold text-[color:var(--accent-strong)]">
                    {userInitial}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-[color:var(--ink)]">{displayName}</p>
                    {user.email && (
                      <p className="truncate text-xs text-[color:var(--muted-ink)]">{user.email}</p>
                    )}
                  </div>
                  {user.role && (
                    <span className="rounded-full bg-[color:var(--accent-soft)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[color:var(--accent-strong)]">
                      {user.role}
                    </span>
                  )}
                </div>
              )}

              {/* Links */}
              <div className="grid gap-2 overflow-y-auto px-4 py-4">
                {MORE_LINKS.map(({ href, icon: Icon, label }) => (
                  <Link
                    key={href}
                    href={href}
                    onClick={() => {
                      haptic('tap')
                      onClose()
                    }}
                    className="flex items-center justify-between rounded-[1.25rem] border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-4 py-3 text-[color:var(--ink)] transition-all hover:bg-[color:var(--accent-soft)] hover:border-[color:var(--accent-soft)] active:scale-[0.99]"
                  >
                    <span className="flex items-center gap-3">
                      <span className="flex size-10 items-center justify-center rounded-[1rem] bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]">
                        <Icon size={18} aria-hidden="true" />
                      </span>
                      <span className="text-sm font-semibold">{label}</span>
                    </span>
                    <ChevronRight size={16} className="text-[color:var(--muted-ink)]" aria-hidden="true" />
                  </Link>
                ))}
              </div>

              {/* Footer actions */}
              <div className="border-t border-[color:var(--line)] px-4 py-3">
                <Button
                  variant="ghost"
                  onClick={() => { onClose(); haptic('warning'); logout(); }}
                  className="flex w-full items-center justify-start gap-3 rounded-[1.25rem] px-4 py-3 text-sm font-medium text-[color:var(--danger)] hover:bg-[color:var(--danger-soft)] hover:text-[color:var(--danger)]"
                >
                  <LogOut size={16} aria-hidden="true" />
                  <span>Sign out</span>
                </Button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
