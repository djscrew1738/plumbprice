'use client'

import { useEffect } from 'react'
import Link from 'next/link'
import { ChevronRight, X } from 'lucide-react'
import { MORE_LINKS } from './nav'
import { useFocusTrap, useTrapFocusOutside } from '@/lib/useFocusTrap'

type MoreSheetProps = {
  open: boolean
  onClose: () => void
}

export function MoreSheet({ open, onClose }: MoreSheetProps) {
  const containerRef = useFocusTrap(open)
  useTrapFocusOutside(open, onClose)

  useEffect(() => {
    if (!open) {
      return
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      }
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
    open ? (
      <>
        <div
          data-focus-trap
          aria-hidden="true"
          data-testid="more-sheet-overlay"
          className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm animate-fade-in lg:hidden"
          onClick={onClose}
        />

        <div
          ref={containerRef}
          data-focus-trap
          role="dialog"
          aria-modal="true"
          aria-labelledby="more-sheet-title"
          className="fixed inset-x-0 bottom-0 z-50 flex justify-center px-3 pb-[max(env(safe-area-inset-bottom),12px)] pt-6 lg:hidden"
          style={{ maxHeight: '87dvh' }}
        >
          <div
            className="bottom-sheet flex w-full max-w-md flex-col overflow-hidden animate-slide-up"
            style={{ maxHeight: '87dvh' }}
          >
            <div className="flex items-center justify-center pt-3 pb-1">
              <div className="h-1.5 w-11 rounded-full bg-[color:var(--line)]" />
            </div>

            <div className="flex items-start justify-between gap-4 border-b border-[color:var(--line)] px-5 py-4">
              <div>
                <p className="text-[11px] font-bold text-[color:var(--accent-strong)]">
                  PlumbPrice AI
                </p>
                <h2 id="more-sheet-title" className="mt-1 text-lg font-semibold text-[color:var(--ink)]">
                  More destinations
                </h2>
              </div>

              <button
                type="button"
                onClick={onClose}
                className="rounded-[1rem] p-2 text-[color:var(--muted-ink)] transition-colors hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]"
                aria-label="Close more destinations"
              >
                <X size={18} />
              </button>
            </div>

            <div className="grid gap-2 overflow-y-auto px-4 py-4">
              {MORE_LINKS.map(({ href, icon: Icon, label }) => (
                <Link
                  key={href}
                  href={href}
                  onClick={onClose}
                  className="flex items-center justify-between rounded-[1.25rem] border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-4 py-3 text-[color:var(--ink)] transition-colors hover:bg-[color:var(--accent-soft)]"
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
          </div>
        </div>
      </>
    ) : null
  )
}
