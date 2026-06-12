'use client'

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Zap, ArrowRight } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Skeleton } from '@/components/ui/Skeleton'
import { blueprintApiV3, type BlueprintJobV3 } from '@/lib/api-v3'
import type { TakeoffFixture, TakeoffResult } from './types'

interface TakeoffDisplayProps {
  jobId: string
  onCreateEstimate: (jobId: string, fixtures: TakeoffFixture[]) => void
}

export function TakeoffDisplay({ jobId, onCreateEstimate }: TakeoffDisplayProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['blueprint-takeoff', jobId],
    queryFn: async () => {
      const res = await blueprintApiV3.getTakeoff(Number(jobId))
      const job = res.data as BlueprintJobV3

      // Aggregate detections across all pages into fixtures
      const fixtureMap = new Map<string, { count: number; totalConfidence: number }>()
      for (const page of job.pages || []) {
        for (const det of page.detections || []) {
          const existing = fixtureMap.get(det.fixture_type)
          if (existing) {
            existing.count++
            existing.totalConfidence += det.confidence
          } else {
            fixtureMap.set(det.fixture_type, { count: 1, totalConfidence: det.confidence })
          }
        }
      }
      const fixtures = Array.from(fixtureMap.entries()).map(([name, data]) => ({
        name,
        quantity: data.count,
        confidence: Math.round((data.totalConfidence / data.count) * 100) / 100,
        unit: 'ea',
      }))

      return {
        fixtures,
        rooms: (job.rooms || []).map(r => ({
          type: r.room_type,
          name: r.room_name,
          area_sqft: r.area_sqft,
          fixture_count: r.fixture_count,
          confidence: r.confidence,
        })),
        pipe_runs: (job.pipe_runs || []).map(p => ({
          pipe_type: p.pipe_type,
          length_ft: p.length_ft,
          confidence: p.confidence,
        })),
      } as TakeoffResult
    },
    staleTime: Infinity,
  })

  const [quantities, setQuantities] = useState<Record<string, number>>({})

  // Seed quantities from fetched data (only when data first arrives)
  useEffect(() => {
    if (data?.fixtures) {
      const initial: Record<string, number> = {}
      data.fixtures.forEach((f, i) => {
        initial[`${f.name}-${i}`] = f.quantity
      })
      setQuantities(initial)
    }
  }, [data])

  if (isLoading) {
    return <Skeleton variant="table-row" count={3} className="mt-2" />
  }

  if (isError || !data) {
    return (
      <p className="mt-2 text-[11px] text-zinc-600">
        {isError ? 'Could not load takeoff data.' : 'No fixtures detected.'}
      </p>
    )
  }

  const handleCreateEstimate = () => {
    const modified = data.fixtures.map((f, i) => ({
      ...f,
      quantity: quantities[`${f.name}-${i}`] ?? f.quantity,
    }))
    onCreateEstimate(jobId, modified)
  }

  return (
    <div className="mt-3 space-y-2">
      <p className="text-[11px] font-bold uppercase tracking-widest text-zinc-500">
        Detected fixtures ({data.fixtures.length})
      </p>
      <div className="space-y-1">
        {data.fixtures.map((f, i) => {
          const key = `${f.name}-${i}`
          return (
            <div key={key} className="flex items-center gap-3 rounded-lg border border-white/[0.05] bg-white/[0.02] px-3 py-1.5">
              <span className="flex-1 truncate text-xs font-medium text-zinc-300">{f.name}</span>
              <div className="flex items-center gap-1">
                <span className="text-[11px] text-zinc-500">×</span>
                <input
                  type="number"
                  min={0}
                  step={1}
                  value={quantities[key] ?? f.quantity}
                  onChange={(e) => {
                    const v = Math.max(0, Number(e.target.value) || 0)
                    setQuantities(prev => ({ ...prev, [key]: v }))
                  }}
                  className="w-14 rounded-md border border-white/[0.1] bg-white/[0.06] px-1.5 py-0.5 text-right text-[11px] text-zinc-300 focus:outline-none focus:ring-1 focus:ring-blue-500/60 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                  aria-label={`Quantity for ${f.name}`}
                />
                {f.unit && <span className="text-[11px] text-zinc-500">{f.unit}</span>}
              </div>
              <Badge
                variant={f.confidence >= 0.8 ? 'success' : f.confidence >= 0.5 ? 'warning' : 'danger'}
                size="sm"
              >
                {Math.round(f.confidence * 100)}%
              </Badge>
            </div>
          )
        })}
      </div>
      {(data.rooms.length > 0 || data.pipe_runs.length > 0) && (
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
          {data.rooms.length > 0 && (
            <div className="rounded-lg border border-white/[0.05] bg-white/[0.02] p-2.5">
              <p className="mb-1.5 text-[11px] font-bold uppercase tracking-widest text-zinc-500">
                Rooms ({data.rooms.length})
              </p>
              <div className="space-y-1">
                {data.rooms.map((r, i) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <span className="truncate text-zinc-300">{r.name || r.type}</span>
                    <span className="text-zinc-500">{r.area_sqft ? `${r.area_sqft.toFixed(0)} sqft` : ''}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {data.pipe_runs.length > 0 && (
            <div className="rounded-lg border border-white/[0.05] bg-white/[0.02] p-2.5">
              <p className="mb-1.5 text-[11px] font-bold uppercase tracking-widest text-zinc-500">
                Pipe Runs ({data.pipe_runs.length})
              </p>
              <div className="space-y-1">
                {data.pipe_runs.map((p, i) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <span className="truncate text-zinc-300">{p.pipe_type.replace(/_/g, ' ')}</span>
                    <span className="text-zinc-500">{p.length_ft.toFixed(0)} ft</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      <div className="mt-2 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={handleCreateEstimate}
          className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-600 px-4 py-2 text-xs font-semibold text-white transition-all hover:shadow-lg active:scale-[0.98]"
        >
          <Zap size={13} />
          Create Estimate (v3)
          <ArrowRight size={12} />
        </button>
        <a
          href={`/blueprints/${jobId}/review`}
          className="inline-flex items-center gap-2 rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-xs font-semibold text-amber-200 transition-all hover:bg-amber-500/20"
        >
          Review detections
        </a>
      </div>
    </div>
  )
}
