'use client'

import { memo, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useReducedMotion } from '@/lib/useReducedMotion'

interface DrawerProps {
  open: boolean
  onClose: () => void
  title?: string
  description?: string
  children: React.ReactNode
  footer?: React.ReactNode
  position?: 'left' | 'right' | 'bottom'
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full'
  className?: string
}

const sizeClasses = {
  sm: 'w-80',
  md: 'w-96',
  lg: 'w-[32rem]',
  xl: 'w-[40rem]',
  full: 'w-full',
}

export const Drawer = memo(function Drawer({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  position = 'right',
  size = 'md',
  className,
}: DrawerProps) {
  const reduce = useReducedMotion()

  useEffect(() => {
    if (!open) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = prevOverflow
    }
  }, [open, onClose])

  const isHorizontal = position === 'left' || position === 'right'
  const translateX = position === 'left' ? '-100%' : '100%'
  const translateY = position === 'bottom' ? '100%' : '0'

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
            onClick={onClose}
            aria-hidden="true"
          />

          {/* Drawer panel */}
          <motion.div
            role="dialog"
            aria-modal="true"
            initial={reduce ? { opacity: 0 } : { x: isHorizontal ? translateX : 0, y: !isHorizontal ? translateY : 0 }}
            animate={{ x: 0, y: 0 }}
            exit={reduce ? { opacity: 0 } : { x: isHorizontal ? translateX : 0, y: !isHorizontal ? translateY : 0 }}
            transition={{ type: 'spring', damping: 32, stiffness: 320 }}
            className={cn(
              'fixed z-50 bg-[color:var(--panel-solid)] shadow-2xl',
              isHorizontal
                ? cn('inset-y-0 h-full', position === 'left' ? 'left-0' : 'right-0', sizeClasses[size])
                : 'inset-x-0 bottom-0 rounded-t-[1.5rem] max-h-[85dvh]',
              className
            )}
          >
            <div className="flex h-full flex-col">
              {/* Header */}
              {(title || description) && (
                <div className="flex items-start justify-between gap-4 border-b border-[color:var(--line)] px-5 py-4">
                  <div>
                    {title && <h2 className="text-lg font-semibold text-[color:var(--ink)]">{title}</h2>}
                    {description && <p className="mt-1 text-sm text-[color:var(--muted-ink)]">{description}</p>}
                  </div>
                  <button
                    onClick={onClose}
                    className="rounded-[1rem] p-2 text-[color:var(--muted-ink)] transition-colors hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]"
                    aria-label="Close drawer"
                  >
                    <X size={18} />
                  </button>
                </div>
              )}

              {/* Content */}
              <div className="flex-1 overflow-y-auto px-5 py-4">
                {children}
              </div>

              {/* Footer */}
              {footer && (
                <div className="border-t border-[color:var(--line)] px-5 py-4">
                  {footer}
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
})
