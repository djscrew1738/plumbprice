'use client'

import { useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  BriefcaseBusiness, CircleDollarSign, MapPin, RefreshCw,
  UserRound, TrendingUp, ChevronLeft, ChevronRight, Plus, X, Check,
} from 'lucide-react'
import { projectsApi, type ProjectPipelineItem, type ProjectPipelineResponse } from '@/lib/api'
import { cn, formatCurrency } from '@/lib/utils'
import { PageIntro } from '@/components/layout/PageIntro'
import { useToast } from '@/components/ui/Toast'

const STAGES = [
  { key: 'lead', label: 'Lead', colClass: 'stage-lead', countColor: 'text-[color:var(--muted-ink)]', emptyColor: 'border-[color:var(--line)]' },
  { key: 'estimate_sent', label: 'Estimate Sent', colClass: 'stage-sent', countColor: 'text-blue-700', emptyColor: 'border-blue-500/20' },
  { key: 'won', label: 'Won', colClass: 'stage-won', countColor: 'text-emerald-700', emptyColor: 'border-emerald-500/20' },
  { key: 'lost', label: 'Lost', colClass: 'stage-lost', countColor: 'text-red-700', emptyColor: 'border-red-500/20' },
] as const

export function PipelinePage() {
  const toast = useToast()
  const [data,        setData]        = useState<ProjectPipelineResponse | null>(null)
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState<string | null>(null)
  const [showCreate,  setShowCreate]  = useState(false)

  const load = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await projectsApi.list()
      setData(response.data)
    } catch {
      setError('Could not load pipeline')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const moveProject = useCallback(async (projectId: number, newStatus: string) => {
    // Optimistic update
    setData(prev => {
      if (!prev) return prev
      return {
        ...prev,
        projects: prev.projects.map(p =>
          p.id === projectId ? { ...p, status: newStatus } : p
        ),
        summary: (() => {
          const old = prev.projects.find(p => p.id === projectId)
          if (!old) return prev.summary
          const s = { ...prev.summary }
          s[old.status] = Math.max(0, (s[old.status] ?? 1) - 1)
          s[newStatus] = (s[newStatus] ?? 0) + 1
          return s
        })(),
      }
    })
    try {
      await projectsApi.update(projectId, { status: newStatus })
    } catch {
      toast.error('Could not move project', 'Refreshing pipeline…')
      void load()
    }
  }, [load, toast])

  const handleProjectCreated = useCallback((project: ProjectPipelineItem) => {
    setShowCreate(false)
    setData(prev => {
      if (!prev) return { projects: [project], summary: { lead: 1 } }
      return {
        ...prev,
        projects: [project, ...prev.projects],
        summary: { ...prev.summary, lead: (prev.summary['lead'] ?? 0) + 1 },
      }
    })
    toast.success('Project created', project.name)
  }, [toast])

  const stageKeys = STAGES.map(s => s.key)
  const projects = data?.projects ?? []
  const summary  = data?.summary  ?? {}

  const totalPipelineValue = projects
    .filter(p => p.status !== 'lost')
    .reduce((s, p) => s + (p.latest_estimate_total ?? 0), 0)

  const closedCount = (summary['won'] ?? 0) + (summary['lost'] ?? 0)
  const winRate = closedCount > 0 ? Math.round(((summary['won'] ?? 0) / closedCount) * 100) : null

  return (
    <div className="min-h-full">
      <div className="mx-auto w-full max-w-7xl px-4 py-5 sm:px-6 lg:px-8">
        <PageIntro
          eyebrow="Sales Pipeline"
          title="Track bid movement from lead to close."
          description="Watch stage counts, win rate, and total open value in one view."
          actions={(
            <div className="flex items-center gap-2">
              <button
                onClick={() => void load()}
                disabled={loading}
                className="btn-secondary min-h-0 py-2"
              >
                <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                <span className="hidden sm:inline">Refresh</span>
              </button>
              <button
                onClick={() => setShowCreate(true)}
                className="btn-primary min-h-0 py-2"
              >
                <Plus size={14} />
                <span className="hidden sm:inline">New Project</span>
              </button>
            </div>
          )}
        >
          <div className="flex flex-wrap items-center gap-2.5">
            {STAGES.map(stage => (
              <span key={stage.key} className="shell-chip">
                <span>{stage.label}</span>
                <span className={cn('font-semibold tabular-nums', stage.countColor)}>
                  {summary[stage.key] ?? 0}
                </span>
              </span>
            ))}
            {winRate !== null && (
              <span className="shell-chip">
                <TrendingUp size={13} className="text-emerald-700" />
                <span className="text-emerald-700 font-semibold">{winRate}% win rate</span>
              </span>
            )}
            {totalPipelineValue > 0 && (
              <span className="shell-chip">
                <CircleDollarSign size={13} className="text-blue-700" />
                <span className="font-semibold text-[color:var(--ink)]">{formatCurrency(totalPipelineValue)}</span>
                <span>open pipeline</span>
              </span>
            )}
          </div>
        </PageIntro>

        <div className="mt-4">

        {/* Loading */}
        {loading && (
          <div className="grid grid-cols-1 xl:grid-cols-4 gap-4">
            {STAGES.map(stage => (
              <div key={stage.key} className={cn('card p-4 space-y-3', stage.colClass)}>
                <div className="skeleton h-3.5 w-1/2 rounded-lg" />
                {[1,2].map(i => <div key={i} className="skeleton h-28 rounded-2xl" />)}
              </div>
            ))}
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div className="card p-10 text-center">
            <p className="text-red-700 font-medium text-sm mb-3">{error}</p>
            <button onClick={() => void load()} className="btn-primary mx-auto">Retry</button>
          </div>
        )}

        {/* Empty */}
        {!loading && !error && projects.length === 0 && (
          <div className="card p-12 text-center">
            <CircleDollarSign size={28} className="mx-auto text-[color:var(--muted-ink)] mb-4" />
            <h3 className="text-base font-bold text-[color:var(--ink)] mb-2">No opportunities yet</h3>
            <p className="text-sm text-[color:var(--muted-ink)] max-w-xs mx-auto">
              Create jobs through the estimator or API to populate the pipeline.
            </p>
          </div>
        )}

        {/* Kanban columns */}
        {!loading && !error && projects.length > 0 && (
          <div className="grid grid-cols-1 xl:grid-cols-4 gap-4 items-start">
            {STAGES.map((stage, stageIndex) => {
              const stageProjects = projects.filter(p => p.status === stage.key)
              return (
                <section
                  key={stage.key}
                  className={cn('card p-4 min-h-[360px]', stage.colClass)}
                >
                  <div className="flex items-center justify-between gap-2 mb-4">
                    <div>
                      <h2 className="text-xs font-bold text-[color:var(--ink)] uppercase tracking-wider">{stage.label}</h2>
                      {stageProjects.some(p => p.latest_estimate_total) && (
                        <p className="text-[10px] text-[color:var(--muted-ink)] mt-0.5 tabular-nums">
                          {formatCurrency(stageProjects.reduce((s, p) => s + (p.latest_estimate_total ?? 0), 0))}
                        </p>
                      )}
                    </div>
                    <span className={cn(
                      'text-xs font-bold tabular-nums px-2 py-0.5 rounded-full',
                      stage.key === 'won' && 'bg-emerald-500/10 text-emerald-700 border border-emerald-500/20',
                      stage.key === 'lost' && 'bg-red-500/10 text-red-700 border border-red-500/20',
                      stage.key === 'estimate_sent' && 'bg-blue-500/10 text-blue-700 border border-blue-500/20',
                      stage.key === 'lead' && 'bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)] border border-[color:var(--line)]',
                    )}>
                      {stageProjects.length}
                    </span>
                  </div>

                  <div className="space-y-2.5">
                    {stageProjects.length === 0 && (
                      <div className={cn(
                        'rounded-2xl border border-dashed p-6 text-xs text-[color:var(--muted-ink)] text-center',
                        stage.emptyColor,
                      )}>
                        No jobs in this stage
                      </div>
                    )}
                    {stageProjects.map((project, projectIndex) => (
                      <ProjectCard
                        key={project.id}
                        project={project}
                        delay={stageIndex * 0.04 + projectIndex * 0.04}
                        stageKeys={stageKeys}
                        onMove={moveProject}
                      />
                    ))}
                  </div>
                </section>
              )
            })}
          </div>
        )}
        </div>
      </div>

      {/* Create Project Modal */}
      <AnimatePresence>
        {showCreate && (
          <CreateProjectModal
            onClose={() => setShowCreate(false)}
            onCreated={handleProjectCreated}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

function ProjectCard({
  project,
  delay,
  stageKeys,
  onMove,
}: {
  project: ProjectPipelineItem
  delay: number
  stageKeys: readonly string[]
  onMove: (id: number, newStatus: string) => Promise<void>
}) {
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
        'rounded-2xl border bg-[color:var(--panel)] p-3.5 space-y-3 transition-colors hover:bg-[color:var(--panel-strong)]',
        project.status === 'won' && 'border-emerald-500/20 bg-emerald-500/[0.04]',
        project.status === 'lost' && 'border-red-500/20 bg-red-500/[0.03]',
        project.status === 'estimate_sent' && 'border-blue-500/20 bg-blue-500/[0.03]',
        project.status === 'lead' && 'border-[color:var(--line)]',
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-[color:var(--ink)] truncate leading-snug">{project.name}</div>
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
        <span className="text-[color:var(--muted-ink)]">
          {project.estimate_count} {project.estimate_count === 1 ? 'estimate' : 'estimates'}
        </span>
        <div className="flex items-center gap-1">
          {project.status === 'won' && (
            <span className="text-emerald-700 font-bold mr-1">Won ✓</span>
          )}
          {project.status === 'lost' && (
            <span className="text-red-700 font-bold mr-1">Lost</span>
          )}
          {canBack && (
            <button
              onClick={() => void move('back')}
              disabled={moving}
              className="p-1 rounded-lg text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] hover:bg-[color:var(--panel-strong)] transition-colors disabled:opacity-40"
              aria-label="Move to previous stage"
              title="Move back"
            >
              <ChevronLeft size={13} />
            </button>
          )}
          {canForward && (
            <button
              onClick={() => void move('forward')}
              disabled={moving}
              className="p-1 rounded-lg text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] hover:bg-[color:var(--panel-strong)] transition-colors disabled:opacity-40"
              aria-label="Move to next stage"
              title="Advance stage"
            >
              <ChevronRight size={13} />
            </button>
          )}
        </div>
      </div>
    </motion.article>
  )
}

// ─── Create Project Modal ─────────────────────────────────────────────────────

const JOB_TYPES = ['service', 'construction', 'commercial']
const COUNTIES  = ['Dallas', 'Tarrant', 'Collin', 'Denton', 'Rockwall', 'Parker']

function CreateProjectModal({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: (p: ProjectPipelineItem) => void
}) {
  const toast = useToast()
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    name: '',
    job_type: 'service',
    customer_name: '',
    county: 'Dallas',
    notes: '',
  })

  const set = (field: string, val: string) =>
    setForm(prev => ({ ...prev, [field]: val }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) return
    setSaving(true)
    try {
      const res = await projectsApi.create({
        name:          form.name.trim(),
        job_type:      form.job_type,
        customer_name: form.customer_name.trim() || undefined,
        county:        form.county,
        notes:         form.notes.trim() || undefined,
      })
      // API may return the new project directly or nested
      const raw = res.data as unknown as { project?: ProjectPipelineItem } | ProjectPipelineItem
      const project = ('project' in raw && raw.project) ? raw.project : raw as ProjectPipelineItem
      onCreated(project)
    } catch {
      toast.error('Could not create project', 'Please try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
        onClick={onClose}
      />
      {/* Panel */}
      <motion.div
        initial={{ opacity: 0, scale: 0.96, y: 16 }}
        animate={{ opacity: 1, scale: 1,    y: 0  }}
        exit={{   opacity: 0, scale: 0.96,  y: 16 }}
        transition={{ duration: 0.18 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        onClick={e => e.stopPropagation()}
      >
        <form
          onSubmit={e => void handleSubmit(e)}
          className="w-full max-w-md bg-[color:var(--panel)] border border-[color:var(--line)] rounded-2xl shadow-2xl overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-[color:var(--line)]">
            <h2 className="text-sm font-bold text-[color:var(--ink)]">New Project</h2>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] hover:bg-[color:var(--panel-strong)] transition-colors"
            >
              <X size={15} />
            </button>
          </div>

          {/* Body */}
          <div className="px-5 py-4 space-y-4">
            {/* Name */}
            <div>
              <label className="block text-xs font-semibold text-[color:var(--muted-ink)] mb-1.5">
                Project Name <span className="text-red-500">*</span>
              </label>
              <input
                autoFocus
                value={form.name}
                onChange={e => set('name', e.target.value)}
                placeholder="e.g. 123 Main St — Water Heater"
                className="w-full px-3 py-2 bg-[color:var(--panel-strong)] border border-[color:var(--line)] rounded-xl text-sm text-[color:var(--ink)] placeholder-[color:var(--muted-ink)] focus:outline-none focus:ring-2 focus:ring-blue-500/30 transition"
                required
              />
            </div>

            {/* Job type + County */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-[color:var(--muted-ink)] mb-1.5">Job Type</label>
                <select
                  value={form.job_type}
                  onChange={e => set('job_type', e.target.value)}
                  className="w-full px-3 py-2 bg-[color:var(--panel-strong)] border border-[color:var(--line)] rounded-xl text-sm text-[color:var(--ink)] focus:outline-none focus:ring-2 focus:ring-blue-500/30 transition"
                >
                  {JOB_TYPES.map(t => (
                    <option key={t} value={t} className="capitalize">{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-[color:var(--muted-ink)] mb-1.5">County</label>
                <select
                  value={form.county}
                  onChange={e => set('county', e.target.value)}
                  className="w-full px-3 py-2 bg-[color:var(--panel-strong)] border border-[color:var(--line)] rounded-xl text-sm text-[color:var(--ink)] focus:outline-none focus:ring-2 focus:ring-blue-500/30 transition"
                >
                  {COUNTIES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            </div>

            {/* Customer */}
            <div>
              <label className="block text-xs font-semibold text-[color:var(--muted-ink)] mb-1.5">Customer Name</label>
              <input
                value={form.customer_name}
                onChange={e => set('customer_name', e.target.value)}
                placeholder="Optional"
                className="w-full px-3 py-2 bg-[color:var(--panel-strong)] border border-[color:var(--line)] rounded-xl text-sm text-[color:var(--ink)] placeholder-[color:var(--muted-ink)] focus:outline-none focus:ring-2 focus:ring-blue-500/30 transition"
              />
            </div>

            {/* Notes */}
            <div>
              <label className="block text-xs font-semibold text-[color:var(--muted-ink)] mb-1.5">Notes</label>
              <textarea
                value={form.notes}
                onChange={e => set('notes', e.target.value)}
                placeholder="Optional job notes…"
                rows={2}
                className="w-full px-3 py-2 bg-[color:var(--panel-strong)] border border-[color:var(--line)] rounded-xl text-sm text-[color:var(--ink)] placeholder-[color:var(--muted-ink)] focus:outline-none focus:ring-2 focus:ring-blue-500/30 transition resize-none"
              />
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-2 px-5 py-3.5 border-t border-[color:var(--line)] bg-[color:var(--panel-strong)]">
            <button type="button" onClick={onClose} className="btn-secondary min-h-0 py-2">
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || !form.name.trim()}
              className="btn-primary min-h-0 py-2 disabled:opacity-50"
            >
              {saving ? (
                <RefreshCw size={13} className="animate-spin" />
              ) : (
                <Check size={13} />
              )}
              {saving ? 'Creating…' : 'Create Project'}
            </button>
          </div>
        </form>
      </motion.div>
    </>
  )
}
