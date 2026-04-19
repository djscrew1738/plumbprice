'use client'

import { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, XCircle, AlertCircle, X } from 'lucide-react'
import { cn } from '@/lib/utils'

type ToastType = 'success' | 'error' | 'info'

interface ToastItem {
  id: string
  type: ToastType
  title: string
  message?: string
}

interface ToastCtx {
  success: (title: string, message?: string) => void
  error:   (title: string, message?: string) => void
  info:    (title: string, message?: string) => void
}

const ToastContext = createContext<ToastCtx>({ success: () => {}, error: () => {}, info: () => {} })

export function useToast() { return useContext(ToastContext) }

const STYLES: Record<ToastType, { wrap: string; icon: string; title: string }> = {
  success: { wrap: 'bg-[color:var(--panel)] border-emerald-500/30',  icon: 'text-emerald-500', title: 'text-emerald-700 dark:text-emerald-400' },
  error:   { wrap: 'bg-[color:var(--panel)] border-red-500/30',      icon: 'text-red-500',     title: 'text-red-700 dark:text-red-400'         },
  info:    { wrap: 'bg-[color:var(--panel)] border-blue-500/30',      icon: 'text-blue-500',    title: 'text-blue-700 dark:text-blue-400'        },
}

const ICONS: Record<ToastType, typeof CheckCircle2> = {
  success: CheckCircle2,
  error:   XCircle,
  info:    AlertCircle,
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const add = useCallback((type: ToastType, title: string, message?: string) => {
    const id = crypto.randomUUID()
    setToasts(prev => [...prev, { id, type, title, message }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4500)
  }, [])

  const dismiss = useCallback((id: string) => setToasts(prev => prev.filter(t => t.id !== id)), [])

  const value: ToastCtx = {
    success: (title, msg) => add('success', title, msg),
    error:   (title, msg) => add('error',   title, msg),
    info:    (title, msg) => add('info',    title, msg),
  }

  return (
    <ToastContext.Provider value={value}>
      {children}

      {/* Toast stack — top-right desktop, top-center mobile */}
      <div role="region" aria-label="Notifications" aria-live="polite" aria-atomic="false" className="fixed top-4 left-1/2 -translate-x-1/2 sm:left-auto sm:translate-x-0 sm:right-4 z-[300] flex flex-col gap-2 w-[calc(100vw-2rem)] sm:w-80 pointer-events-none">
        <AnimatePresence initial={false}>
          {toasts.map(t => {
            const s = STYLES[t.type]
            const Icon = ICONS[t.type]
            return (
              <motion.div
                key={t.id}
                initial={{ opacity: 0, y: -10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0,   scale: 1    }}
                exit={{   opacity: 0, y: -8,   scale: 0.95 }}
                transition={{ type: 'spring', stiffness: 420, damping: 32 }}
                className={cn(
                  'pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-2xl border shadow-2xl',
                  s.wrap,
                )}
              >
                <Icon size={16} className={cn('shrink-0 mt-0.5', s.icon)} aria-hidden="true" />
                <div className="flex-1 min-w-0">
                  <p className={cn('text-sm font-semibold leading-snug', s.title)}>{t.title}</p>
                  {t.message && <p className="text-xs text-[color:var(--muted-ink)] mt-0.5 leading-relaxed">{t.message}</p>}
                </div>
                <button
                  onClick={() => dismiss(t.id)}
                  aria-label="Dismiss notification"
                  className="shrink-0 rounded-lg p-1 text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
                >
                  <X size={14} />
                </button>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}
