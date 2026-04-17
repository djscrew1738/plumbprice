'use client'

import { useState, useCallback, type DragEvent } from 'react'
import { CircleDollarSign } from 'lucide-react'
import { type ProjectPipelineItem } from '@/lib/api'
import { cn, formatCurrency } from '@/lib/utils'
import { EmptyState } from '@/components/ui/EmptyState'
import { PipelineCard } from './PipelineCard'

export interface StageConfig {
  key: string
  label: string
  colClass: string
  countColor: string
  emptyColor: string
}

export interface PipelineColumnProps {
  stage: StageConfig
  projects: ProjectPipelineItem[]
  stageIndex: number
  stageKeys: readonly string[]
  onMoveProject: (id: number, newStatus: string) => Promise<void>
  onProjectDeleted?: (id: number) => void
}

export function PipelineColumn({
  stage,
  projects,
  stageIndex,
  stageKeys,
  onMoveProject,
  onProjectDeleted,
}: PipelineColumnProps) {
  const [isDragOver, setIsDragOver] = useState(false)

  const handleDragOver = useCallback((e: DragEvent<HTMLElement>) => {
    if (!e.dataTransfer.types.includes('application/x-pipeline-project')) return
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: DragEvent<HTMLElement>) => {
    // Only clear when leaving the column itself (not child elements)
    if (e.currentTarget.contains(e.relatedTarget as Node)) return
    setIsDragOver(false)
  }, [])

  const handleDrop = useCallback((e: DragEvent<HTMLElement>) => {
    e.preventDefault()
    setIsDragOver(false)

    const raw = e.dataTransfer.getData('application/x-pipeline-project')
    if (!raw) return

    try {
      const data = JSON.parse(raw) as { projectId: number; sourceStage: string }
      if (data.sourceStage === stage.key) return
      void onMoveProject(data.projectId, stage.key)
    } catch { /* ignore malformed data */ }
  }, [stage.key, onMoveProject])

  return (
    <section
      className={cn(
        'card p-4 min-h-[360px] transition-all duration-200',
        stage.colClass,
        isDragOver && 'border-2 border-dashed border-[color:var(--accent)] bg-[color:var(--accent)]/[0.04] scale-[1.01]',
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="flex items-center justify-between gap-2 mb-4">
        <div>
          <h2 className="text-xs font-bold text-[color:var(--ink)] uppercase tracking-wider">{stage.label}</h2>
          {projects.some(p => p.latest_estimate_total) && (
            <p className="text-[10px] text-[color:var(--muted-ink)] mt-0.5 tabular-nums">
              {formatCurrency(projects.reduce((s, p) => s + (p.latest_estimate_total ?? 0), 0))}
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
          {projects.length}
        </span>
      </div>

      <div className="space-y-2.5">
        {projects.length === 0 && (
          <EmptyState
            icon={<CircleDollarSign size={20} />}
            title={isDragOver ? 'Drop here' : 'Empty'}
            description={isDragOver ? `Move to ${stage.label}` : 'No jobs in this stage'}
            className={cn(
              'card rounded-2xl border border-dashed p-4',
              isDragOver && 'border-[color:var(--accent)] bg-[color:var(--accent)]/[0.06]',
            )}
          />
        )}
        {projects.map((project, projectIndex) => (
          <PipelineCard
            key={project.id}
            project={project}
            delay={stageIndex * 0.04 + projectIndex * 0.04}
            stageKeys={stageKeys}
            onMove={onMoveProject}
            onDeleted={onProjectDeleted}
          />
        ))}
      </div>
    </section>
  )
}
