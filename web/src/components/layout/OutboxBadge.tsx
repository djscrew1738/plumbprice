"use client"

import { CloudOff, Cloud, Loader2 } from 'lucide-react'
import { useOutbox } from '@/lib/hooks/useOutbox'
import { useFlag } from '@/lib/hooks/useFeatureFlags'
import { Tooltip } from '@/components/ui/Tooltip'

/**
 * Compact connectivity / outbox indicator. Renders nothing when:
 *   - the `outbox_offline` flag is off, AND
 *   - the device is online with zero queued items.
 *
 * Otherwise shows a pill with the count of queued mutations and a manual
 * "Flush" trigger.
 */
export function OutboxBadge() {
  const enabled = useFlag('outbox_offline', false)
  const { count, online, flushNow } = useOutbox()

  if (!enabled && online && count === 0) return null
  if (online && count === 0) return null

  const label = !online
    ? `Offline · ${count} queued`
    : count > 0
      ? `${count} pending sync`
      : 'Online'

  return (
    <Tooltip content={online ? 'Replay queued changes now' : 'Will sync when connection returns'} side="bottom">
      <button
        type="button"
        onClick={() => online && void flushNow()}
        disabled={!online}
        className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors
          ${online
            ? 'bg-amber-500/10 text-amber-400 hover:bg-amber-500/20'
            : 'bg-rose-500/10 text-rose-400'}
        `}
        aria-label={label}
      >
        {!online ? (
          <CloudOff className="h-3.5 w-3.5" aria-hidden />
        ) : count > 0 ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
        ) : (
          <Cloud className="h-3.5 w-3.5" aria-hidden />
        )}
        <span>{label}</span>
      </button>
    </Tooltip>
  )
}
