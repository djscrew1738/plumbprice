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
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type ModalSize = 'sm' | 'md' | 'lg' | 'full'

export interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  description?: string
  children: ReactNode
  size?: ModalSize
  className?: string
  /** Whether clicking the backdrop closes the modal (default true). */
  closeOnBackdrop?: boolean
}

/* ------------------------------------------------------------------ */
/*  Size map                                                           */
/* ------------------------------------------------------------------ */

const sizeClasses: Record<ModalSize, string> = {
  sm: 'sm:max-w-sm',
  md: 'sm:max-w-lg',
  lg: 'sm:max-w-2xl',
  full: 'sm:max-w-full sm:inset-4',
}

/* ------------------------------------------------------------------ */
/*  Focusable-element selector                                         */
/* ------------------------------------------------------------------ */

const FOCUSABLE =
  'a[href],button:not([disabled]),textarea:not([disabled]),input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])'

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  size = 'md',
  className,
  closeOnBackdrop = true,
}: ModalProps) {
  const uid = useId()
  const titleId = `${uid}-title`
  const descId = `${uid}-desc`

  const panelRef = useRef<HTMLDivElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)

  /* ---- focus trap: capture + restore ---- */
  useEffect(() => {
    if (!open) return

    // Remember the element that was focused before the modal opened.
    previousFocusRef.current = document.activeElement as HTMLElement | null

    // Small delay so the panel DOM is ready after framer-motion mounts it.
    const raf = requestAnimationFrame(() => {
      const first = panelRef.current?.querySelector<HTMLElement>(FOCUSABLE)
      first?.focus()
    })

    return () => {
      cancelAnimationFrame(raf)
      // Restore focus when the modal closes.
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
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose])

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
    if (closeOnBackdrop) onClose()
  }, [closeOnBackdrop, onClose])

  /* ---- portal target guard (SSR-safe) ---- */
  if (typeof document === 'undefined') return null

  return createPortal(
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            key="modal-backdrop"
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
            key="modal-panel"
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            aria-describedby={description ? descId : undefined}
            initial={{ opacity: 0, scale: 0.95, y: -12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -12 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className={cn(
              // mobile: fullscreen
              'fixed inset-0 z-50 flex flex-col',
              // desktop: centered card
              'sm:inset-auto sm:left-1/2 sm:top-1/2 sm:-translate-x-1/2 sm:-translate-y-1/2 sm:w-full',
              'bg-[color:var(--panel)] border border-[color:var(--line)] sm:rounded-2xl shadow-2xl',
              sizeClasses[size],
              className,
            )}
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-[color:var(--line)] px-5 py-4">
              <h2
                id={titleId}
                className="text-base font-semibold text-[color:var(--ink)]"
              >
                {title}
              </h2>
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg p-1 text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
                aria-label="Close"
              >
                <X size={16} />
              </button>
            </div>

            {/* Optional description */}
            {description && (
              <p
                id={descId}
                className="px-5 pt-3 text-sm text-[color:var(--muted-ink)]"
              >
                {description}
              </p>
            )}

            {/* Body (scrollable) */}
            <div className="flex-1 overflow-y-auto px-5 py-4 max-h-[70vh]">
              {children}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>,
    document.body,
  )
}
