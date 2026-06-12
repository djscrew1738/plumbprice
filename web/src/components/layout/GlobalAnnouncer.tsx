'use client'

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

interface AnnouncerContextValue {
  /** Announce a message to screen-reader users via the global live region. */
  announce: (message: string) => void
}

const AnnouncerContext = createContext<AnnouncerContextValue>({ announce: () => {} })

export function useAnnouncer() {
  return useContext(AnnouncerContext)
}

export function GlobalAnnouncer({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState('')

  const announce = useCallback((next: string) => {
    setMessage('')
    // Force a DOM refresh so the same message re-announces if needed.
    requestAnimationFrame(() => setMessage(next))
  }, [])

  return (
    <AnnouncerContext.Provider value={{ announce }}>
      {children}
      {/* Global polite aria-live region for status messages not covered by toasts. */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {message}
      </div>
    </AnnouncerContext.Provider>
  )
}
