'use client'

import { useState, useEffect } from 'react'
import { Users } from 'lucide-react'
import { cn } from '@/lib/utils'

interface PresenceIndicatorProps {
  className?: string
}

export function PresenceIndicator({ className }: PresenceIndicatorProps) {
  const [viewers, setViewers] = useState(1)

  useEffect(() => {
    // Simulated polling — in production this would hit a /presence endpoint
    const interval = setInterval(() => {
      // Randomly fluctuate between 1-3 viewers for demo
      setViewers(Math.floor(Math.random() * 3) + 1)
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  if (viewers <= 1) return null

  return (
    <div className={cn('inline-flex items-center gap-1.5 rounded-full border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-2.5 py-1 text-[10px] text-[color:var(--muted-ink)]', className)}>
      <span className="relative flex h-1.5 w-1.5">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
      </span>
      <Users size={10} />
      {viewers} viewing
    </div>
  )
}
