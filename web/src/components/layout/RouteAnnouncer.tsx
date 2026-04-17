'use client'

import { useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import { getPageMeta } from './nav'

/**
 * Announces page title on route changes so screen readers
 * inform users of navigation without a full page reload.
 */
export function RouteAnnouncer() {
  const pathname = usePathname()
  const [announcement, setAnnouncement] = useState('')

  useEffect(() => {
    const meta = getPageMeta(pathname)
    setAnnouncement(`Navigated to ${meta.title}`)
  }, [pathname])

  return (
    <div
      role="status"
      aria-live="assertive"
      aria-atomic="true"
      className="sr-only"
    >
      {announcement}
    </div>
  )
}
