'use client'

/**
 * Phase 2.5 — Blueprint review UI.
 *
 * Surfaces every low-confidence detection (`needs_review[]`) returned by
 * `GET /api/v1/blueprints/{id}/takeoff` and lets the user adjudicate each
 * one with `POST /api/v1/blueprints/detections/{detection_id}/feedback`.
 *
 * Three verdicts are wired up:
 *   - correct  → keeps the detection as-is and clears the review flag
 *   - wrong    → zeros the count (audit-trail safe, doesn't delete)
 *   - edited   → user types a corrected fixture_type and/or count
 */

import { useEffect, useMemo, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { api } from '@/lib/api'

type ReviewItem = {
  detection_id: number
  fixture_type: string
  count: number
  confidence: number
  page_number: number
}

type PageSummary = {
  page_id: number
  page_number: number
  sheet_type: string | null
  sheet_number: string | null
  title: string | null
  scale: string | null
  status: string | null
  px_per_ft: number | null
  scale_calibrated: boolean
  scale_source: string | null
}

type Fixture = {
  type: string
  count: number
  confidence: number
  needs_review: boolean
}

type Takeoff = {
  job_id: number
  status: string
  fixtures: Fixture[]
  pages: PageSummary[]
  needs_review: ReviewItem[]
}

export default function BlueprintReviewPage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()
  const jobId = params?.id

  const [data, setData] = useState<Takeoff | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<Record<number, boolean>>({})
  const [edits, setEdits] = useState<Record<number, { fixture_type?: string; count?: number; note?: string }>>({})
  const [resolved, setResolved] = useState<Record<number, string>>({}) // detection_id → verdict

  async function load() {
    if (!jobId) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.get<Takeoff>(`/blueprints/${jobId}/takeoff`)
      setData(res.data)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load takeoff'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [jobId]) // eslint-disable-line react-hooks/exhaustive-deps

  async function submit(item: ReviewItem, verdict: 'correct' | 'wrong' | 'edited') {
    setBusy(b => ({ ...b, [item.detection_id]: true }))
    try {
      const body: Record<string, unknown> = { verdict }
      if (verdict === 'edited') {
        const e = edits[item.detection_id] || {}
        if (e.fixture_type) body.corrected_fixture_type = e.fixture_type
        if (typeof e.count === 'number' && e.count > 0) body.corrected_count = e.count
        if (e.note) body.note = e.note
      }
      await api.post(`/blueprints/detections/${item.detection_id}/feedback`, body)
      setResolved(r => ({ ...r, [item.detection_id]: verdict }))
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to submit feedback'
      setError(msg)
    } finally {
      setBusy(b => ({ ...b, [item.detection_id]: false }))
    }
  }

  const pendingItems = useMemo(
    () => (data?.needs_review || []).filter(i => !resolved[i.detection_id]),
    [data, resolved]
  )

  if (loading) {
    return <div className="p-8 text-gray-600">Loading takeoff…</div>
  }
  if (error || !data) {
    return (
      <div className="p-8">
        <p className="mb-3 text-red-700">{error || 'No data.'}</p>
        <button onClick={() => router.back()} className="text-sm text-blue-600 hover:underline">← Back</button>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Blueprint Review</h1>
          <p className="text-sm text-gray-600">Job #{data.job_id} · {data.status}</p>
        </div>
        <button onClick={() => router.push(`/blueprints`)}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50">
          ← Blueprints
        </button>
      </div>

      {/* Pages summary */}
      <section className="mb-6">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-500">Pages ({data.pages.length})</h2>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-3">
          {data.pages.map(p => (
            <PageCard key={p.page_id} page={p} onChanged={load} />
          ))}
        </div>
      </section>

      {/* Fixtures totals */}
      <section className="mb-6">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Fixture totals ({data.fixtures.length})
        </h2>
        <div className="overflow-hidden rounded border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="px-3 py-2">Fixture</th>
                <th className="px-3 py-2">Count</th>
                <th className="px-3 py-2">Avg confidence</th>
                <th className="px-3 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {data.fixtures.map(f => (
                <tr key={f.type} className="border-t border-gray-100">
                  <td className="px-3 py-2 font-medium">{f.type}</td>
                  <td className="px-3 py-2">{f.count}</td>
                  <td className="px-3 py-2">{(f.confidence * 100).toFixed(0)}%</td>
                  <td className="px-3 py-2">
                    {f.needs_review ? (
                      <span className="rounded bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">needs review</span>
                    ) : (
                      <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800">ok</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Review queue */}
      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Review queue ({pendingItems.length} pending · {Object.keys(resolved).length} done)
        </h2>
        {data.needs_review.length === 0 && (
          <p className="rounded border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
            No detections flagged for review — every fixture cleared the confidence threshold.
          </p>
        )}
        <div className="space-y-3">
          {data.needs_review.map(item => {
            const isDone = !!resolved[item.detection_id]
            const isBusy = !!busy[item.detection_id]
            const e = edits[item.detection_id] || {}
            return (
              <div key={item.detection_id}
                className={`rounded-lg border p-4 shadow-sm ${
                  isDone ? 'border-gray-200 bg-gray-50 opacity-70' : 'border-amber-200 bg-white'
                }`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="font-medium text-gray-900">
                      {item.fixture_type} <span className="text-gray-500">× {item.count}</span>
                    </div>
                    <div className="text-xs text-gray-600">
                      Page {item.page_number} · confidence {(item.confidence * 100).toFixed(0)}%
                    </div>
                  </div>
                  {isDone && (
                    <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800">
                      ✓ {resolved[item.detection_id]}
                    </span>
                  )}
                </div>

                {!isDone && (
                  <>
                    <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
                      <input
                        className="rounded border border-gray-300 px-2 py-1 text-sm"
                        placeholder={`Corrected type (was ${item.fixture_type})`}
                        value={e.fixture_type || ''}
                        onChange={ev => setEdits(s => ({ ...s, [item.detection_id]: { ...s[item.detection_id], fixture_type: ev.target.value } }))}
                      />
                      <input
                        type="number"
                        min={0}
                        className="rounded border border-gray-300 px-2 py-1 text-sm"
                        placeholder={`Corrected count (was ${item.count})`}
                        value={e.count ?? ''}
                        onChange={ev => setEdits(s => ({ ...s, [item.detection_id]: { ...s[item.detection_id], count: ev.target.value === '' ? undefined : Number(ev.target.value) } }))}
                      />
                      <input
                        className="rounded border border-gray-300 px-2 py-1 text-sm"
                        placeholder="Note (optional)"
                        value={e.note || ''}
                        onChange={ev => setEdits(s => ({ ...s, [item.detection_id]: { ...s[item.detection_id], note: ev.target.value } }))}
                      />
                    </div>
                    <div className="mt-3 flex gap-2">
                      <button onClick={() => submit(item, 'correct')} disabled={isBusy}
                        className="rounded bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50">
                        ✓ Correct
                      </button>
                      <button onClick={() => submit(item, 'edited')} disabled={isBusy || (!e.fixture_type && !e.count)}
                        className="rounded bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
                        ✎ Save edit
                      </button>
                      <button onClick={() => submit(item, 'wrong')} disabled={isBusy}
                        className="rounded bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700 disabled:opacity-50">
                        ✗ Wrong
                      </button>
                    </div>
                  </>
                )}
              </div>
            )
          })}
        </div>
      </section>
    </div>
  )
}


// ─── Phase 2.5 — per-page scale calibration ────────────────────────────────────

function PageCard({ page, onChanged }: { page: PageSummary; onChanged: () => void }) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [form, setForm] = useState({ x1: '', y1: '', x2: '', y2: '', real_feet: '' })

  async function autoCalibrate() {
    setBusy(true); setErr(null)
    try {
      await api.post(`/blueprints/pages/${page.page_id}/calibrate/auto`)
      onChanged()
    } catch (e) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErr(msg || 'Auto-calibration failed')
    } finally {
      setBusy(false)
    }
  }

  async function manualCalibrate() {
    setBusy(true); setErr(null)
    try {
      const body = {
        x1: parseFloat(form.x1), y1: parseFloat(form.y1),
        x2: parseFloat(form.x2), y2: parseFloat(form.y2),
        real_feet: parseFloat(form.real_feet),
      }
      if (Object.values(body).some(v => Number.isNaN(v))) {
        setErr('All fields are required and must be numbers'); setBusy(false); return
      }
      await api.post(`/blueprints/pages/${page.page_id}/calibrate`, body)
      setOpen(false)
      onChanged()
    } catch (e) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErr(msg || 'Calibration failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="rounded border border-gray-200 bg-white p-3 text-sm shadow-sm">
      <div className="font-medium text-gray-900">
        Page {page.page_number} {page.sheet_number ? `· ${page.sheet_number}` : ''}
      </div>
      <div className="text-xs text-gray-600">{page.title || page.sheet_type || '—'}</div>
      <div className="mt-1 text-xs text-gray-500">
        Scale: <span className="font-mono">{page.scale || '—'}</span>
      </div>
      <div className="mt-1 text-xs text-gray-500">
        Calibration:{' '}
        {page.scale_calibrated && page.px_per_ft ? (
          <span className="font-mono text-emerald-700">
            {page.px_per_ft} px/ft <span className="text-gray-500">({page.scale_source})</span>
          </span>
        ) : (
          <span className="text-amber-700">not calibrated</span>
        )}
      </div>

      <div className="mt-2 flex flex-wrap gap-1.5">
        {page.scale && (
          <button
            onClick={autoCalibrate}
            disabled={busy}
            className="rounded bg-emerald-600 px-2 py-1 text-[11px] font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
          >
            Auto from text
          </button>
        )}
        <button
          onClick={() => setOpen(o => !o)}
          className="rounded border border-gray-300 px-2 py-1 text-[11px] font-medium text-gray-700 hover:bg-gray-50"
        >
          {open ? 'Cancel' : 'Manual…'}
        </button>
      </div>

      {err && <div className="mt-2 text-[11px] text-red-600">{err}</div>}

      {open && (
        <div className="mt-2 space-y-1.5 rounded bg-gray-50 p-2 text-[11px]">
          <div className="text-gray-600">
            Click two points on the page in any image tool, copy pixel
            coordinates, and enter the real-world distance in feet.
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            <input className="rounded border border-gray-300 px-2 py-1" placeholder="x1"
              value={form.x1} onChange={e => setForm({ ...form, x1: e.target.value })} />
            <input className="rounded border border-gray-300 px-2 py-1" placeholder="y1"
              value={form.y1} onChange={e => setForm({ ...form, y1: e.target.value })} />
            <input className="rounded border border-gray-300 px-2 py-1" placeholder="x2"
              value={form.x2} onChange={e => setForm({ ...form, x2: e.target.value })} />
            <input className="rounded border border-gray-300 px-2 py-1" placeholder="y2"
              value={form.y2} onChange={e => setForm({ ...form, y2: e.target.value })} />
          </div>
          <input className="w-full rounded border border-gray-300 px-2 py-1" placeholder="real distance (feet)"
            value={form.real_feet} onChange={e => setForm({ ...form, real_feet: e.target.value })} />
          <button
            onClick={manualCalibrate}
            disabled={busy}
            className="w-full rounded bg-blue-600 px-2 py-1 text-[11px] font-medium text-white hover:bg-blue-500 disabled:opacity-50"
          >
            {busy ? 'Saving…' : 'Save calibration'}
          </button>
        </div>
      )}
    </div>
  )
}
