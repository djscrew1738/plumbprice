'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, X, Keyboard, Smartphone, Camera, Sun } from 'lucide-react'

const VERSION = '2.1.1'
const STORAGE_KEY = `pp-whatsnew-seen-${VERSION}`

const HIGHLIGHTS = [
  { icon: Smartphone, text: 'Installable PWA — pin PlumbPrice to your home screen' },
  { icon: Camera, text: 'On-site photo capture with priced quick-quotes' },
  { icon: Keyboard, text: 'Cmd / Ctrl + K opens the command palette' },
  { icon: Sun, text: 'Dark mode toggle in the header' },
]

export function WhatsNewBanner() {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined') return
    try {
      if (!window.localStorage.getItem(STORAGE_KEY)) {
        // Defer slightly so it doesn't compete with auth redirects.
        const t = setTimeout(() => setOpen(true), 1200)
        return () => clearTimeout(t)
      }
    } catch {
      // private mode or storage disabled — just don't show
    }
  }, [])

  const dismiss = () => {
    try {
      window.localStorage.setItem(STORAGE_KEY, '1')
    } catch {
      // ignore
    }
    setOpen(false)
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          role="status"
          aria-live="polite"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 24 }}
          className="fixed bottom-4 right-4 z-40 max-w-sm rounded-xl border border-blue-200 bg-white shadow-lg dark:border-blue-800 dark:bg-slate-900"
        >
          <div className="flex items-start gap-3 p-4">
            <div className="rounded-lg bg-blue-50 p-2 text-blue-600 dark:bg-blue-950 dark:text-blue-300">
              <Sparkles className="h-5 w-5" aria-hidden />
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                What&apos;s new in PlumbPrice {VERSION}
              </p>
              <ul className="mt-2 space-y-1.5">
                {HIGHLIGHTS.map(({ icon: Icon, text }) => (
                  <li
                    key={text}
                    className="flex items-start gap-2 text-xs text-slate-600 dark:text-slate-300"
                  >
                    <Icon className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-slate-400" aria-hidden />
                    <span>{text}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-3 flex items-center gap-3 text-xs">
                <a
                  href="/changelog"
                  className="font-medium text-blue-600 hover:underline dark:text-blue-400"
                  onClick={dismiss}
                >
                  Full changelog →
                </a>
                <button
                  onClick={dismiss}
                  className="text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
                >
                  Got it
                </button>
              </div>
            </div>
            <button
              onClick={dismiss}
              aria-label="Dismiss"
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
