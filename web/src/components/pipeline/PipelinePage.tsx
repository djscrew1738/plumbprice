'use client'

import { useState, useCallback, useMemo, useDeferredValue, useEffect } from 'react'
import {
  CircleDollarSign, RefreshCw, TrendingUp, Plus, X, GripVertical,
} from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { type ProjectPipelineItem, type ProjectPipelineResponse } from '@/lib/api'
import { usePipeline, useMoveProject, pipelineKeys } from '@/lib/hooks'
import { cn, formatCurrency } from '@/lib/utils'
import { PageIntro } from '@/components/layout/PageIntro'
import { useToast } from '@/components/ui/Toast'
import { EmptyState } from '@/components/ui/EmptyState'
import { SearchInput } from '@/components/ui/SearchInput'
import { Select, type SelectOption } from '@/components/ui/Select'
import { PipelineColumn } from './PipelineColumn'
import { CreateProjectModal } from './CreateProjectModal'

const STAGES = [
  { key: 'lead', label: 'Lead', colClass: 'stage-lead', countColor: 'text-[color:var(--muted-ink)]', emptyColor: 'border-[color:var(--line)]' },
  { key: 'estimate_sent', label: 'Estimate Sent', colClass: 'stage-sent', countColor: 'text-blue-700', emptyColor: 'border-blue-500/20' },
  { key: 'won', label: 'Won', colClass: 'stage-won', countColor: 'text-emerald-700', emptyColor: 'border-emerald-500/20' },
  { key: 'lost', label: 'Lost', colClass: 'stage-lost', countColor: 'text-red-700', emptyColor: 'border-red-500/20' },
] as const

const JOB_TYPE_OPTIONS: SelectOption[] = [
  { value: '', label: 'All Job Types' },
  { value: 'service', label: 'Service' },
  { value: 'construction', label: 'Construction' },
  { value: 'commercial', label: 'Commercial' },
]

export function PipelinePage() {
  const toast = useToast()
  const queryClient = useQueryClient()
  const [showCreate,  setShowCreate]  = useState(false)
  const [showDragHint, setShowDragHint] = useState(false)

  useEffect(() => {
    const seen = localStorage.getItem('pipeline_drag_hint_seen')
    if (!seen) setShowDragHint(true)
  }, [])

  const dismissDragHint = useCallback(() => {
    localStorage.setItem('pipeline_drag_hint_seen', '1')
    setShowDragHint(false)
  }, [])

  // Filter state
  const [searchQuery, setSearchQuery] = useState('')
  const [jobTypeFilter, setJobTypeFilter] = useState('')
  const deferredSearch = useDeferredValue(searchQuery)

  const { data, isLoading: loading, error: queryError, refetch: load } = usePipeline()

  const error = queryError ? 'Could not load pipeline' : null

  const moveProjectMutation = useMoveProject()

  const moveProject = useCallback(async (projectId: number, newStatus: string) => {
    moveProjectMutation.mutate({ projectId, newStatus }, {
      onError: () => toast.error('Could not move project', 'Refreshing pipeline…'),
    })
  }, [moveProjectMutation, toast])

  const handleProjectCreated = useCallback((_project: ProjectPipelineItem) => {
    setShowCreate(false)
    void queryClient.invalidateQueries({ queryKey: ['projects'] })
    toast.success('Project created', _project.name)
  }, [toast, queryClient])

  const handleProjectDeleted = useCallback((projectId: number) => {
    queryClient.setQueryData<ProjectPipelineResponse>(pipelineKeys.all, prev => {
      if (!prev) return prev
      const removed = prev.projects.find(p => p.id === projectId)
      return {
        ...prev,
        projects: prev.projects.filter(p => p.id !== projectId),
        summary: removed
          ? { ...prev.summary, [removed.status]: Math.max(0, (prev.summary[removed.status] ?? 1) - 1) }
          : prev.summary,
      }
    })
    void queryClient.invalidateQueries({ queryKey: pipelineKeys.all })
  }, [queryClient])

  const stageKeys = useMemo(() => STAGES.map(s => s.key), [])
  const projects = useMemo(() => data?.projects ?? [], [data?.projects])
  const summary  = data?.summary  ?? {}

  // Apply client-side filters
  const filteredProjects = useMemo(() => {
    let result = projects

    if (deferredSearch.trim()) {
      const q = deferredSearch.toLowerCase()
      result = result.filter(p =>
        p.name.toLowerCase().includes(q) ||
        (p.customer_name && p.customer_name.toLowerCase().includes(q))
      )
    }

    if (jobTypeFilter) {
      result = result.filter(p => p.job_type === jobTypeFilter)
    }

    return result
  }, [projects, deferredSearch, jobTypeFilter])

  const hasActiveFilters = searchQuery.trim() !== '' || jobTypeFilter !== ''
  const isFiltered = hasActiveFilters && filteredProjects.length !== projects.length

  const clearFilters = useCallback(() => {
    setSearchQuery('')
    setJobTypeFilter('')
  }, [])

  const totalPipelineValue = useMemo(() =>
    projects
      .filter(p => p.status !== 'lost')
      .reduce((s, p) => s + (p.latest_estimate_total ?? 0), 0),
    [projects]
  )

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
                aria-label="Refresh pipeline"
                className="btn-secondary min-h-0 py-2"
              >
                <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                <span className="hidden sm:inline">Refresh</span>
              </button>
              <button
                onClick={() => setShowCreate(true)}
                aria-label="Create new project"
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

        {/* Filter bar */}
        {!loading && !error && projects.length > 0 && (
          <div className="mb-4 card p-3">
            <div className="flex flex-wrap items-end gap-3">
              <SearchInput
                value={searchQuery}
                onChange={setSearchQuery}
                placeholder="Search projects or customers…"
                className="flex-1 min-w-[200px]"
                aria-label="Search pipeline projects"
              />
              <Select
                options={JOB_TYPE_OPTIONS}
                value={jobTypeFilter}
                onChange={setJobTypeFilter}
                placeholder="All Job Types"
                size="md"
                className="w-44"
              />
              {hasActiveFilters && (
                <button
                  onClick={clearFilters}
                  className="btn-secondary min-h-0 py-2 flex items-center gap-1.5"
                >
                  <X size={13} />
                  Clear
                </button>
              )}
              <span className="text-xs text-[color:var(--muted-ink)] ml-auto tabular-nums whitespace-nowrap">
                {isFiltered
                  ? `Showing ${filteredProjects.length} of ${projects.length} projects`
                  : `${projects.length} projects`}
              </span>
            </div>
          </div>
        )}

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
          <EmptyState
            icon={<CircleDollarSign size={28} />}
            title="No opportunities yet"
            description="Create jobs through the estimator or API to populate the pipeline."
            className="card"
          />
        )}

        {/* No filter results */}
        {!loading && !error && projects.length > 0 && filteredProjects.length === 0 && hasActiveFilters && (
          <EmptyState
            icon={<CircleDollarSign size={28} />}
            title="No matching projects"
            description="Try adjusting your search or filters."
            className="card"
          />
        )}

        {/* Kanban columns */}
        {!loading && !error && filteredProjects.length > 0 && (
          <>
            {showDragHint && (
              <div className="mb-3 flex items-center gap-2.5 rounded-xl bg-[color:var(--accent-soft)] border border-[color:var(--accent)]/30 px-4 py-2.5">
                <GripVertical size={14} className="text-[color:var(--accent-strong)] shrink-0" />
                <p className="text-xs text-[color:var(--accent-strong)] font-medium flex-1">
                  Drag cards between columns to move projects through the pipeline.
                </p>
                <button
                  onClick={dismissDragHint}
                  className="min-h-[32px] min-w-[32px] flex items-center justify-center rounded-lg text-[color:var(--accent-strong)] hover:bg-[color:var(--accent)]/10 transition-colors"
                  aria-label="Dismiss hint"
                >
                  <X size={13} />
                </button>
              </div>
            )}
            <div className="grid grid-cols-1 xl:grid-cols-4 gap-4 items-start">
            {STAGES.map((stage, stageIndex) => (
              <PipelineColumn
                key={stage.key}
                stage={stage}
                projects={filteredProjects.filter(p => p.status === stage.key)}
                stageIndex={stageIndex}
                stageKeys={stageKeys}
                onMoveProject={moveProject}
                onProjectDeleted={handleProjectDeleted}
              />
            ))}
            </div>
          </>
        )}
        </div>
      </div>

      <CreateProjectModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={handleProjectCreated}
      />
    </div>
  )
}
