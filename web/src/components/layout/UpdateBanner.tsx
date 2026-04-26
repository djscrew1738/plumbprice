'use client'

import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { RefreshCw } from 'lucide-react'

/**
 * Listens for the 'sw-update-available' event dispatched by registerSW().
 * When fired, shows a banner offering the user a one-click reload to pick
 * up the new service worker (and therefore the freshly deployed app shell).
 */
export function UpdateBanner() {
  const [applyUpdate, setApplyUpdate] = useState<(() => void) | null>(null)

  useEffect(() => {
    function onUpdate(e: Event) {
      const ce = e as CustomEvent<{ applyUpdate: () => void }>
      if (ce.detail?.applyUpdate) setApplyUpdate(() => ce.detail.applyUpdate)
    }
    window.addEventListener('sw-update-available', onUpdate)
    return () => window.removeEventListener('sw-update-available', onUpdate)
  }, [])

  return (
    <AnimatePresence>
      {applyUpdate && (
        <motion.div
          initial={{ y: -40, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -40, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="overflow-hidden"
        >
          <div
            role="status"
            className="flex flex-wrap items-center justify-center gap-3 bg-[hsl(var(--primary)/0.12)] border-b border-[hsl(var(--primary)/0.25)] px-4 py-2 text-sm font-medium text-[hsl(var(--foreground))]"
          >
            <RefreshCw size={16} className="shrink-0" aria-hidden="true" />
            <span>A new version of PlumbPrice is ready.</span>
            <button
              type="button"
              onClick={() => applyUpdate()}
              className="rounded-md bg-[hsl(var(--primary))] px-3 py-1 text-xs font-semibold text-[hsl(var(--primary-foreground))] hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
            >
              Reload
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
