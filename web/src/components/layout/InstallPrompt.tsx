'use client'

import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Download, X } from 'lucide-react'

const DISMISS_KEY = 'pp.installPrompt.dismissedAt'
const DISMISS_TTL_MS = 7 * 24 * 60 * 60 * 1000  // 7 days — don't pester

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

/**
 * Shows a lightweight "Install PlumbPrice" prompt:
 *  - On Android/Chrome: fires the native `beforeinstallprompt` flow when the
 *    user accepts.
 *  - On iOS Safari (no beforeinstallprompt): renders instructions to use the
 *    Share menu → Add to Home Screen, since that's the only path Apple allows.
 *
 * Suppressed if the user already installed (display-mode: standalone), or
 * dismissed within the last 7 days.
 */
export function InstallPrompt() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null)
  const [iosVisible, setIosVisible] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined') return

    // Already installed?
    const standalone =
      window.matchMedia?.('(display-mode: standalone)').matches ||
      // iOS Safari exposes navigator.standalone
      // @ts-expect-error -- legacy Apple-only field
      window.navigator.standalone === true
    if (standalone) return

    // Recently dismissed?
    const dismissedAt = Number(window.localStorage.getItem(DISMISS_KEY) || 0)
    if (dismissedAt && Date.now() - dismissedAt < DISMISS_TTL_MS) return

    // Android/Chrome path
    const onBeforeInstall = (e: Event) => {
      e.preventDefault()
      setDeferred(e as BeforeInstallPromptEvent)
    }
    window.addEventListener('beforeinstallprompt', onBeforeInstall)

    // iOS Safari fallback: detect roughly, show instructional banner.
    const ua = window.navigator.userAgent
    const isIos = /iPhone|iPad|iPod/.test(ua) && !/CriOS|FxiOS|EdgiOS/.test(ua)
    if (isIos) setIosVisible(true)

    return () => window.removeEventListener('beforeinstallprompt', onBeforeInstall)
  }, [])

  function dismiss() {
    window.localStorage.setItem(DISMISS_KEY, String(Date.now()))
    setDeferred(null)
    setIosVisible(false)
  }

  async function install() {
    if (!deferred) return
    await deferred.prompt()
    await deferred.userChoice
    dismiss()
  }

  const visible = !!deferred || iosVisible

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ y: 80, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 80, opacity: 0 }}
          transition={{ duration: 0.25 }}
          className="fixed inset-x-3 bottom-3 z-50 mx-auto max-w-md sm:bottom-6"
        >
          <div className="flex items-start gap-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-3 shadow-lg">
            <div className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))]">
              <Download size={18} aria-hidden="true" />
            </div>
            <div className="min-w-0 flex-1 text-sm">
              <div className="font-semibold text-[hsl(var(--foreground))]">
                Install PlumbPrice
              </div>
              {deferred ? (
                <p className="text-[hsl(var(--muted-foreground))]">
                  Add to your home screen for instant access offline.
                </p>
              ) : (
                <p className="text-[hsl(var(--muted-foreground))]">
                  Tap <span aria-hidden="true">⬆️</span> Share, then{' '}
                  <strong>&ldquo;Add to Home Screen&rdquo;</strong>.
                </p>
              )}
              {deferred && (
                <div className="mt-2 flex gap-2">
                  <button
                    type="button"
                    onClick={install}
                    className="rounded-md bg-[hsl(var(--primary))] px-3 py-1.5 text-xs font-semibold text-[hsl(var(--primary-foreground))] hover:opacity-90"
                  >
                    Install
                  </button>
                  <button
                    type="button"
                    onClick={dismiss}
                    className="rounded-md px-3 py-1.5 text-xs font-medium text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--muted)/0.5)]"
                  >
                    Not now
                  </button>
                </div>
              )}
            </div>
            <button
              type="button"
              onClick={dismiss}
              aria-label="Dismiss install prompt"
              className="rounded-md p-1 text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--muted)/0.5)]"
            >
              <X size={16} aria-hidden="true" />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
