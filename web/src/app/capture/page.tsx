'use client'

/**
 * Phase 3 — On-site photo quick-quote (PWA friendly).
 *
 * Workflow:
 *   1. Tap "Take photo" → device camera opens (capture="environment")
 *   2. Optionally add a note
 *   3. Submit → POST /api/v1/photos/quick-quote (multipart)
 *   4. Render priced draft + unmapped items
 */

import { useRef, useState } from 'react'
import { api } from '@/lib/api'

type QuoteLine = {
  task_code: string
  description: string
  quantity: number
  confidence: number
  condition: string | null
  subtotal_low: number
  subtotal_high: number
  subtotal_expected: number
}

type QuoteResponse = {
  status: string
  scene: string
  summary: string
  lines: QuoteLine[]
  totals: { low: number; high: number; expected: number }
  unmapped: { type: string; count: number; confidence: number; reason: string }[]
}

export default function CaptureRoute() {
  const fileRef = useRef<HTMLInputElement>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [note, setNote] = useState('')
  const [county, setCounty] = useState('Dallas')
  const [urgency, setUrgency] = useState('standard')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [quote, setQuote] = useState<QuoteResponse | null>(null)

  const handlePick = (f: File | null) => {
    setError(null)
    setQuote(null)
    setFile(f)
    if (f) setPreview(URL.createObjectURL(f))
    else setPreview(null)
  }

  const submit = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    setQuote(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      if (note) fd.append('note', note)
      fd.append('county', county)
      fd.append('urgency', urgency)
      const res = await api.post<QuoteResponse>('/photos/quick-quote', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 90_000,
      })
      setQuote(res.data)
      if (res.data.status === 'vision_error') {
        setError('Vision model is unavailable — try again in a minute.')
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="mx-auto max-w-md p-4 space-y-4">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">Photo Quick-Quote</h1>
        <p className="text-sm text-gray-500">
          Snap a fixture or problem, get a priced draft in seconds.
        </p>
      </header>

      <section className="space-y-3">
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={(e) => handlePick(e.target.files?.[0] ?? null)}
        />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className="w-full rounded-2xl bg-blue-600 py-4 font-semibold text-white active:scale-[0.99]"
        >
          {file ? 'Retake photo' : '📷 Take photo'}
        </button>
        {preview && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={preview} alt="preview" className="w-full rounded-xl border" />
        )}

        <label className="block text-sm">
          <span className="text-gray-600">Optional note (e.g. &quot;leak under master sink&quot;)</span>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            className="mt-1 w-full rounded-lg border p-2"
          />
        </label>

        <div className="grid grid-cols-2 gap-2">
          <label className="block text-sm">
            <span className="text-gray-600">County</span>
            <select
              value={county}
              onChange={(e) => setCounty(e.target.value)}
              className="mt-1 w-full rounded-lg border p-2"
            >
              {['Dallas', 'Tarrant', 'Collin', 'Denton', 'Rockwall', 'Ellis', 'Kaufman'].map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            <span className="text-gray-600">Urgency</span>
            <select
              value={urgency}
              onChange={(e) => setUrgency(e.target.value)}
              className="mt-1 w-full rounded-lg border p-2"
            >
              <option value="standard">Standard</option>
              <option value="same_day">Same day</option>
              <option value="after_hours">After hours</option>
              <option value="emergency">Emergency</option>
            </select>
          </label>
        </div>

        <button
          type="button"
          onClick={submit}
          disabled={!file || loading}
          className="w-full rounded-2xl bg-emerald-600 py-3 font-semibold text-white disabled:opacity-50"
        >
          {loading ? 'Analyzing…' : 'Get quick quote'}
        </button>
      </section>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {quote && quote.status !== 'vision_error' && (
        <section className="space-y-3">
          <div className="rounded-xl bg-gray-50 p-3 text-sm">
            <div className="font-medium">Scene: {quote.scene}</div>
            {quote.summary && <div className="text-gray-600 mt-1">{quote.summary}</div>}
          </div>
          <div className="rounded-xl border p-3">
            <div className="flex items-baseline justify-between">
              <span className="text-sm text-gray-600">Estimated total</span>
              <span className="text-2xl font-semibold">${quote.totals.expected.toFixed(0)}</span>
            </div>
            <div className="text-xs text-gray-500">
              Range: ${quote.totals.low.toFixed(0)} – ${quote.totals.high.toFixed(0)}
            </div>
          </div>
          <ul className="space-y-2">
            {quote.lines.map((l, i) => (
              <li key={i} className="rounded-lg border p-3 text-sm">
                <div className="flex justify-between">
                  <span className="font-medium">{l.task_code}</span>
                  <span>${l.subtotal_expected.toFixed(0)}</span>
                </div>
                <div className="text-xs text-gray-500">
                  qty {l.quantity}{l.condition ? ` · ${l.condition}` : ''} · conf {(l.confidence * 100).toFixed(0)}%
                </div>
              </li>
            ))}
          </ul>
          {quote.unmapped.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm">
              <div className="font-medium text-amber-900">Items needing manual review</div>
              <ul className="mt-1 list-disc pl-5 text-amber-800">
                {quote.unmapped.map((u, i) => (
                  <li key={i}>{u.type} (×{u.count}) — {u.reason}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}
    </main>
  )
}
