'use client'

/**
 * Field tech home page — /field
 *
 * Mobile-first, full-screen layout for field plumbing technicians.
 * Shows quick-action tiles (Photo Quote, Voice Quote) and today's assigned jobs.
 * Accessible to field_tech and admin roles only.
 */

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Camera, Mic, Wifi, WifiOff, ChevronRight, ClipboardList } from 'lucide-react'
import { cn } from '@/lib/utils'
import { haptic } from '@/lib/haptics'

export default function FieldHomePage() {
  const [syncing, setSyncing] = useState(false)
  const [isOnline, setIsOnline] = useState(true)

  useEffect(() => {
    setIsOnline(navigator.onLine)
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  // Listen for outbox sync triggers from service worker
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === 'OUTBOX_SYNC_TRIGGERED') {
        setSyncing(true)
        // Actual sync is handled by outbox.ts — just show indicator
        setTimeout(() => setSyncing(false), 3000)
      }
    }
    navigator.serviceWorker?.addEventListener('message', handleMessage)
    return () => navigator.serviceWorker?.removeEventListener('message', handleMessage)
  }, [])

  return (
    <div className="flex flex-col min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-background border-b border-border-subtle px-4 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-foreground">PlumbPrice Field</h1>
          <p className="text-xs text-muted-foreground">CTL Plumbing LLC</p>
        </div>
        <div className="flex items-center gap-2">
          {syncing && (
            <span className="text-xs text-orange-500 font-medium animate-pulse">Syncing…</span>
          )}
          {isOnline ? (
            <Wifi className="h-4 w-4 text-green-500" />
          ) : (
            <WifiOff className="h-4 w-4 text-orange-500" />
          )}
        </div>
      </header>

      {/* Offline banner */}
      {!isOnline && (
        <div className="bg-orange-50 border-b border-orange-200 px-4 py-2 text-sm text-orange-700 text-center">
          Offline mode — estimates will sync when you reconnect
        </div>
      )}

      {/* Quick-action tiles */}
      <section className="p-4 space-y-3">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide px-1">
          Quick Actions
        </h2>

        <QuickActionTile
          icon={<Camera className="h-7 w-7" />}
          title="Photo Quote"
          description="Snap photos → instant estimate"
          href="/field/photo"
          accent="orange"
        />

        <QuickActionTile
          icon={<Mic className="h-7 w-7" />}
          title="Voice Quote"
          description="Describe the job → priced estimate"
          href="/field/voice"
          accent="blue"
        />

        <QuickActionTile
          icon={<ClipboardList className="h-7 w-7" />}
          title="My Jobs"
          description="View and close assigned jobs"
          href="/field/jobs"
          accent="gray"
        />
      </section>

      {/* Bottom nav spacer */}
      <div className="h-16" />
    </div>
  )
}

function QuickActionTile({
  icon,
  title,
  description,
  href,
  accent,
}: {
  icon: React.ReactNode
  title: string
  description: string
  href: string
  accent: 'orange' | 'blue' | 'gray'
}) {
  const router = useRouter()

  const accentClasses = {
    orange: 'bg-orange-50 text-orange-600 border-orange-200',
    blue: 'bg-blue-50 text-blue-600 border-blue-200',
    gray: 'bg-surface-1 text-muted-foreground border-border-subtle',
  }

  return (
    <button
      onClick={() => {
        haptic('tap')
        router.push(href)
      }}
      className={cn(
        'w-full flex items-center gap-4 p-4 rounded-xl border',
        'active:scale-[0.98] transition-transform duration-100',
        'min-h-[72px]', // 44px is minimum tap target; 72px gives comfortable touch
        accentClasses[accent]
      )}
    >
      <div className="flex-shrink-0">{icon}</div>
      <div className="flex-1 text-left">
        <div className="font-semibold text-foreground text-base">{title}</div>
        <div className="text-sm text-muted-foreground">{description}</div>
      </div>
      <ChevronRight className="h-5 w-5 text-muted-foreground flex-shrink-0" />
    </button>
  )
}
