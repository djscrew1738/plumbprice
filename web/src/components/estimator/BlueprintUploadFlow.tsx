'use client'

/**
 * BlueprintUploadFlow
 *
 * Handles the "Upload Job File" entry mode: uploads one or more blueprint PDFs
 * to the API, polls each job's status, and on completion auto-creates a draft
 * Estimate from the detected fixtures and navigates to it.
 *
 * Thumbnails/per-page previews are deferred — the worker currently stores only
 * aggregated detections, so we display the aggregate fixture list with counts.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AlertCircle, FileUp, Loader2, CheckCircle2, RotateCw, X } from 'lucide-react'

import { blueprintsApi } from '@/lib/api'
import { useToast } from '@/components/ui/Toast'
import { useWebSocket } from '@/lib/hooks/useWebSocket'

type Stage = 'uploading' | 'processing' | 'completed' | 'failed'

interface DetectedFixture {
  type: string
  count: number
  confidence: number
}

interface JobState {
  id: string
  file: File
  jobId?: number
  stage: Stage
  statusLabel: string
  fixtures?: DetectedFixture[]
  errorMessage?: string
  estimateId?: number
}

interface Props {
  projectId?: number
}

const POLL_MS = 2000

function mapStage(apiStatus: string): { stage: Stage; label: string } {
  const s = (apiStatus || '').toLowerCase()
  if (s === 'completed' || s === 'complete' || s === 'ready' || s === 'done') {
    return { stage: 'completed', label: 'Ready' }
  }
  if (s === 'failed' || s === 'error') {
    return { stage: 'failed', label: 'Failed' }
  }
  if (s === 'processing' || s === 'analyzing') {
    return { stage: 'processing', label: 'Detecting fixtures…' }
  }
  if (s === 'queued' || s === 'pending' || s === 'uploaded') {
    return { stage: 'processing', label: 'Processing…' }
  }
  return { stage: 'processing', label: apiStatus || 'Processing…' }
}

export function BlueprintUploadFlow({ projectId }: Props) {
  const router = useRouter()
  const { success, error } = useToast()
  const [jobs, setJobs] = useState<JobState[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const pollTimersRef = useRef<Record<string, ReturnType<typeof setInterval>>>({})
  const hasCreatedRef = useRef<Set<string>>(new Set())
  // Maps numeric jobId (as string) to the local file entry id
  const jobIdToLocalRef = useRef<Map<string, string>>(new Map())

  const updateJob = useCallback((id: string, patch: Partial<JobState>) => {
    setJobs(prev => prev.map(j => (j.id === id ? { ...j, ...patch } : j)))
  }, [])

  const stopPolling = useCallback((id: string) => {
    const timer = pollTimersRef.current[id]
    if (timer) {
      clearInterval(timer)
      delete pollTimersRef.current[id]
    }
  }, [])

  useEffect(() => {
    // Cleanup on unmount
    return () => {
      Object.values(pollTimersRef.current).forEach(t => clearInterval(t))
      pollTimersRef.current = {}
    }
  }, [])

  const createEstimate = useCallback(async (id: string, jobId: number) => {
    if (hasCreatedRef.current.has(id)) return
    hasCreatedRef.current.add(id)
    try {
      const { data } = await blueprintsApi.toEstimate(jobId, projectId ? { project_id: projectId } : undefined)
      updateJob(id, { estimateId: data.estimate_id })
      success('Estimate created from blueprint — opening now…')
      router.push(`/estimates/${data.estimate_id}`)
    } catch (err) {
      hasCreatedRef.current.delete(id)
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err as Error)?.message ||
        'Failed to create estimate'
      updateJob(id, { stage: 'failed', statusLabel: 'Conversion failed', errorMessage: msg })
      error('Could not create estimate', msg)
    }
  }, [projectId, router, success, error, updateJob])

  const pollJob = useCallback((id: string, jobId: number) => {
    stopPolling(id)
    pollTimersRef.current[id] = setInterval(async () => {
      try {
        const statusRes = await blueprintsApi.getStatus(String(jobId))
        const { stage, label } = mapStage(statusRes.data?.status)
        updateJob(id, { stage, statusLabel: label })

        if (stage === 'completed') {
          stopPolling(id)
          try {
            const takeoff = await blueprintsApi.getTakeoff(String(jobId))
            updateJob(id, { fixtures: takeoff.data?.fixtures ?? [] })
          } catch {
            // Non-fatal — estimate creation does its own aggregation
          }
          void createEstimate(id, jobId)
        } else if (stage === 'failed') {
          stopPolling(id)
          updateJob(id, {
            errorMessage:
              statusRes.data?.processing_error || 'Blueprint analysis failed',
          })
        }
      } catch (err) {
        // Transient poll errors: keep polling, but surface on repeated failure.
        // A single failed poll is logged and ignored.
        console.debug('blueprint status poll failed', err)
      }
    }, POLL_MS)
  }, [createEstimate, stopPolling, updateJob])

  // Handle WS push — short-circuits polling when server broadcasts status
  const handleWsMessage = useCallback((msg: Record<string, unknown>) => {
    if (msg.type !== 'blueprint_status') return
    const remoteJobId = String(msg.job_id ?? '')
    const localId = jobIdToLocalRef.current.get(remoteJobId)
    if (!localId) return

    if (msg.status === 'completed') {
      stopPolling(localId)
      const numericJobId = Number(remoteJobId)
      blueprintsApi.getTakeoff(remoteJobId)
        .then(takeoff => {
          updateJob(localId, { stage: 'completed', statusLabel: 'Ready', fixtures: takeoff.data?.fixtures ?? [] })
        })
        .catch(() => {
          updateJob(localId, { stage: 'completed', statusLabel: 'Ready' })
        })
        .finally(() => {
          void createEstimate(localId, numericJobId)
        })
    } else if (msg.status === 'error') {
      stopPolling(localId)
      updateJob(localId, {
        stage: 'failed',
        statusLabel: 'Failed',
        errorMessage: String(msg.error ?? 'Blueprint analysis failed'),
      })
    }
  }, [stopPolling, updateJob, createEstimate])

  useWebSocket(handleWsMessage)

  const uploadFile = useCallback(async (file: File) => {
    const id = `${file.name}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    setJobs(prev => [
      ...prev,
      { id, file, stage: 'uploading', statusLabel: 'Uploading…' },
    ])

    try {
      const { data } = await blueprintsApi.upload(file)
      const jobId = Number(data?.id)
      if (!jobId || Number.isNaN(jobId)) {
        throw new Error('Upload response missing job id')
      }
      updateJob(id, { jobId, stage: 'processing', statusLabel: 'Processing…' })
      jobIdToLocalRef.current.set(String(jobId), id)
      pollJob(id, jobId)
    } catch (err) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err as Error)?.message ||
        'Upload failed'
      updateJob(id, { stage: 'failed', statusLabel: 'Upload failed', errorMessage: msg })
    }
  }, [pollJob, updateJob])

  const retryJob = useCallback((id: string) => {
    const job = jobs.find(j => j.id === id)
    if (!job) return
    hasCreatedRef.current.delete(id)
    updateJob(id, {
      stage: 'uploading',
      statusLabel: 'Uploading…',
      errorMessage: undefined,
      fixtures: undefined,
      jobId: undefined,
    })
    void uploadFile(job.file)
    // Remove the stale job entry; uploadFile adds a fresh one
    setJobs(prev => prev.filter(j => j.id !== id))
  }, [jobs, updateJob, uploadFile])

  const removeJob = useCallback((id: string) => {
    stopPolling(id)
    setJobs(prev => prev.filter(j => j.id !== id))
  }, [stopPolling])

  const onFilesSelected = (fileList: FileList | null) => {
    if (!fileList) return
    Array.from(fileList).forEach(f => {
      void uploadFile(f)
    })
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  return (
    <div className="flex h-full flex-col px-4 py-6">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        multiple
        className="hidden"
        onChange={e => onFilesSelected(e.target.files)}
      />

      {jobs.length === 0 ? (
        <div className="flex flex-1 items-center justify-center">
          <div
            role="button"
            tabIndex={0}
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={e => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                fileInputRef.current?.click()
              }
            }}
            className="group w-full max-w-sm cursor-pointer text-center"
          >
            <div className="mx-auto mb-4 flex size-16 items-center justify-center rounded-2xl border-2 border-dashed border-[color:var(--line)] bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)] transition-colors group-hover:border-[color:var(--accent-strong)]">
              <FileUp size={26} />
            </div>
            <h2 className="text-xl font-semibold text-[color:var(--ink)]">Upload Blueprint</h2>
            <p className="mt-2 text-sm text-[color:var(--muted-ink)]">
              Click to browse or drop PDF plans. We&apos;ll detect fixtures and draft a priced estimate automatically.
            </p>
            <p className="mt-3 text-[11px] text-[color:var(--muted-ink)] opacity-60">PDF · up to 100 MB</p>
          </div>
        </div>
      ) : (
        <div className="mx-auto w-full max-w-2xl space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-[color:var(--ink)]">Blueprint uploads</h2>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="rounded-lg border border-[color:var(--line)] px-3 py-1.5 text-xs font-semibold text-[color:var(--ink)] hover:bg-[color:var(--panel-strong)]"
            >
              + Add file
            </button>
          </div>

          {jobs.map(job => (
            <JobCard
              key={job.id}
              job={job}
              onRetry={retryJob}
              onRemove={removeJob}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function JobCard({
  job,
  onRetry,
  onRemove,
}: {
  job: JobState
  onRetry: (id: string) => void
  onRemove: (id: string) => void
}) {
  const isActive = job.stage === 'uploading' || job.stage === 'processing'
  return (
    <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--panel-strong)] p-4">
      <div className="flex items-center gap-3">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]">
          <FileUp size={16} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium text-[color:var(--ink)]">{job.file.name}</div>
          <div className="mt-0.5 flex items-center gap-1.5 text-[11px] text-[color:var(--muted-ink)]">
            {isActive && <Loader2 size={11} className="animate-spin" aria-hidden="true" />}
            {job.stage === 'completed' && <CheckCircle2 size={11} className="text-emerald-500" aria-hidden="true" />}
            {job.stage === 'failed' && <AlertCircle size={11} className="text-red-500" aria-hidden="true" />}
            <span>{job.statusLabel}</span>
          </div>
        </div>
        {job.stage === 'failed' && (
          <button
            type="button"
            onClick={() => onRetry(job.id)}
            className="flex size-8 items-center justify-center rounded-lg text-[color:var(--muted-ink)] hover:bg-[color:var(--panel)] hover:text-[color:var(--ink)]"
            aria-label={`Retry ${job.file.name}`}
          >
            <RotateCw size={14} />
          </button>
        )}
        <button
          type="button"
          onClick={() => onRemove(job.id)}
          className="flex size-8 items-center justify-center rounded-lg text-[color:var(--muted-ink)] hover:bg-[color:var(--panel)] hover:text-[color:var(--ink)]"
          aria-label={`Remove ${job.file.name}`}
        >
          <X size={14} />
        </button>
      </div>

      {job.stage === 'failed' && job.errorMessage && (
        <div
          role="alert"
          className="mt-3 flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/5 p-2.5 text-xs text-red-600 dark:text-red-400"
        >
          <AlertCircle size={12} className="mt-0.5 shrink-0" />
          <span className="flex-1">{job.errorMessage}</span>
        </div>
      )}

      {job.fixtures && job.fixtures.length > 0 && (
        <div className="mt-3 space-y-1.5">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--muted-ink)]">
            Detected fixtures ({job.fixtures.length})
          </p>
          <ul className="space-y-1">
            {job.fixtures.map((f, idx) => (
              <li
                key={`${f.type}-${idx}`}
                className="flex items-center justify-between rounded-md bg-[color:var(--panel)] px-2.5 py-1.5 text-xs"
              >
                <span className="text-[color:var(--ink)]">{f.type.replace(/_/g, ' ')}</span>
                <span className="tabular-nums text-[color:var(--muted-ink)]">
                  ×{f.count}
                  {typeof f.confidence === 'number' && (
                    <span className="ml-2 opacity-70">{Math.round(f.confidence * 100)}%</span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
