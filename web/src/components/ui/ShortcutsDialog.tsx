'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Keyboard } from 'lucide-react'
import { SHORTCUT_HELP } from '@/lib/useKeyboardShortcuts'

export function ShortcutsDialog() {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const handler = () => setOpen(o => !o)
    window.addEventListener('show-shortcuts', handler)
    return () => window.removeEventListener('show-shortcuts', handler)
  }, [])

  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open])

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -12 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="fixed left-1/2 top-[20%] z-50 w-full max-w-sm -translate-x-1/2 rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-5 shadow-2xl"
            role="dialog"
            aria-label="Keyboard shortcuts"
          >
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Keyboard size={15} className="text-[color:var(--accent-strong)]" />
                <h2 className="text-sm font-semibold text-[color:var(--ink)]">Keyboard shortcuts</h2>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="rounded-lg p-1 text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
              >
                <X size={15} />
              </button>
            </div>
            <ul className="space-y-2">
              {SHORTCUT_HELP.map(s => (
                <li key={s.keys} className="flex items-center justify-between">
                  <span className="text-sm text-[color:var(--muted-ink)]">{s.description}</span>
                  <kbd className="rounded-md border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-2 py-0.5 font-mono text-[11px] text-[color:var(--ink)]">
                    {s.keys}
                  </kbd>
                </li>
              ))}
            </ul>
            <p className="mt-4 text-[11px] text-[color:var(--muted-ink)]">
              Press <kbd className="rounded border border-[color:var(--line)] px-1 font-mono text-[10px]">?</kbd> to toggle this dialog
            </p>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
