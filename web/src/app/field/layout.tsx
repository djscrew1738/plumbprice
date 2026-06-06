'use client'

/**
 * Field tech layout — /field/*
 *
 * Enables the offline outbox flag for all field routes so that estimate
 * mutations are automatically queued to IndexedDB when offline and
 * flushed when connectivity returns.
 */

import { useEffect } from 'react'

const OUTBOX_FLAG_KEY = 'flag:outbox_offline'

export default function FieldLayout({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Enable outbox offline queuing for all field routes.
    // This flag is read by useCreateEstimate() and other mutations.
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(OUTBOX_FLAG_KEY, '1')
    }
    return () => {
      // Do NOT clear on unmount — field techs navigate between /field/* routes
      // and the flag should persist for the entire field session.
    }
  }, [])

  return <>{children}</>
}
