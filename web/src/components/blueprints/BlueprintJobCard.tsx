'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { FileText, X, RefreshCw } from 'lucide-react'
import dynamic from 'next/dynamic'
import { Badge } from '@/components/ui/Badge'
import { cn } from '@/lib/utils'
import type { BlueprintJob } from '@/lib/hooks'
import { STATUS } from './config'
import { TakeoffDisplay } from './TakeoffDisplay'
import type { TakeoffFixture } from './types'

const ConfirmDialog = dynamic(
  () => import('@/components/ui/ConfirmDialog').then(m => ({ default: m.ConfirmDialog })),
  { ssr: false }
)

interface BlueprintJobCardProps {
  job: BlueprintJob
  onRemove: (id: string) => void
  onRetry: (id: string) => void
  onCreateEstimate: (jobId: string, fixtures: TakeoffFixture[]) => void
}

export function BlueprintJobCard({
  job,
  onRemove,
  onRetry,
  onCreateEstimate,
}: BlueprintJobCardProps) {
  const [confirmDelete, setConfirmDelete] = useState(false)
  const cfg = STATUS[job.status] ?? STATUS.queued
  const StatusIcon = cfg.icon

  const uploadedDate = new Date(job.uploaded_at)
  const timeLabel = Number.isFinite(uploadedDate.getTime())
    ? uploadedDate.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
    : ''

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.97 }}
        transition={{ duration: 0.18 }}
        className="card p-4"
      >
        <div className="flex items-center gap-4">
          {/* File icon */}
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/[0.07] bg-white/[0.04]">
            <FileText size={18} className="text-zinc-500" />
          </div>

          {/* Info */}
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-semibold text-zinc-200">{job.filename}</div>
            <div className="mt-0.5 text-[11px] text-zinc-600">
              {job.pages > 0 ? `${job.pages} pages · ` : ''}{timeLabel}
            </div>
            {job.message && (
              <div className="mt-0.5 text-[11px] text-red-400">{job.message}</div>
            )}
          </div>

          {/* Status badge */}
          <Badge variant={cfg.variant} size="md">
            <StatusIcon
              size={11}
              className={cn(job.status === 'processing' && 'animate-spin')}
              aria-hidden="true"
            />
            {cfg.label}
          </Badge>

          {/* Retry (failed only) */}
          {job.status === 'failed' && (
            <button
              type="button"
              onClick={() => onRetry(job.id)}
              className="flex min-h-[32px] min-w-[32px] shrink-0 items-center justify-center rounded-lg p-2 text-zinc-600 transition-colors hover:bg-white/[0.07] hover:text-zinc-300"
              aria-label={`Retry ${job.filename}`}
            >
              <RefreshCw size={14} />
            </button>
          )}

          {/* Remove */}
          <button
            type="button"
            onClick={() => setConfirmDelete(true)}
            className="flex min-h-[32px] min-w-[32px] shrink-0 items-center justify-center rounded-lg p-2 text-zinc-600 transition-colors hover:bg-white/[0.07] hover:text-zinc-300"
            aria-label={`Remove ${job.filename}`}
          >
            <X size={14} />
          </button>
        </div>

        {/* Takeoff results for completed jobs */}
        {job.status === 'completed' && (
          <TakeoffDisplay jobId={job.id} onCreateEstimate={onCreateEstimate} />
        )}
      </motion.div>

      <ConfirmDialog
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        onConfirm={() => { onRemove(job.id); setConfirmDelete(false) }}
        title="Delete blueprint"
        description={`Delete "${job.filename}"? This cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
      />
    </>
  )
}
