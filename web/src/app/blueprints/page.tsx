'use client'

import { useRef, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Layers, UploadCloud, FileText, X, Zap, ArrowRight } from 'lucide-react'
import { PageIntro } from '@/components/layout/PageIntro'
import { cn } from '@/lib/utils'

const ACCEPTED = '.pdf,.png,.jpg,.jpeg,.webp'
const MAX_MB = 20

export default function Blueprints() {
  const router = useRouter()
  const inputRef = useRef<HTMLInputElement>(null)
  const [file,    setFile]    = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [error,   setError]   = useState<string | null>(null)

  const handleFile = (f: File) => {
    setError(null)
    if (f.size > MAX_MB * 1024 * 1024) {
      setError(`File too large. Maximum size is ${MAX_MB} MB.`)
      return
    }
    const ext = f.name.split('.').pop()?.toLowerCase() ?? ''
    if (!['pdf','png','jpg','jpeg','webp'].includes(ext)) {
      setError('Unsupported file type. Upload a PDF or image.')
      return
    }
    setFile(f)
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }, [])

  const onDragOver = (e: React.DragEvent) => { e.preventDefault(); setDragging(true) }
  const onDragLeave = () => setDragging(false)

  const handleOpenInEstimator = () => {
    if (!file) return
    // Store the filename in sessionStorage so the estimator can display context
    sessionStorage.setItem('blueprint_filename', file.name)
    router.push('/estimator?entry=upload-job-files&blueprint=1')
  }

  return (
    <div className="min-h-full">
      <div className="mx-auto w-full max-w-3xl px-4 py-5 sm:px-6 lg:px-8">
        <PageIntro
          eyebrow="Blueprints"
          title="Upload job files for pricing."
          description="Drop a PDF or photo of plans, fixture schedules, or scope sheets — then take it straight to the estimator."
        />

        <div className="mt-4 space-y-4">
          {/* Drop zone */}
          <div
            onDrop={onDrop}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onClick={() => inputRef.current?.click()}
            className={cn(
              'card flex flex-col items-center justify-center gap-4 p-12 cursor-pointer transition-all border-2 border-dashed select-none',
              dragging
                ? 'border-blue-500/60 bg-blue-500/[0.06]'
                : 'border-[color:var(--line)] hover:border-blue-500/40 hover:bg-[color:var(--panel-strong)]',
            )}
          >
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPTED}
              className="hidden"
              onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
            />
            <div className={cn(
              'flex h-16 w-16 items-center justify-center rounded-2xl border transition-colors',
              dragging
                ? 'border-blue-500/40 bg-blue-500/15 text-blue-600'
                : 'border-[color:var(--line)] bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)]',
            )}>
              <UploadCloud size={28} />
            </div>
            <div className="text-center">
              <p className="text-sm font-semibold text-[color:var(--ink)]">
                {dragging ? 'Drop to upload' : 'Drag & drop or click to browse'}
              </p>
              <p className="mt-1 text-xs text-[color:var(--muted-ink)]">
                PDF, PNG, JPG, WEBP · up to {MAX_MB} MB
              </p>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-600">
              <span className="flex-1">{error}</span>
              <button onClick={() => setError(null)} className="shrink-0 hover:opacity-70"><X size={14} /></button>
            </div>
          )}

          {/* Selected file card */}
          {file && !error && (
            <div className="card p-4 flex items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-600">
                <FileText size={18} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-[color:var(--ink)] truncate">{file.name}</p>
                <p className="text-xs text-[color:var(--muted-ink)]">{(file.size / 1024).toFixed(0)} KB</p>
              </div>
              <button
                onClick={e => { e.stopPropagation(); setFile(null) }}
                className="p-1.5 rounded-lg text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] hover:bg-[color:var(--panel-strong)] transition-colors"
              >
                <X size={15} />
              </button>
            </div>
          )}

          {/* Actions */}
          {file && !error && (
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={handleOpenInEstimator}
                className="btn-primary flex-1"
              >
                <Zap size={15} />
                Open in Estimator
                <ArrowRight size={14} className="ml-auto" />
              </button>
            </div>
          )}

          {/* Info callout */}
          <div className="card-inset p-4 flex items-start gap-3">
            <Layers size={16} className="text-[color:var(--muted-ink)] shrink-0 mt-0.5" />
            <p className="text-xs text-[color:var(--muted-ink)] leading-relaxed">
              <strong className="text-[color:var(--ink)]">Phase 2 feature:</strong> Automated PDF fixture detection and quantity extraction is in development.
              For now, upload your file and describe the scope in the estimator chat to get accurate pricing.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
