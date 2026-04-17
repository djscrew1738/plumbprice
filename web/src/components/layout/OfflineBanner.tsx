'use client'

import { AnimatePresence, motion } from 'framer-motion'
import { WifiOff } from 'lucide-react'
import { useOnlineStatus } from '@/lib/useOnlineStatus'

export function OfflineBanner() {
  const online = useOnlineStatus()

  return (
    <AnimatePresence>
      {!online && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.25, ease: 'easeInOut' }}
          className="overflow-hidden"
        >
          <div
            role="alert"
            className="flex items-center justify-center gap-2 bg-[hsl(var(--warning)/0.12)] border-b border-[hsl(var(--warning)/0.25)] px-4 py-2 text-sm font-medium text-[hsl(var(--warning-foreground))]"
          >
            <WifiOff size={16} className="shrink-0" aria-hidden="true" />
            You&apos;re currently offline. Some features may be unavailable.
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
