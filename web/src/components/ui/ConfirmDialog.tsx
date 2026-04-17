'use client'

import {
  useEffect,
  useRef,
  useId,
  useCallback,
  type ReactNode,
} from 'react'
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface ConfirmDialogProps {
  open: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  description?: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'default' | 'danger'
  isLoading?: boolean
}

/* ------------------------------------------------------------------ */
/*  Focusable-element selector                                         */
/* ------------------------------------------------------------------ */

const FOCUSABLE =
  'a[href],button:not([disabled]),textarea:not([disabled]),input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])'

/* ------------------------------------------------------------------ */
/*  Spinner                                                            */
/* ------------------------------------------------------------------ */

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  isLoading = false,
}: ConfirmDialogProps) {
  const uid = useId()
  const titleId = `${uid}-title`
  const descId = `${uid}-desc`

  const panelRef = useRef<HTMLDivElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)

  /* ---- focus trap: capture + restore ---- */
  useEffect(() => {
    if (!open) return

    previousFocusRef.current = document.activeElement as HTMLElement | null

    const raf = requestAnimationFrame(() => {
      const first = panelRef.current?.querySelector<HTMLElement>(FOCUSABLE)
      first?.focus()
    })

    return () => {
      cancelAnimationFrame(raf)
      previousFocusRef.current?.focus()
    }
  }, [open])

  /* ---- focus trap: keep focus inside panel ---- */
  useEffect(() => {
    if (!open) return

    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== 'Tab' || !panelRef.current) return

      const focusable = Array.from(
        panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE),
      )
      if (focusable.length === 0) return

      const first = focusable[0]
      const last = focusable[focusable.length - 1]

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }

    window.addEventListener('keydown', handleTab)
    return () => window.removeEventListener('keydown', handleTab)
  }, [open])

  /* ---- Escape key ---- */
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isLoading) onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose, isLoading])

  /* ---- lock body scroll ---- */
  useEffect(() => {
    if (!open) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prev
    }
  }, [open])

  const handleBackdropClick = useCallback(() => {
    if (!isLoading) onClose()
  }, [onClose, isLoading])

  if (typeof document === 'undefined') return null

  const confirmBtnClass =
    variant === 'danger'
      ? 'bg-[hsl(var(--danger))] text-white hover:bg-[hsl(var(--danger)/0.9)] focus-visible:ring-[hsl(var(--danger))]'
      : 'bg-gradient-to-br from-[color:var(--accent)] to-[color:var(--accent-strong)] text-white hover:shadow-[0_6px_18px_hsl(var(--accent-hsl)/0.36)] focus-visible:ring-[color:var(--accent)]'

  return createPortal(
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            key="confirm-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm"
            onClick={handleBackdropClick}
            aria-hidden="true"
          />

          {/* Panel */}
          <motion.div
            key="confirm-panel"
            ref={panelRef}
            role="alertdialog"
            aria-modal="true"
            aria-labelledby={titleId}
            aria-describedby={description ? descId : undefined}
            initial={{ opacity: 0, scale: 0.95, y: -12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -12 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className={cn(
              'fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md',
              'bg-[color:var(--panel)] border border-[color:var(--line)] rounded-2xl shadow-2xl',
            )}
          >
            <div className="px-6 pt-6 pb-2">
              <h2
                id={titleId}
                className="text-base font-semibold text-[color:var(--ink)]"
              >
                {title}
              </h2>
              {description && (
                <p
                  id={descId}
                  className="mt-2 text-sm text-[color:var(--muted-ink)] leading-relaxed"
                >
                  {description}
                </p>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 px-6 py-4">
              <button
                type="button"
                onClick={onClose}
                disabled={isLoading}
                className={cn(
                  'inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-semibold transition-all outline-none',
                  'bg-[color:var(--panel)] text-[color:var(--ink)] border border-[color:var(--line)]',
                  'hover:bg-[color:var(--panel-strong)] active:scale-[0.98]',
                  'focus-visible:ring-2 focus-visible:ring-[color:var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[hsl(var(--background))]',
                  'disabled:pointer-events-none disabled:opacity-40',
                )}
              >
                {cancelLabel}
              </button>

              <button
                type="button"
                onClick={onConfirm}
                disabled={isLoading}
                className={cn(
                  'inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all outline-none',
                  'focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-[hsl(var(--background))]',
                  'disabled:pointer-events-none disabled:opacity-40 active:scale-[0.98]',
                  confirmBtnClass,
                )}
                aria-busy={isLoading || undefined}
              >
                {isLoading && <Spinner />}
                {isLoading ? 'Loading…' : confirmLabel}
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>,
    document.body,
  )
}
