'use client'

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
}

export function PipelineColumn({
  stage,
  projects,
  stageIndex,
  stageKeys,
  onMoveProject,
}: PipelineColumnProps) {
  return (
    <section className={cn('card p-4 min-h-[360px]', stage.colClass)}>
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
            title="Empty"
            description="No jobs in this stage"
            className="card rounded-2xl border border-dashed p-4"
          />
        )}
        {projects.map((project, projectIndex) => (
          <PipelineCard
            key={project.id}
            project={project}
            delay={stageIndex * 0.04 + projectIndex * 0.04}
            stageKeys={stageKeys}
            onMove={onMoveProject}
          />
        ))}
      </div>
    </section>
  )
}
