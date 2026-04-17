'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  BriefcaseBusiness, MapPin, UserRound, ChevronLeft, ChevronRight, Clock,
} from 'lucide-react'
import { type ProjectPipelineItem } from '@/lib/api'
import { cn, formatCurrency } from '@/lib/utils'
import { Badge } from '@/components/ui/Badge'
import { Tooltip } from '@/components/ui/Tooltip'

function timeAgo(dateStr: string): string {
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diffMs = now - then
  const mins = Math.floor(diffMs / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 30) return `${days}d ago`
  const months = Math.floor(days / 30)
  return `${months}mo ago`
}

export interface PipelineCardProps {
  project: ProjectPipelineItem
  delay: number
  stageKeys: readonly string[]
  onMove: (id: number, newStatus: string) => Promise<void>
}

export function PipelineCard({ project, delay, stageKeys, onMove }: PipelineCardProps) {
  const [moving, setMoving] = useState(false)
  const currentIdx = stageKeys.indexOf(project.status)
  const canForward = currentIdx < stageKeys.length - 1
  const canBack    = currentIdx > 0

  const move = async (direction: 'forward' | 'back') => {
    const nextStatus = stageKeys[direction === 'forward' ? currentIdx + 1 : currentIdx - 1]
    if (!nextStatus) return
    setMoving(true)
    try {
      await onMove(project.id, nextStatus)
    } finally {
      setMoving(false)
    }
  }

  return (
    <motion.article
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18, delay }}
      className={cn(
        'rounded-2xl border bg-[color:var(--panel)] p-3.5 space-y-3 transition-all hover:-translate-y-0.5 hover:shadow-lg',
        project.status === 'won' && 'border-emerald-500/20 bg-emerald-500/[0.04]',
        project.status === 'lost' && 'border-red-500/20 bg-red-500/[0.03]',
        project.status === 'estimate_sent' && 'border-blue-500/20 bg-blue-500/[0.03]',
        project.status === 'lead' && 'border-[color:var(--line)]',
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-[color:var(--ink)] truncate leading-snug">{project.name}</h3>
          <div className="flex items-center gap-1 mt-1">
            <BriefcaseBusiness size={11} className="text-[color:var(--muted-ink)] shrink-0" />
            <span className="text-[11px] text-[color:var(--muted-ink)] capitalize">{project.job_type}</span>
          </div>
        </div>
        <div className="text-right shrink-0">
          {project.latest_estimate_total != null ? (
            <div className="text-sm font-bold text-[color:var(--ink)] tabular-nums">
              {formatCurrency(project.latest_estimate_total)}
            </div>
          ) : (
            <div className="text-xs text-[color:var(--muted-ink)] font-medium">Open</div>
          )}
        </div>
      </div>

      {/* Details */}
      <div className="grid grid-cols-2 gap-1.5 text-xs">
        <div className="card-inset px-2.5 py-2">
          <div className="flex items-center gap-1 text-[color:var(--muted-ink)] mb-0.5">
            <UserRound size={10} />
            <span className="text-[10px]">Customer</span>
          </div>
          <div className="text-[color:var(--ink)] font-medium truncate">{project.customer_name || '—'}</div>
        </div>
        <div className="card-inset px-2.5 py-2">
          <div className="flex items-center gap-1 text-[color:var(--muted-ink)] mb-0.5">
            <MapPin size={10} />
            <span className="text-[10px]">County</span>
          </div>
          <div className="text-[color:var(--ink)] font-medium truncate">{project.county}</div>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-[11px]">
        <div className="flex items-center gap-2 text-[color:var(--muted-ink)]">
          <span>{project.estimate_count} {project.estimate_count === 1 ? 'estimate' : 'estimates'}</span>
          <Tooltip content={new Date(project.created_at).toLocaleDateString()}>
            <span className="flex items-center gap-0.5">
              <Clock size={9} />
              {timeAgo(project.created_at)}
            </span>
          </Tooltip>
        </div>
        <div className="flex items-center gap-1">
          {project.status === 'won' && (
            <Badge variant="success" size="sm" className="mr-1">Won ✓</Badge>
          )}
          {project.status === 'lost' && (
            <Badge variant="danger" size="sm" className="mr-1">Lost</Badge>
          )}
          {canBack && (
            <Tooltip content="Move back">
              <button
                onClick={() => void move('back')}
                disabled={moving}
                className="p-2 rounded-lg text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] hover:bg-[color:var(--panel-strong)] transition-colors disabled:opacity-40"
                aria-label="Move to previous stage"
              >
                <ChevronLeft size={13} />
              </button>
            </Tooltip>
          )}
          {canForward && (
            <Tooltip content="Advance stage">
              <button
                onClick={() => void move('forward')}
                disabled={moving}
                className="p-2 rounded-lg text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] hover:bg-[color:var(--panel-strong)] transition-colors disabled:opacity-40"
                aria-label="Move to next stage"
              >
                <ChevronRight size={13} />
              </button>
            </Tooltip>
          )}
        </div>
      </div>
    </motion.article>
  )
}
