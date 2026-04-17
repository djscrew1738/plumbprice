'use client'

import { useState, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Layers, Upload, FileText, Clock, CheckCircle2,
  AlertCircle, X, Loader2, FolderOpen, Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/Badge'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'

// ─── Types ────────────────────────────────────────────────────────────────────

type JobStatus = 'queued' | 'processing' | 'done' | 'failed'

interface BlueprintJob {
  id: string
  filename: string
  pages: number
  status: JobStatus
  uploadedAt: Date
  message?: string
}

// ─── Status config ────────────────────────────────────────────────────────────

const STATUS: Record<JobStatus, { icon: typeof CheckCircle2; variant: 'neutral' | 'info' | 'success' | 'danger'; label: string }> = {
  queued:     { icon: Clock,         variant: 'neutral',  label: 'Queued'     },
  processing: { icon: Loader2,       variant: 'info',     label: 'Processing' },
  done:       { icon: CheckCircle2,  variant: 'success',  label: 'Complete'   },
  failed:     { icon: AlertCircle,   variant: 'danger',   label: 'Failed'     },
}

// ─── Drop zone ────────────────────────────────────────────────────────────────

function DropZone({ onFiles }: { onFiles: (files: File[]) => void }) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const files = Array.from(e.dataTransfer.files).filter(f => f.type === 'application/pdf')
    if (files.length) onFiles(files)
  }, [onFiles])

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
      onClick={() => inputRef.current?.click()}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      role="button"
      aria-label="Upload blueprint PDFs. Press Enter or Space to open file picker"
      className="relative rounded-2xl border-2 border-dashed p-10 text-center cursor-pointer transition-all outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
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
        accept="application/pdf"
        multiple
        className="hidden"
        onChange={handleChange}
      />

      {/* Ambient glow when dragging */}
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
        {dragging
          ? <Upload size={26} className="text-blue-400" />
          : <Layers size={26} className="text-zinc-500" />
        }
      </div>

      <p className="text-sm font-bold text-zinc-300 mb-1">
        {dragging ? 'Drop your PDF here' : 'Upload blueprint PDFs'}
      </p>
      <p className="text-xs text-zinc-600">
        Drag & drop or{' '}
        <span className="font-bold" style={{ color: 'hsl(221 83% 65%)' }}>browse files</span>
        {' '}· PDF only
      </p>

      {/* Phase 4 badge */}
      <div className="mt-5 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-violet-500/10 border border-violet-500/20">
        <Zap size={11} className="text-violet-400" />
        <span className="text-[10px] font-extrabold text-violet-400 uppercase tracking-wider">AI Detection in Phase 4</span>
      </div>
    </motion.div>
  )
}

// ─── Job card ─────────────────────────────────────────────────────────────────

function JobCard({ job, onRemove }: { job: BlueprintJob; onRemove: (id: string) => void }) {
  const cfg = STATUS[job.status]
  const StatusIcon = cfg.icon

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      transition={{ duration: 0.18 }}
      className="card p-4 flex items-center gap-4"
    >
      {/* File icon */}
      <div className="w-10 h-10 rounded-xl bg-white/[0.04] border border-white/[0.07] flex items-center justify-center shrink-0">
        <FileText size={18} className="text-zinc-500" />
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="font-semibold text-zinc-200 text-sm truncate">{job.filename}</div>
        <div className="text-[11px] text-zinc-600 mt-0.5">
          {job.pages} pages · {job.uploadedAt.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
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

      {/* Remove */}
      <button
        onClick={() => onRemove(job.id)}
        className="flex min-h-[32px] min-w-[32px] items-center justify-center rounded-lg p-2 hover:bg-white/[0.07] text-zinc-600 hover:text-zinc-300 transition-colors shrink-0"
        aria-label={`Remove ${job.filename}`}
      >
        <X size={14} />
      </button>
    </motion.div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function BlueprintsPage() {
  const [jobs, setJobs] = useState<BlueprintJob[]>([])
  const [confirmClearAll, setConfirmClearAll] = useState(false)

  const handleFiles = useCallback((files: File[]) => {
    const newJobs: BlueprintJob[] = files.map(file => ({
      id: crypto.randomUUID(),
      filename: file.name,
      pages: 0,
      status: 'queued' as const,
      uploadedAt: new Date(),
    }))
    setJobs(prev => [...newJobs, ...prev])

    // Simulate processing progression (Phase 4 will use real backend)
    newJobs.forEach(job => {
      setTimeout(() => {
        setJobs(prev => prev.map(j =>
          j.id === job.id ? { ...j, status: 'processing', pages: Math.floor(Math.random() * 12) + 1 } : j
        ))
      }, 800)

      setTimeout(() => {
        setJobs(prev => prev.map(j =>
          j.id === job.id
            ? { ...j, status: 'done', message: undefined }
            : j
        ))
      }, 3500 + Math.random() * 1500)
    })
  }, [])

  const removeJob = useCallback((id: string) => {
    setJobs(prev => prev.filter(j => j.id !== id))
  }, [])

  const doneCount = jobs.filter(j => j.status === 'done').length
  const processingCount = jobs.filter(j => j.status === 'processing').length

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
              <p className="text-[11px] text-zinc-600">Upload PDFs for fixture detection and takeoff</p>
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
              {doneCount > 0 && (
                <span className="flex items-center gap-1 text-emerald-400 font-semibold">
                  <CheckCircle2 size={11} />
                  {doneCount} complete
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-4 space-y-4">

        {/* Phase 4 info banner */}
        <div className="flex items-start gap-3 p-4 rounded-2xl bg-violet-500/[0.04] border border-violet-500/15">
          <Zap size={16} className="text-violet-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-semibold text-zinc-300 mb-0.5">AI blueprint analysis coming in Phase 4</p>
            <p className="text-[11px] text-zinc-600 leading-relaxed">
              Upload your PDFs now to queue them. Phase 4 adds computer vision fixture detection, automatic takeoff generation, and direct estimate creation from detected items.
            </p>
          </div>
        </div>

        {/* Drop zone */}
        <DropZone onFiles={handleFiles} />

        {/* Capabilities preview */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
          {[
            { icon: Layers,       color: 'text-violet-400', bg: 'bg-violet-500/10 border-violet-500/20', title: 'Fixture Detection',  desc: 'AI counts toilets, WH, fixtures per page' },
            { icon: FolderOpen,   color: 'text-blue-400',   bg: 'bg-blue-500/10 border-blue-500/20',     title: 'Auto Takeoff',       desc: 'Generates material list from detected items' },
            { icon: FileText,     color: 'text-emerald-400',bg: 'bg-emerald-500/10 border-emerald-500/20',title: 'Instant Estimate',  desc: 'One click to full priced estimate' },
          ].map(({ icon: Icon, color, bg, title, desc }) => (
            <div key={title} className="card p-4 opacity-50">
              <div className={cn('w-8 h-8 rounded-xl border flex items-center justify-center mb-3', bg)}>
                <Icon size={15} className={color} />
              </div>
              <div className="text-xs font-bold text-zinc-300 mb-1">{title}</div>
              <div className="text-[11px] text-zinc-600 leading-relaxed">{desc}</div>
            </div>
          ))}
        </div>

        {/* Upload jobs */}
        {jobs.length > 0 && (
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
                  <JobCard key={job.id} job={job} onRemove={removeJob} />
                ))}
              </AnimatePresence>
            </div>

            <ConfirmDialog
              open={confirmClearAll}
              onClose={() => setConfirmClearAll(false)}
              onConfirm={() => { setJobs([]); setConfirmClearAll(false) }}
              title="Clear all uploads"
              description={`Remove all ${jobs.length} uploaded file${jobs.length !== 1 ? 's' : ''}? This cannot be undone.`}
              confirmLabel="Clear All"
              variant="danger"
            />
          </div>
        )}
      </div>
    </div>
  )
}
