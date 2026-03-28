'use client'

import { useEffect, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { BriefcaseBusiness, CircleDollarSign, MapPin, RefreshCw, UserRound, TrendingUp } from 'lucide-react'
import { projectsApi, type ProjectPipelineItem, type ProjectPipelineResponse } from '@/lib/api'
import { cn, formatCurrency } from '@/lib/utils'

const STAGES = [
  { key: 'lead',          label: 'Lead',          colClass: 'stage-lead',  countColor: 'text-zinc-400',    emptyColor: 'border-zinc-700/40' },
  { key: 'estimate_sent', label: 'Estimate Sent',  colClass: 'stage-sent',  countColor: 'text-blue-400',    emptyColor: 'border-blue-500/20' },
  { key: 'won',           label: 'Won',            colClass: 'stage-won',   countColor: 'text-emerald-400', emptyColor: 'border-emerald-500/20' },
  { key: 'lost',          label: 'Lost',           colClass: 'stage-lost',  countColor: 'text-red-400',     emptyColor: 'border-red-500/20' },
] as const

export function PipelinePage() {
  const [data,    setData]    = useState<ProjectPipelineResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)

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

  const projects = data?.projects ?? []
  const summary  = data?.summary  ?? {}

  const totalPipelineValue = projects
    .filter(p => p.status !== 'lost')
    .reduce((s, p) => s + (p.latest_estimate_total ?? 0), 0)

  const closedCount = (summary['won'] ?? 0) + (summary['lost'] ?? 0)
  const winRate = closedCount > 0 ? Math.round(((summary['won'] ?? 0) / closedCount) * 100) : null

  return (
    <div className="min-h-full bg-[#080808]">

      {/* ── Header bar ── */}
      <div className="bg-[#080808]/80 backdrop-blur-xl border-b border-white/[0.06] px-4 py-3 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-4 overflow-x-auto scrollbar-hide">
            {/* Stage counts */}
            {STAGES.map(stage => (
              <div key={stage.key} className="flex items-center gap-2 shrink-0">
                <span className="text-[11px] text-zinc-600 font-medium whitespace-nowrap">{stage.label}</span>
                <span className={cn('text-sm font-bold tabular-nums', stage.countColor)}>
                  {summary[stage.key] ?? 0}
                </span>
              </div>
            ))}
            {winRate !== null && (
              <>
                <div className="w-px h-5 bg-white/[0.06] shrink-0" />
                <div className="flex items-center gap-1.5 shrink-0">
                  <TrendingUp size={13} className="text-emerald-400" />
                  <span className="text-sm font-bold text-emerald-400">{winRate}%</span>
                  <span className="text-[11px] text-zinc-600">win rate</span>
                </div>
              </>
            )}
            {totalPipelineValue > 0 && (
              <>
                <div className="w-px h-5 bg-white/[0.06] shrink-0" />
                <div className="flex items-center gap-1.5 shrink-0">
                  <CircleDollarSign size={13} className="text-blue-400" />
                  <span className="text-sm font-bold text-white">{formatCurrency(totalPipelineValue)}</span>
                  <span className="text-[11px] text-zinc-600">pipeline</span>
                </div>
              </>
            )}
          </div>
          <button
            onClick={() => void load()}
            disabled={loading}
            className="btn-secondary shrink-0 py-2"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-4">

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
            <p className="text-red-400 font-medium text-sm mb-3">{error}</p>
            <button onClick={() => void load()} className="btn-primary mx-auto">Retry</button>
          </div>
        )}

        {/* Empty */}
        {!loading && !error && projects.length === 0 && (
          <div className="card p-12 text-center">
            <CircleDollarSign size={28} className="mx-auto text-zinc-700 mb-4" />
            <h3 className="text-base font-bold text-white mb-2">No opportunities yet</h3>
            <p className="text-sm text-zinc-600 max-w-xs mx-auto">
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
                    <h2 className="text-xs font-bold text-white uppercase tracking-wider">{stage.label}</h2>
                    <span className={cn(
                      'text-xs font-bold tabular-nums px-2 py-0.5 rounded-full',
                      stage.key === 'won'  && 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
                      stage.key === 'lost' && 'bg-red-500/10 text-red-400 border border-red-500/20',
                      stage.key === 'estimate_sent' && 'bg-blue-500/10 text-blue-400 border border-blue-500/20',
                      stage.key === 'lead' && 'bg-white/[0.04] text-zinc-500 border border-white/[0.08]',
                    )}>
                      {stageProjects.length}
                    </span>
                  </div>

                  <div className="space-y-2.5">
                    {stageProjects.length === 0 && (
                      <div className={cn(
                        'rounded-2xl border border-dashed p-6 text-xs text-zinc-700 text-center',
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
  )
}

function ProjectCard({ project, delay }: { project: ProjectPipelineItem; delay: number }) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18, delay }}
      className={cn(
        'rounded-2xl border bg-[#0c0c0c] p-3.5 space-y-3 hover:border-white/10 transition-colors',
        project.status === 'won'  && 'border-emerald-500/20 bg-emerald-500/[0.03]',
        project.status === 'lost' && 'border-red-500/15 bg-red-500/[0.02]',
        project.status === 'estimate_sent' && 'border-blue-500/15 bg-blue-500/[0.02]',
        project.status === 'lead' && 'border-white/[0.07]',
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-white truncate leading-snug">{project.name}</div>
          <div className="flex items-center gap-1 mt-1">
            <BriefcaseBusiness size={11} className="text-zinc-600 shrink-0" />
            <span className="text-[11px] text-zinc-600 capitalize">{project.job_type}</span>
          </div>
        </div>
        <div className="text-right shrink-0">
          {project.latest_estimate_total != null ? (
            <div className="text-sm font-bold text-white tabular-nums">
              {formatCurrency(project.latest_estimate_total)}
            </div>
          ) : (
            <div className="text-xs text-zinc-700 font-medium">Open</div>
          )}
        </div>
      </div>

      {/* Details */}
      <div className="grid grid-cols-2 gap-1.5 text-xs">
        <div className="card-inset px-2.5 py-2">
          <div className="flex items-center gap-1 text-zinc-600 mb-0.5">
            <UserRound size={10} />
            <span className="text-[10px]">Customer</span>
          </div>
          <div className="text-zinc-300 font-medium truncate">{project.customer_name || '—'}</div>
        </div>
        <div className="card-inset px-2.5 py-2">
          <div className="flex items-center gap-1 text-zinc-600 mb-0.5">
            <MapPin size={10} />
            <span className="text-[10px]">County</span>
          </div>
          <div className="text-zinc-300 font-medium truncate">{project.county}</div>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-zinc-700">
          {project.estimate_count} {project.estimate_count === 1 ? 'estimate' : 'estimates'}
        </span>
        {project.status === 'won' && (
          <span className="text-emerald-400 font-bold">Won ✓</span>
        )}
        {project.status === 'lost' && (
          <span className="text-red-500 font-bold">Lost</span>
        )}
      </div>
    </motion.article>
  )
}
