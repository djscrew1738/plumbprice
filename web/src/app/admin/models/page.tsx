'use client'

/**
 * ML Model Registry — /admin/models
 *
 * Displays model versions (production / shadow / retired), shadow eval metrics,
 * and promote/retire actions for admin users.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Brain, CheckCircle, Clock, Archive, AlertCircle, ArrowUpCircle } from 'lucide-react'
import { apiV3 } from '@/lib/api-v3'
import { Skeleton } from '@/components/ui/Skeleton'

// ─── Types ────────────────────────────────────────────────────────────────────

interface MLModel {
  id: number
  model_id: string
  base_model: string
  training_samples: number
  eval_score: number | null
  shadow_calls: number
  shadow_match_rate: number | null
  status: 'shadow' | 'production' | 'retired'
  created_at: string
}

interface ModelsResponse {
  models: MLModel[]
  baseline_match_rate: number | null
}

// ─── API helpers ──────────────────────────────────────────────────────────────

function useMLModels() {
  return useQuery<ModelsResponse>({
    queryKey: ['ml-models'],
    queryFn: () => apiV3.get<ModelsResponse>('/ml/models').then((r) => r.data),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })
}

function usePromoteModel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiV3.post(`/ml/models/${id}/promote`),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['ml-models'] }),
  })
}

function useRetireModel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiV3.post(`/ml/models/${id}/retire`),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['ml-models'] }),
  })
}

// ─── Sub-components ───────────────────────────────────────────────────────────

const STATUS_CONFIG = {
  production: {
    label: 'Production',
    icon: CheckCircle,
    bg: 'bg-green-100',
    text: 'text-green-700',
    ring: 'border-green-200',
  },
  shadow: {
    label: 'Shadow (10% traffic)',
    icon: Clock,
    bg: 'bg-yellow-100',
    text: 'text-yellow-700',
    ring: 'border-yellow-200',
  },
  retired: {
    label: 'Retired',
    icon: Archive,
    bg: 'bg-surface-2',
    text: 'text-muted-foreground',
    ring: 'border-border-subtle',
  },
}

function ModelCard({
  model,
  baselineMatchRate,
  onPromote,
  onRetire,
}: {
  model: MLModel
  baselineMatchRate: number | null
  onPromote: () => void
  onRetire: () => void
}) {
  const cfg = STATUS_CONFIG[model.status]
  const StatusIcon = cfg.icon
  const canPromote =
    model.status === 'shadow' &&
    model.shadow_calls >= 100 &&
    model.shadow_match_rate != null &&
    (baselineMatchRate == null || model.shadow_match_rate > baselineMatchRate + 0.05)

  return (
    <div className={`rounded-xl border bg-card p-5 space-y-4 ${cfg.ring}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <Brain className="h-5 w-5 text-brand flex-shrink-0" />
          <div>
            <p className="font-semibold text-sm font-mono">{model.model_id}</p>
            <p className="text-xs text-muted-foreground">Base: {model.base_model}</p>
          </div>
        </div>
        <span className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${cfg.bg} ${cfg.text}`}>
          <StatusIcon className="h-3 w-3" />
          {cfg.label}
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="bg-surface-1 rounded-lg p-2">
          <p className="text-muted-foreground">Training Samples</p>
          <p className="font-semibold text-base mt-0.5">{model.training_samples.toLocaleString()}</p>
        </div>
        <div className="bg-surface-1 rounded-lg p-2">
          <p className="text-muted-foreground">Eval Score</p>
          <p className="font-semibold text-base mt-0.5">
            {model.eval_score != null ? `${(model.eval_score * 100).toFixed(1)}%` : '—'}
          </p>
        </div>
        <div className="bg-surface-1 rounded-lg p-2">
          <p className="text-muted-foreground">Shadow Calls</p>
          <p className="font-semibold text-base mt-0.5">{model.shadow_calls}</p>
        </div>
        <div className="bg-surface-1 rounded-lg p-2">
          <p className="text-muted-foreground">Match Rate</p>
          <p className={`font-semibold text-base mt-0.5 ${
            model.shadow_match_rate != null && baselineMatchRate != null &&
            model.shadow_match_rate > baselineMatchRate
              ? 'text-green-600'
              : ''
          }`}>
            {model.shadow_match_rate != null
              ? `${(model.shadow_match_rate * 100).toFixed(1)}%`
              : '—'}
          </p>
        </div>
      </div>

      {model.status === 'shadow' && (
        <div className="text-xs text-muted-foreground">
          {model.shadow_calls < 100 ? (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Needs {100 - model.shadow_calls} more shadow calls to be eligible for promotion
            </span>
          ) : !canPromote ? (
            <span className="flex items-center gap-1 text-yellow-600">
              <AlertCircle className="h-3 w-3" />
              Match rate must exceed baseline by &gt;5pp to promote
              {baselineMatchRate != null &&
                ` (baseline: ${(baselineMatchRate * 100).toFixed(1)}%)`}
            </span>
          ) : (
            <span className="flex items-center gap-1 text-green-600 font-medium">
              <CheckCircle className="h-3 w-3" />
              Eligible for promotion
            </span>
          )}
        </div>
      )}

      {model.status !== 'retired' && (
        <div className="flex gap-2 pt-1">
          {model.status === 'shadow' && (
            <button
              onClick={onPromote}
              disabled={!canPromote}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-brand text-white text-xs font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-brand/90 transition-colors min-h-[36px]"
            >
              <ArrowUpCircle className="h-3.5 w-3.5" />
              Promote to Production
            </button>
          )}
          <button
            onClick={onRetire}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-surface-1 text-muted-foreground text-xs font-medium hover:text-foreground hover:bg-surface-2 transition-colors min-h-[36px]"
          >
            <Archive className="h-3.5 w-3.5" />
            Retire
          </button>
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        Created {new Date(model.created_at).toLocaleDateString()}
      </p>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ModelRegistryPage() {
  const { data, isLoading, isError, refetch } = useMLModels()
  const promoteMut = usePromoteModel()
  const retireMut = useRetireModel()

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">ML Model Registry</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Fine-tuned model versions — shadow testing and promotion controls
          </p>
        </div>
        {data?.baseline_match_rate != null && (
          <div className="text-right">
            <p className="text-xs text-muted-foreground">Baseline match rate</p>
            <p className="text-xl font-bold text-foreground">
              {(data.baseline_match_rate * 100).toFixed(1)}%
            </p>
          </div>
        )}
      </div>

      {isLoading && (
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <Skeleton key={i} className="h-48 rounded-xl" />
          ))}
        </div>
      )}

      {isError && (
        <div className="rounded-xl bg-red-50 border border-red-200 p-6 text-center">
          <AlertCircle className="h-6 w-6 text-red-500 mx-auto mb-2" />
          <p className="text-sm text-red-700">Failed to load model registry</p>
          <button onClick={() => void refetch()} className="mt-2 text-sm text-red-600 underline">
            Retry
          </button>
        </div>
      )}

      {!isLoading && !isError && (
        <>
          {(data?.models ?? []).length === 0 && (
            <div className="rounded-xl bg-surface-1 border border-border-subtle p-10 text-center">
              <Brain className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
              <p className="text-muted-foreground text-sm font-medium">No models yet</p>
              <p className="text-xs text-muted-foreground mt-1">
                Fine-tuning jobs appear here once ML_FINETUNE_ENABLED is set and enough training
                data has been collected (≥50 samples).
              </p>
            </div>
          )}
          <div className="space-y-4">
            {(data?.models ?? []).map((model) => (
              <ModelCard
                key={model.id}
                model={model}
                baselineMatchRate={data?.baseline_match_rate ?? null}
                onPromote={() => promoteMut.mutate(model.id)}
                onRetire={() => retireMut.mutate(model.id)}
              />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
