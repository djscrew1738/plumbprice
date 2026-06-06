'use client'

/**
 * Variance Analytics Dashboard — /admin/variance
 *
 * Shows estimated vs. actual cost variance by task code and a summary
 * of pending pricing recommendations from the corrections engine.
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { TrendingUp, TrendingDown, Minus, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { apiV3 } from '@/lib/api-v3'
import { formatCurrency } from '@/lib/utils'
import { Skeleton } from '@/components/ui/Skeleton'

// ─── Types ────────────────────────────────────────────────────────────────────

interface VarianceRow {
  task_code: string
  sample_count: number
  avg_estimated: number
  avg_actual: number
  avg_variance_pct: number
}

interface PricingRecommendation {
  id: number
  task_code: string
  recommendation_type: string
  suggested_value: number
  current_value: number
  avg_variance_pct: number
  sample_count: number
  status: string
  created_at: string
}

interface VarianceResponse {
  rows: VarianceRow[]
  recommendations: PricingRecommendation[]
}

// ─── API helpers ──────────────────────────────────────────────────────────────

function useVarianceData() {
  return useQuery<VarianceResponse>({
    queryKey: ['variance-analytics'],
    queryFn: () => apiV3.get<VarianceResponse>('/analytics/variance').then((r) => r.data),
    staleTime: 60_000,
  })
}

function useApproveRecommendation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) =>
      apiV3.post(`/analytics/variance/recommendations/${id}/approve`),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['variance-analytics'] }),
  })
}

function useRejectRecommendation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) =>
      apiV3.post(`/analytics/variance/recommendations/${id}/reject`),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['variance-analytics'] }),
  })
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function VarianceBar({ pct }: { pct: number }) {
  const abs = Math.abs(pct)
  const capped = Math.min(abs, 50)
  const color = abs < 5 ? 'bg-green-400' : abs < 15 ? 'bg-yellow-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-surface-2 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${(capped / 50) * 100}%` }}
        />
      </div>
      <span
        className={`text-xs font-mono w-14 text-right ${
          abs < 5 ? 'text-green-600' : abs < 15 ? 'text-yellow-600' : 'text-red-600'
        }`}
      >
        {pct > 0 ? '+' : ''}
        {pct.toFixed(1)}%
      </span>
    </div>
  )
}

function VarianceIcon({ pct }: { pct: number }) {
  if (Math.abs(pct) < 5) return <Minus className="h-4 w-4 text-green-500" />
  if (pct > 0) return <TrendingUp className="h-4 w-4 text-red-500" />
  return <TrendingDown className="h-4 w-4 text-blue-500" />
}

function RecommendationCard({
  rec,
  onApprove,
  onReject,
}: {
  rec: PricingRecommendation
  onApprove: () => void
  onReject: () => void
}) {
  const label = {
    adjust_labor_hours: 'Adjust Labor Hours',
    adjust_material_markup: 'Adjust Material Markup',
    adjust_overhead: 'Adjust Overhead',
  }[rec.recommendation_type] ?? rec.recommendation_type

  return (
    <div className="rounded-xl border border-border-subtle bg-card p-4 space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold">{rec.task_code}</p>
          <p className="text-xs text-muted-foreground">{label}</p>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700 font-medium">
          Pending Review
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div>
          <p className="text-muted-foreground">Current</p>
          <p className="font-mono font-medium">{rec.current_value.toFixed(2)}</p>
        </div>
        <div>
          <p className="text-muted-foreground">Suggested</p>
          <p className="font-mono font-medium text-brand">{rec.suggested_value.toFixed(2)}</p>
        </div>
        <div>
          <p className="text-muted-foreground">Based on</p>
          <p className="font-medium">{rec.sample_count} jobs</p>
        </div>
      </div>
      <p className="text-xs text-muted-foreground">
        Avg variance: {rec.avg_variance_pct > 0 ? '+' : ''}
        {rec.avg_variance_pct.toFixed(1)}% over estimated
      </p>
      <div className="flex gap-2">
        <button
          onClick={onApprove}
          className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-green-50 text-green-700 border border-green-200 text-xs font-medium hover:bg-green-100 transition-colors min-h-[36px]"
        >
          <CheckCircle className="h-3.5 w-3.5" />
          Approve
        </button>
        <button
          onClick={onReject}
          className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-red-50 text-red-700 border border-red-200 text-xs font-medium hover:bg-red-100 transition-colors min-h-[36px]"
        >
          <XCircle className="h-3.5 w-3.5" />
          Reject
        </button>
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function VarianceDashboardPage() {
  const { data, isLoading, isError, refetch } = useVarianceData()
  const approveMut = useApproveRecommendation()
  const rejectMut = useRejectRecommendation()
  const [tab, setTab] = useState<'variance' | 'recommendations'>('variance')

  const pendingRecs = data?.recommendations.filter((r) => r.status === 'pending') ?? []

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Variance Analytics</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Estimated vs. actual job costs with pricing correction recommendations
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 p-1 bg-surface-1 rounded-xl w-fit">
        {(
          [
            { id: 'variance', label: 'Cost Variance' },
            {
              id: 'recommendations',
              label: `Recommendations${pendingRecs.length > 0 ? ` (${pendingRecs.length})` : ''}`,
            },
          ] as const
        ).map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={[
              'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              tab === t.id
                ? 'bg-card shadow-sm text-foreground'
                : 'text-muted-foreground hover:text-foreground',
            ].join(' ')}
          >
            {t.label}
          </button>
        ))}
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-16 rounded-xl" />
          ))}
        </div>
      )}

      {isError && (
        <div className="rounded-xl bg-red-50 border border-red-200 p-6 text-center">
          <AlertCircle className="h-6 w-6 text-red-500 mx-auto mb-2" />
          <p className="text-sm text-red-700">Failed to load variance data</p>
          <button onClick={() => void refetch()} className="mt-2 text-sm text-red-600 underline">
            Retry
          </button>
        </div>
      )}

      {!isLoading && !isError && tab === 'variance' && (
        <div className="space-y-2">
          {(data?.rows ?? []).length === 0 && (
            <div className="rounded-xl bg-surface-1 border border-border-subtle p-8 text-center">
              <p className="text-muted-foreground text-sm">
                No closed jobs with actual cost data yet.
              </p>
            </div>
          )}
          {(data?.rows ?? []).map((row) => (
            <div
              key={row.task_code}
              className="rounded-xl border border-border-subtle bg-card p-4 space-y-2"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <VarianceIcon pct={row.avg_variance_pct} />
                  <p className="font-medium text-sm">{row.task_code}</p>
                </div>
                <span className="text-xs text-muted-foreground">{row.sample_count} jobs</span>
              </div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground">
                <span>Avg estimated: {formatCurrency(row.avg_estimated)}</span>
                <span>Avg actual: {formatCurrency(row.avg_actual)}</span>
              </div>
              <VarianceBar pct={row.avg_variance_pct} />
            </div>
          ))}
        </div>
      )}

      {!isLoading && !isError && tab === 'recommendations' && (
        <div className="space-y-3">
          {pendingRecs.length === 0 && (
            <div className="rounded-xl bg-surface-1 border border-border-subtle p-8 text-center">
              <p className="text-muted-foreground text-sm">No pending recommendations.</p>
            </div>
          )}
          {pendingRecs.map((rec) => (
            <RecommendationCard
              key={rec.id}
              rec={rec}
              onApprove={() => approveMut.mutate(rec.id)}
              onReject={() => rejectMut.mutate(rec.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
