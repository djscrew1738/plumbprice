'use client'

import { useState, useCallback, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { AnimatePresence } from 'framer-motion'
import { useQueryClient } from '@tanstack/react-query'
import {
  Layers, CheckCircle2, AlertCircle, Loader2, FolderOpen,
  FileText, RefreshCw,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import dynamic from 'next/dynamic'
import { Skeleton } from '@/components/ui/Skeleton'
import { useToast } from '@/components/ui/Toast'
import { blueprintsApi } from '@/lib/api'
import { blueprintApiV3 } from '@/lib/api-v3'
import { useBlueprints, useUploadBlueprint, useDeleteBlueprint } from '@/lib/hooks'
import { useBlueprintPolling } from '@/lib/hooks/useBlueprintPolling'
import { MAX_BLUEPRINT_SIZE_MB } from '@/lib/constants'
import { AdobeCloudPicker } from '@/components/blueprints/AdobeCloudPicker'
import { DropZone } from './DropZone'
import { BlueprintJobCard } from './BlueprintJobCard'

const ConfirmDialog = dynamic(
  () => import('@/components/ui/ConfirmDialog').then(m => ({ default: m.ConfirmDialog })),
  { ssr: false }
)

export function BlueprintsPage() {
  const router = useRouter()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [confirmClearAll, setConfirmClearAll] = useState(false)

  // Fetch blueprint list
  const { data: jobsData, isLoading, isError, refetch } = useBlueprints()

  const jobs = useMemo(() => jobsData ?? [], [jobsData])

  // Poll active jobs
  useBlueprintPolling(jobs)

  // Upload mutation
  const uploadMutation = useUploadBlueprint()

  // Delete mutation
  const deleteMutation = useDeleteBlueprint()

  const handleFiles = useCallback((files: File[]) => {
    const maxBytes = MAX_BLUEPRINT_SIZE_MB * 1024 * 1024
    const validFiles: File[] = []
    for (const file of files) {
      if (file.size > maxBytes) {
        toast.error('File too large', `${file.name} exceeds ${MAX_BLUEPRINT_SIZE_MB} MB limit.`)
      } else {
        validFiles.push(file)
      }
    }
    validFiles.forEach(file => uploadMutation.mutate(file, {
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

  const handleCreateEstimate = useCallback(async (jobId: string) => {
    try {
      const res = await blueprintApiV3.toEstimate(Number(jobId))
      const { estimate_id } = res.data as { estimate_id: number }
      toast.success('Estimate created (v3)', 'Navigating to your new estimate…')
      router.push(`/estimates/${estimate_id}`)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error('Could not create estimate', msg ?? 'Please try again.')
    }
  }, [router, toast])

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
      <div className="sticky top-0 z-10 border-b border-white/[0.06] bg-[hsl(var(--background))]/80 px-4 py-3 backdrop-blur-xl">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-violet-500/20 bg-violet-500/10">
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
                <span className="flex items-center gap-1 font-semibold text-blue-400" aria-label={`${processingCount} files processing`} role="status">
                  <Loader2 size={11} className="animate-spin" aria-hidden="true" />
                  {processingCount} processing
                </span>
              )}
              {completedCount > 0 && (
                <span className="flex items-center gap-1 font-semibold text-emerald-400">
                  <CheckCircle2 size={11} />
                  {completedCount} complete
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="mx-auto max-w-3xl space-y-4 px-4 py-4">

        {/* Drop zone */}
        <DropZone onFiles={handleFiles} isUploading={uploadMutation.isPending} />

        {/* Adobe Cloud import */}
        <div className="flex items-center gap-3">
          <div className="h-px flex-1 bg-white/[0.06]" />
          <span className="text-[11px] font-medium text-zinc-600">or import from</span>
          <div className="h-px flex-1 bg-white/[0.06]" />
        </div>
        <AdobeCloudPicker
          onImported={() => {
            queryClient.invalidateQueries({ queryKey: ['blueprints'] })
          }}
          className="w-full justify-center"
        />

        {/* Capabilities preview */}
        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
          {[
            { icon: Layers,       color: 'text-violet-400',  bg: 'bg-violet-500/10 border-violet-500/20',    title: 'Fixture Detection', desc: 'AI counts toilets, WH, fixtures per page' },
            { icon: FolderOpen,   color: 'text-blue-400',    bg: 'bg-blue-500/10 border-blue-500/20',        title: 'Auto Takeoff',      desc: 'Generates material list from detected items' },
            { icon: FileText,     color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20',  title: 'Instant Estimate',  desc: 'One click to full priced estimate' },
          ].map(({ icon: Icon, color, bg, title, desc }) => (
            <div key={title} className="card p-4">
              <div className={cn('mb-3 flex h-8 w-8 items-center justify-center rounded-xl border', bg)}>
                <Icon size={15} className={color} />
              </div>
              <div className="mb-1 text-xs font-bold text-zinc-300">{title}</div>
              <div className="text-[11px] leading-relaxed text-zinc-600">{desc}</div>
            </div>
          ))}
        </div>

        {/* Loading state */}
        {isLoading && (
          <Skeleton variant="card" count={3} className="h-16 rounded-xl" />
        )}

        {/* Error state */}
        {!isLoading && isError && (
          <div className="flex items-center gap-3 rounded-2xl border border-red-500/20 bg-red-500/[0.06] p-4">
            <AlertCircle size={16} className="shrink-0 text-red-400" />
            <p className="flex-1 text-xs text-zinc-400">Failed to load blueprints.</p>
            <button
              type="button"
              onClick={() => void refetch()}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-400 transition-colors hover:text-blue-300"
            >
              <RefreshCw size={12} />
              Retry
            </button>
          </div>
        )}

        {/* Blueprint jobs list */}
        {!isLoading && !isError && jobs.length > 0 && (
          <div>
            <div className="mb-3 flex items-center justify-between px-0.5">
              <p className="text-[11px] font-bold uppercase tracking-widest text-zinc-600">
                Uploaded files ({jobs.length})
              </p>
              <button
                type="button"
                onClick={() => setConfirmClearAll(true)}
                className="text-[11px] text-zinc-600 transition-colors hover:text-zinc-400"
                aria-label="Clear all uploaded files"
              >
                Clear all
              </button>
            </div>
            <div className="space-y-2.5">
              <AnimatePresence initial={false}>
                {jobs.map(job => (
                  <BlueprintJobCard
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
