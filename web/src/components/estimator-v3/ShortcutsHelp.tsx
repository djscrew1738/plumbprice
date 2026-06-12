'use client'

import { useEffect, useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { X, Keyboard } from 'lucide-react'
import { SHORTCUT_HELP } from '@/lib/useKeyboardShortcuts'

export function ShortcutsHelp() {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const handler = () => setOpen((o) => !o)
    window.addEventListener('show-shortcuts', handler)
    return () => window.removeEventListener('show-shortcuts', handler)
  }, [])

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-[20%] z-50 w-full max-w-sm -translate-x-1/2 rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-5 shadow-2xl focus:outline-none">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Keyboard size={15} className="text-[color:var(--accent-strong)]" />
              <h2 className="text-sm font-semibold text-[color:var(--ink)]">
                Keyboard shortcuts
              </h2>
            </div>
            <Dialog.Close asChild>
              <button
                aria-label="Close shortcuts dialog"
                className="rounded-lg p-2 text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
              >
                <X size={15} />
              </button>
            </Dialog.Close>
          </div>
          <ul className="space-y-2">
            {SHORTCUT_HELP.map((s) => (
              <li key={s.keys} className="flex items-center justify-between">
                <span className="text-sm text-[color:var(--muted-ink)]">
                  {s.description}
                </span>
                <kbd className="rounded-md border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-2 py-0.5 font-mono text-[11px] text-[color:var(--ink)]">
                  {s.keys}
                </kbd>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-[11px] text-[color:var(--muted-ink)]">
            Press{' '}
            <kbd className="rounded border border-[color:var(--line)] px-1 font-mono text-[10px]">
              ?
            </kbd>{' '}
            to toggle this dialog
          </p>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
