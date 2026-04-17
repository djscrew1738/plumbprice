'use client'

import { useState, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Layers, Upload, FileText, Clock, CheckCircle2,
  AlertCircle, X, Loader2, FolderOpen, Zap,
  RefreshCw, ArrowRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import dynamic from 'next/dynamic'
import { Badge } from '@/components/ui/Badge'

const ConfirmDialog = dynamic(() => import('@/components/ui/ConfirmDialog').then(m => ({ default: m.ConfirmDialog })), { ssr: false })
import { Skeleton } from '@/components/ui/Skeleton'
import { useToast } from '@/components/ui/Toast'
import { blueprintsApi } from '@/lib/api'
import { useBlueprints, useUploadBlueprint, useDeleteBlueprint, type JobStatus, type BlueprintJob } from '@/lib/hooks'

// ─── Types ────────────────────────────────────────────────────────────────────

interface TakeoffFixture {
  name: string
  quantity: number
  confidence: number
  unit?: string
}

interface TakeoffResult {
  fixtures: TakeoffFixture[]
}

// ─── Status config ────────────────────────────────────────────────────────────

const STATUS: Record<JobStatus, { icon: typeof CheckCircle2; variant: 'neutral' | 'warning' | 'success' | 'danger'; label: string }> = {
  queued:     { icon: Clock,         variant: 'neutral',  label: 'Queued'     },
  processing: { icon: Loader2,       variant: 'warning',  label: 'Processing' },
  completed:  { icon: CheckCircle2,  variant: 'success',  label: 'Complete'   },
  failed:     { icon: AlertCircle,   variant: 'danger',   label: 'Failed'     },
}

// ─── Drop zone ────────────────────────────────────────────────────────────────

function DropZone({ onFiles, isUploading }: { onFiles: (files: File[]) => void; isUploading: boolean }) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    if (isUploading) return
    const files = Array.from(e.dataTransfer.files).filter(
      f => f.type === 'application/pdf' || f.type.startsWith('image/')
    )
    if (files.length) onFiles(files)
  }, [onFiles, isUploading])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? [])
    if (files.length) onFiles(files)
    e.target.value = ''
  }

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      inputRef.current?.click()
    }
  }, [])

  return (
    <motion.div
      onDragOver={e => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      animate={{ scale: dragging ? 1.01 : 1 }}
      transition={{ duration: 0.15 }}
      onClick={() => !isUploading && inputRef.current?.click()}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      role="button"
      aria-label="Upload blueprint files. Press Enter or Space to open file picker"
      className={cn(
        'relative rounded-2xl border-2 border-dashed p-10 text-center cursor-pointer transition-all outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2',
        isUploading && 'pointer-events-none opacity-60',
      )}
      style={{
        borderColor: dragging ? 'hsl(221 83% 55% / 0.6)' : 'rgba(255,255,255,0.10)',
        background: dragging
          ? 'linear-gradient(135deg, hsl(221 83% 55% / 0.07), hsl(230 76% 52% / 0.04))'
          : 'rgba(255,255,255,0.015)',
        boxShadow: dragging
          ? 'inset 0 0 0 1px hsl(221 83% 55% / 0.15), 0 8px 32px hsl(221 83% 55% / 0.08)'
          : 'none',
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,image/*"
        multiple
        className="hidden"
        onChange={handleChange}
        disabled={isUploading}
      />

      {dragging && (
        <div
          className="absolute inset-0 rounded-2xl pointer-events-none"
          style={{
            background: 'radial-gradient(ellipse at 50% 50%, hsl(221 83% 55% / 0.08), transparent 70%)',
          }}
          aria-hidden="true"
        />
      )}

      <div
        className="relative w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4 transition-all"
        style={{
          background: dragging
            ? 'linear-gradient(135deg, hsl(221 83% 55% / 0.2), hsl(230 76% 52% / 0.15))'
            : 'rgba(255,255,255,0.04)',
          border: dragging
            ? '1px solid hsl(221 83% 55% / 0.4)'
            : '1px solid rgba(255,255,255,0.08)',
          boxShadow: dragging ? '0 0 20px hsl(221 83% 55% / 0.15)' : 'none',
        }}
      >
        {isUploading
          ? <Loader2 size={26} className="text-blue-400 animate-spin" />
          : dragging
            ? <Upload size={26} className="text-blue-400" />
            : <Layers size={26} className="text-zinc-500" />
        }
      </div>

      <p className="text-sm font-bold text-zinc-300 mb-1">
        {isUploading ? 'Uploading…' : dragging ? 'Drop your files here' : 'Upload blueprint files'}
      </p>
      <p className="text-xs text-zinc-600">
        Drag & drop or{' '}
        <span className="font-bold" style={{ color: 'hsl(221 83% 65%)' }}>browse files</span>
        {' '}· PDF or image
      </p>
    </motion.div>
  )
}

// ─── Takeoff display ──────────────────────────────────────────────────────────

function TakeoffDisplay({ jobId, onCreateEstimate }: { jobId: string; onCreateEstimate: (fixtures: TakeoffFixture[]) => void }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['blueprint-takeoff', jobId],
    queryFn: async () => {
      const res = await blueprintsApi.getTakeoff(jobId)
      return res.data as TakeoffResult
    },
    staleTime: Infinity,
  })

  if (isLoading) {
    return <Skeleton variant="table-row" count={3} className="mt-2" />
  }

  if (isError || !data?.fixtures?.length) {
    return (
      <p className="text-[11px] text-zinc-600 mt-2">
        {isError ? 'Could not load takeoff data.' : 'No fixtures detected.'}
      </p>
    )
  }

  return (
    <div className="mt-3 space-y-2">
      <p className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest">
        Detected fixtures ({data.fixtures.length})
      </p>
      <div className="space-y-1">
        {data.fixtures.map((f, i) => (
          <div key={i} className="flex items-center gap-3 px-3 py-1.5 rounded-lg bg-white/[0.02] border border-white/[0.05]">
            <span className="text-xs text-zinc-300 font-medium flex-1 truncate">{f.name}</span>
            <span className="text-[11px] text-zinc-500">×{f.quantity}{f.unit ? ` ${f.unit}` : ''}</span>
            <Badge
              variant={f.confidence >= 0.8 ? 'success' : f.confidence >= 0.5 ? 'warning' : 'danger'}
              size="sm"
            >
              {Math.round(f.confidence * 100)}%
            </Badge>
          </div>
        ))}
      </div>
      <button
        onClick={() => onCreateEstimate(data.fixtures)}
        className="mt-2 inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold bg-gradient-to-br from-emerald-500 to-emerald-600 text-white hover:shadow-lg transition-all active:scale-[0.98]"
      >
        <Zap size={13} />
        Create Estimate
        <ArrowRight size={12} />
      </button>
    </div>
  )
}

// ─── Job card ─────────────────────────────────────────────────────────────────

function JobCard({
  job,
  onRemove,
  onRetry,
  onCreateEstimate,
}: {
  job: BlueprintJob
  onRemove: (id: string) => void
  onRetry: (id: string) => void
  onCreateEstimate: (fixtures: TakeoffFixture[]) => void
}) {
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
          <div className="w-10 h-10 rounded-xl bg-white/[0.04] border border-white/[0.07] flex items-center justify-center shrink-0">
            <FileText size={18} className="text-zinc-500" />
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="font-semibold text-zinc-200 text-sm truncate">{job.filename}</div>
            <div className="text-[11px] text-zinc-600 mt-0.5">
              {job.pages > 0 ? `${job.pages} pages · ` : ''}{timeLabel}
            </div>
            {job.message && (
              <div className="text-[11px] text-red-400 mt-0.5">{job.message}</div>
            )}
          </div>

          {/* Status badge */}
          <Badge variant={cfg.variant} size="md">
            <StatusIcon size={11} className={cn(job.status === 'processing' && 'animate-spin')} aria-hidden="true" />
            {cfg.label}
          </Badge>

          {/* Retry (failed only) */}
          {job.status === 'failed' && (
            <button
              onClick={() => onRetry(job.id)}
              className="flex min-h-[32px] min-w-[32px] items-center justify-center rounded-lg p-2 hover:bg-white/[0.07] text-zinc-600 hover:text-zinc-300 transition-colors shrink-0"
              aria-label={`Retry ${job.filename}`}
            >
              <RefreshCw size={14} />
            </button>
          )}

          {/* Remove */}
          <button
            onClick={() => setConfirmDelete(true)}
            className="flex min-h-[32px] min-w-[32px] items-center justify-center rounded-lg p-2 hover:bg-white/[0.07] text-zinc-600 hover:text-zinc-300 transition-colors shrink-0"
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

// ─── Status polling hook ──────────────────────────────────────────────────────

function useBlueprintPolling(jobs: BlueprintJob[]) {
  const needsPolling = jobs.some(j => j.status === 'queued' || j.status === 'processing')
  const queryClient = useQueryClient()

  useQuery({
    queryKey: ['blueprint-poll'],
    queryFn: async () => {
      const active = jobs.filter(j => j.status === 'queued' || j.status === 'processing')
      await Promise.allSettled(
        active.map(async (job) => {
          try {
            const res = await blueprintsApi.getStatus(job.id)
            const newStatus = res.data?.status as JobStatus | undefined
            if (newStatus && newStatus !== job.status) {
              queryClient.invalidateQueries({ queryKey: ['blueprints'] })
            }
          } catch {
            // Swallow polling errors — the list query will still show the last known state
          }
        })
      )
      return null
    },
    enabled: needsPolling,
    refetchInterval: needsPolling ? 2000 : false,
  })
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function BlueprintsPage() {
  const router = useRouter()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [confirmClearAll, setConfirmClearAll] = useState(false)

  // Fetch blueprint list
  const { data: jobsData, isLoading, isError, refetch } = useBlueprints()

  const jobs = jobsData ?? []

  // Poll active jobs
  useBlueprintPolling(jobs)

  // Upload mutation
  const uploadMutation = useUploadBlueprint()

  // Delete mutation
  const deleteMutation = useDeleteBlueprint()

  const handleFiles = useCallback((files: File[]) => {
    files.forEach(file => uploadMutation.mutate(file, {
      onError: (err: Error) => toast.error('Upload failed', err.message || 'Please try again.'),
    }))
  }, [uploadMutation, toast])

  const removeJob = useCallback((id: string) => {
    deleteMutation.mutate(id, {
      onSuccess: () => toast.success('Blueprint deleted'),
      onError: () => toast.error('Delete failed', 'Please try again.'),
    })
  }, [deleteMutation, toast])

  const retryJob = useCallback((id: string) => {
    // Re-poll status (the backend may allow retries — invalidate to refresh)
    queryClient.invalidateQueries({ queryKey: ['blueprints'] })
    queryClient.invalidateQueries({ queryKey: ['blueprint-poll'] })
    toast.info('Retrying…', `Rechecking status for job ${id.slice(0, 8)}…`)
  }, [queryClient, toast])

  const handleCreateEstimate = useCallback((fixtures: TakeoffFixture[]) => {
    const items = fixtures.map(f => `${f.quantity}x ${f.name}`).join(',')
    router.push(`/estimator?entry=blueprint&items=${encodeURIComponent(items)}`)
  }, [router])

  const handleClearAll = useCallback(async () => {
    await Promise.allSettled(jobs.map(j => blueprintsApi.delete(j.id)))
    queryClient.invalidateQueries({ queryKey: ['blueprints'] })
    setConfirmClearAll(false)
    toast.success('All blueprints cleared')
  }, [jobs, queryClient, toast])

  const completedCount = jobs.filter(j => j.status === 'completed').length
  const processingCount = jobs.filter(j => j.status === 'processing' || j.status === 'queued').length

  return (
    <div className="min-h-full bg-[hsl(var(--background))]">

      {/* ── Header ── */}
      <div className="bg-[hsl(var(--background))]/80 backdrop-blur-xl border-b border-white/[0.06] px-4 py-3 sticky top-0 z-10">
        <div className="max-w-3xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center">
              <Layers size={16} className="text-violet-400" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-white">Blueprint Analysis</h1>
              <p className="text-[11px] text-zinc-600">Upload files for AI fixture detection and takeoff</p>
            </div>
          </div>
          {jobs.length > 0 && (
            <div className="flex items-center gap-2 text-[11px]">
              {processingCount > 0 && (
                <span className="flex items-center gap-1 text-blue-400 font-semibold" aria-label={`${processingCount} files processing`} role="status">
                  <Loader2 size={11} className="animate-spin" aria-hidden="true" />
                  {processingCount} processing
                </span>
              )}
              {completedCount > 0 && (
                <span className="flex items-center gap-1 text-emerald-400 font-semibold">
                  <CheckCircle2 size={11} />
                  {completedCount} complete
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-4 space-y-4">

        {/* Drop zone */}
        <DropZone onFiles={handleFiles} isUploading={uploadMutation.isPending} />

        {/* Capabilities preview */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
          {[
            { icon: Layers,       color: 'text-violet-400', bg: 'bg-violet-500/10 border-violet-500/20', title: 'Fixture Detection',  desc: 'AI counts toilets, WH, fixtures per page' },
            { icon: FolderOpen,   color: 'text-blue-400',   bg: 'bg-blue-500/10 border-blue-500/20',     title: 'Auto Takeoff',       desc: 'Generates material list from detected items' },
            { icon: FileText,     color: 'text-emerald-400',bg: 'bg-emerald-500/10 border-emerald-500/20',title: 'Instant Estimate',  desc: 'One click to full priced estimate' },
          ].map(({ icon: Icon, color, bg, title, desc }) => (
            <div key={title} className="card p-4">
              <div className={cn('w-8 h-8 rounded-xl border flex items-center justify-center mb-3', bg)}>
                <Icon size={15} className={color} />
              </div>
              <div className="text-xs font-bold text-zinc-300 mb-1">{title}</div>
              <div className="text-[11px] text-zinc-600 leading-relaxed">{desc}</div>
            </div>
          ))}
        </div>

        {/* Loading state */}
        {isLoading && (
          <Skeleton variant="card" count={3} className="h-16 rounded-xl" />
        )}

        {/* Error state */}
        {!isLoading && isError && (
          <div className="flex items-center gap-3 p-4 rounded-2xl bg-red-500/[0.06] border border-red-500/20">
            <AlertCircle size={16} className="text-red-400 shrink-0" />
            <p className="text-xs text-zinc-400 flex-1">Failed to load blueprints.</p>
            <button
              onClick={() => void refetch()}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-400 hover:text-blue-300 transition-colors"
            >
              <RefreshCw size={12} />
              Retry
            </button>
          </div>
        )}

        {/* Blueprint jobs list */}
        {!isLoading && !isError && jobs.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-3 px-0.5">
              <p className="text-[11px] font-bold text-zinc-600 uppercase tracking-widest">
                Uploaded files ({jobs.length})
              </p>
              <button
                onClick={() => setConfirmClearAll(true)}
                className="text-[11px] text-zinc-600 hover:text-zinc-400 transition-colors"
                aria-label="Clear all uploaded files"
              >
                Clear all
              </button>
            </div>
            <div className="space-y-2.5">
              <AnimatePresence initial={false}>
                {jobs.map(job => (
                  <JobCard
                    key={job.id}
                    job={job}
                    onRemove={removeJob}
                    onRetry={retryJob}
                    onCreateEstimate={handleCreateEstimate}
                  />
                ))}
              </AnimatePresence>
            </div>

            <ConfirmDialog
              open={confirmClearAll}
              onClose={() => setConfirmClearAll(false)}
              onConfirm={handleClearAll}
              title="Clear all uploads"
              description={`Delete all ${jobs.length} blueprint${jobs.length !== 1 ? 's' : ''}? This cannot be undone.`}
              confirmLabel="Clear All"
              variant="danger"
            />
          </div>
        )}
      </div>
    </div>
  )
}
