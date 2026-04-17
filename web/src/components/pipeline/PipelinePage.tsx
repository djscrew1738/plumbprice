'use client'

import { useState, useCallback } from 'react'
import {
  CircleDollarSign, RefreshCw, TrendingUp, Plus,
} from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { projectsApi, type ProjectPipelineItem, type ProjectPipelineResponse } from '@/lib/api'
import { cn, formatCurrency } from '@/lib/utils'
import { PageIntro } from '@/components/layout/PageIntro'
import { useToast } from '@/components/ui/Toast'
import { EmptyState } from '@/components/ui/EmptyState'
import { PipelineColumn } from './PipelineColumn'
import { CreateProjectModal } from './CreateProjectModal'

const STAGES = [
  { key: 'lead', label: 'Lead', colClass: 'stage-lead', countColor: 'text-[color:var(--muted-ink)]', emptyColor: 'border-[color:var(--line)]' },
  { key: 'estimate_sent', label: 'Estimate Sent', colClass: 'stage-sent', countColor: 'text-blue-700', emptyColor: 'border-blue-500/20' },
  { key: 'won', label: 'Won', colClass: 'stage-won', countColor: 'text-emerald-700', emptyColor: 'border-emerald-500/20' },
  { key: 'lost', label: 'Lost', colClass: 'stage-lost', countColor: 'text-red-700', emptyColor: 'border-red-500/20' },
] as const

export function PipelinePage() {
  const toast = useToast()
  const queryClient = useQueryClient()
  const [showCreate,  setShowCreate]  = useState(false)

  const { data, isLoading: loading, error: queryError, refetch: load } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      const response = await projectsApi.list()
      return response.data
    },
  })

  const error = queryError ? 'Could not load pipeline' : null

  const moveProjectMutation = useMutation({
    mutationFn: async ({ projectId, newStatus }: { projectId: number; newStatus: string }) => {
      await projectsApi.update(projectId, { status: newStatus })
    },
    onMutate: async ({ projectId, newStatus }) => {
      await queryClient.cancelQueries({ queryKey: ['projects'] })
      const previous = queryClient.getQueryData<ProjectPipelineResponse>(['projects'])
      queryClient.setQueryData<ProjectPipelineResponse>(['projects'], prev => {
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
      return { previous }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['projects'], context.previous)
      }
      toast.error('Could not move project', 'Refreshing pipeline…')
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })

  const moveProject = useCallback(async (projectId: number, newStatus: string) => {
    moveProjectMutation.mutate({ projectId, newStatus })
  }, [moveProjectMutation])

  const handleProjectCreated = useCallback((_project: ProjectPipelineItem) => {
    setShowCreate(false)
    void queryClient.invalidateQueries({ queryKey: ['projects'] })
    toast.success('Project created', _project.name)
  }, [toast, queryClient])

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

        {/* Kanban columns */}
        {!loading && !error && projects.length > 0 && (
          <div className="grid grid-cols-1 xl:grid-cols-4 gap-4 items-start">
            {STAGES.map((stage, stageIndex) => (
              <PipelineColumn
                key={stage.key}
                stage={stage}
                projects={projects.filter(p => p.status === stage.key)}
                stageIndex={stageIndex}
                stageKeys={stageKeys}
                onMoveProject={moveProject}
              />
            ))}
          </div>
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
