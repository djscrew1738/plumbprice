'use client'

import { motion } from 'framer-motion'
import { Activity, CheckCircle2, AlertTriangle, XCircle, Clock, RefreshCw } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { useAdminFeedHealth, type FeedHealthItem } from '@/lib/hooks'
import { cn } from '@/lib/utils'

const STATUS_STYLES: Record<string, { icon: React.ReactNode; badge: 'success' | 'warning' | 'danger'; bg: string }> = {
  healthy: {
    icon: <CheckCircle2 size={18} className="text-emerald-500" />,
    badge: 'success',
    bg: 'border-emerald-500/20 bg-emerald-500/5',
  },
  degraded: {
    icon: <AlertTriangle size={18} className="text-amber-500" />,
    badge: 'warning',
    bg: 'border-amber-500/20 bg-amber-500/5',
  },
  unhealthy: {
    icon: <XCircle size={18} className="text-red-500" />,
    badge: 'danger',
    bg: 'border-red-500/20 bg-red-500/5',
  },
}

function FeedCard({ feed }: { feed: FeedHealthItem }) {
  const style = STATUS_STYLES[feed.status] ?? STATUS_STYLES.degraded

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'rounded-2xl border p-4 transition-all',
        style.bg
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          {style.icon}
          <div>
            <h4 className="text-sm font-semibold text-[color:var(--ink)] capitalize">{feed.name}</h4>
            <Badge variant={style.badge} size="sm" className="mt-1">{feed.status}</Badge>
          </div>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-lg bg-[color:var(--panel)] p-2">
          <div className="text-[color:var(--muted-ink)]">Items Synced</div>
          <div className="mt-0.5 font-semibold text-[color:var(--ink)]">{feed.items_synced}</div>
        </div>
        <div className="rounded-lg bg-[color:var(--panel)] p-2">
          <div className="text-[color:var(--muted-ink)]">Errors</div>
          <div className={cn(
            'mt-0.5 font-semibold',
            feed.error_count > 0 ? 'text-red-600' : 'text-[color:var(--ink)]'
          )}>
            {feed.error_count}
          </div>
        </div>
      </div>

      {feed.last_sync && (
        <div className="mt-2 flex items-center gap-1 text-xs text-[color:var(--muted-ink)]">
          <Clock size={10} />
          Last sync: {new Date(feed.last_sync).toLocaleString()}
        </div>
      )}

      {feed.error_message && (
        <div className="mt-2 text-xs text-red-600 dark:text-red-400 truncate">
          {feed.error_message}
        </div>
      )}
    </motion.div>
  )
}

export function FeedStatusDashboard() {
  const { data: feeds = [], isLoading, error, refetch } = useAdminFeedHealth()

  const healthyCount = feeds.filter(f => f.status === 'healthy').length
  const degradedCount = feeds.filter(f => f.status === 'degraded').length
  const unhealthyCount = feeds.filter(f => f.status === 'unhealthy').length

  return (
    <div className="space-y-5">
      {/* Summary */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-3 py-2">
          <CheckCircle2 size={14} className="text-emerald-500" />
          <span className="text-sm font-medium text-emerald-700 dark:text-emerald-400">{healthyCount} Healthy</span>
        </div>
        <div className="flex items-center gap-2 rounded-xl border border-amber-500/20 bg-amber-500/5 px-3 py-2">
          <AlertTriangle size={14} className="text-amber-500" />
          <span className="text-sm font-medium text-amber-700 dark:text-amber-400">{degradedCount} Degraded</span>
        </div>
        <div className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/5 px-3 py-2">
          <XCircle size={14} className="text-red-500" />
          <span className="text-sm font-medium text-red-700 dark:text-red-400">{unhealthyCount} Unhealthy</span>
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={() => refetch()}
          isLoading={isLoading}
          className="ml-auto gap-1.5"
        >
          <RefreshCw size={14} />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-600">
          <AlertTriangle size={14} />
          Failed to load feed health
        </div>
      )}

      {/* Feed cards */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {feeds.map(feed => (
          <FeedCard key={feed.name} feed={feed} />
        ))}
      </div>

      {feeds.length === 0 && !isLoading && (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-[color:var(--line)] bg-[color:var(--panel)] p-8 text-center">
          <Activity size={32} className="text-[color:var(--muted-ink)]" />
          <p className="mt-2 text-sm text-[color:var(--muted-ink)]">No feed adapters registered</p>
        </div>
      )}
    </div>
  )
}
