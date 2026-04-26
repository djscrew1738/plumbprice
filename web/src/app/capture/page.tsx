'use client'

/**
 * Phase 2.1.1 — Field photo quick-quote (PWA, mobile-first).
 *
 * Workflow:
 *   1. Tap "Add photo" — repeat up to 5 (burst mode).
 *   2. Each photo is preprocessed on-device:
 *        - Resized to 2048px max edge (saves cellular data).
 *        - Re-encoded as JPEG (strips EXIF / camera GPS for privacy).
 *   3. Optional: tap "Attach location" to opt in to jobsite GPS.
 *   4. Optional: add a context note.
 *   5. Submit — each photo POSTed sequentially to /photos/quick-quote.
 *      Results are aggregated client-side into a combined view.
 */

import { useRef, useState } from 'react'
import { Camera, MapPin, Trash2, Loader2, AlertTriangle } from 'lucide-react'
import { api } from '@/lib/api'
import { preprocessImage } from '@/lib/imageProcessing'
import { getGeolocation, type GeoFix } from '@/lib/getGeolocation'
import { haptic } from '@/lib/haptics'

const MAX_PHOTOS = 5

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
  photo_id?: number
}

type PhotoSlot = {
  id: string
  file: File          // pre-processed JPEG
  previewUrl: string  // object URL for display
  origBytes: number
  bytes: number
}

type SubmitResult = {
  slotId: string
  ok: boolean
  quote?: QuoteResponse
  error?: string
}

export default function CaptureRoute() {
  const fileRef = useRef<HTMLInputElement>(null)
  const [slots, setSlots] = useState<PhotoSlot[]>([])
  const [note, setNote] = useState('')
  const [county, setCounty] = useState('Dallas')
  const [urgency, setUrgency] = useState('standard')
  const [access, setAccess] = useState('first_floor')
  const [geo, setGeo] = useState<GeoFix | null>(null)
  const [geoError, setGeoError] = useState<string | null>(null)
  const [geoBusy, setGeoBusy] = useState(false)
  const [busy, setBusy] = useState<'preprocessing' | 'submitting' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<SubmitResult[]>([])

  async function handleFile(f: File | null) {
    if (!f) return
    if (slots.length >= MAX_PHOTOS) {
      setError(`Limit ${MAX_PHOTOS} photos per submission.`)
      haptic('warning')
      return
    }
    setError(null)
    setBusy('preprocessing')
    try {
      const processed = await preprocessImage(f)
      const url = URL.createObjectURL(processed.blob)
      const newFile = new File([processed.blob], `field-${Date.now()}.jpg`, {
        type: 'image/jpeg',
        lastModified: Date.now(),
      })
      setSlots((s) => [
        ...s,
        {
          id: `${Date.now()}-${Math.random()}`,
          file: newFile,
          previewUrl: url,
          origBytes: f.size,
          bytes: processed.bytes,
        },
      ])
      haptic('selection')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not process photo')
      haptic('error')
    } finally {
      setBusy(null)
      // Clear the <input> so the same file can be re-picked.
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  function removeSlot(id: string) {
    setSlots((s) => {
      const removed = s.find((x) => x.id === id)
      if (removed) URL.revokeObjectURL(removed.previewUrl)
      return s.filter((x) => x.id !== id)
    })
    haptic('tap')
  }

  async function attachLocation() {
    setGeoError(null)
    setGeoBusy(true)
    try {
      const fix = await getGeolocation()
      setGeo(fix)
      haptic('success')
    } catch (e) {
      setGeoError(e instanceof Error ? e.message : 'Could not get location')
      haptic('error')
    } finally {
      setGeoBusy(false)
    }
  }

  async function submitAll() {
    if (slots.length === 0) return
    setBusy('submitting')
    setError(null)
    setResults([])

    // Sequential to be friendly to the API rate limiter (20/min on this route).
    const out: SubmitResult[] = []
    for (const slot of slots) {
      try {
        const fd = new FormData()
        fd.append('file', slot.file)
        if (note) fd.append('note', note)
        fd.append('county', county)
        fd.append('urgency', urgency)
        fd.append('access', access)
        fd.append('persist', 'true')
        if (geo) {
          fd.append('lat', String(geo.lat))
          fd.append('lng', String(geo.lng))
        }
        const res = await api.post<QuoteResponse>('/photos/quick-quote', fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 90_000,
        })
        out.push({ slotId: slot.id, ok: res.data.status !== 'vision_error', quote: res.data })
      } catch (e: any) {
        out.push({
          slotId: slot.id,
          ok: false,
          error: e?.response?.data?.detail ?? e?.message ?? 'Upload failed',
        })
      }
      // Update incrementally so the user sees progress.
      setResults([...out])
    }
    setBusy(null)
    if (out.some((r) => !r.ok)) haptic('warning')
    else if (out.length > 0) haptic('success')
  }

  const successQuotes = results.filter((r) => r.ok && r.quote).map((r) => r.quote!)
  const combinedTotal = successQuotes.reduce(
    (acc, q) => ({
      low: acc.low + q.totals.low,
      high: acc.high + q.totals.high,
      expected: acc.expected + q.totals.expected,
    }),
    { low: 0, high: 0, expected: 0 }
  )

  return (
    <main className="mx-auto max-w-md p-4 space-y-4 pb-32">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">Photo Quick-Quote</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Snap up to {MAX_PHOTOS} photos. Resized + EXIF-stripped on-device.
        </p>
      </header>

      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
      />

      <section className="grid grid-cols-3 gap-2">
        {slots.map((s) => (
          <div key={s.id} className="relative aspect-square overflow-hidden rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--muted)/0.4)]">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={s.previewUrl} alt="preview" className="h-full w-full object-cover" />
            <button
              type="button"
              onClick={() => removeSlot(s.id)}
              aria-label="Remove photo"
              className="absolute right-1 top-1 rounded-full bg-black/60 p-1 text-white"
            >
              <Trash2 size={14} aria-hidden="true" />
            </button>
            <div className="absolute bottom-0 left-0 right-0 bg-black/55 px-1.5 py-0.5 text-[10px] text-white">
              {(s.bytes / 1024).toFixed(0)}KB · was {(s.origBytes / 1024 / 1024).toFixed(1)}MB
            </div>
          </div>
        ))}
        {slots.length < MAX_PHOTOS && (
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={busy !== null}
            className="flex aspect-square flex-col items-center justify-center gap-1 rounded-xl border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--muted)/0.3)] text-[hsl(var(--muted-foreground))] active:scale-[0.99] disabled:opacity-50"
          >
            {busy === 'preprocessing' ? (
              <Loader2 size={22} className="animate-spin" aria-hidden="true" />
            ) : (
              <Camera size={22} aria-hidden="true" />
            )}
            <span className="text-xs">Add photo</span>
          </button>
        )}
      </section>

      <section className="space-y-3">
        <button
          type="button"
          onClick={attachLocation}
          disabled={geoBusy || busy !== null}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] py-2.5 text-sm font-medium text-[hsl(var(--foreground))] disabled:opacity-50"
        >
          {geoBusy ? <Loader2 size={16} className="animate-spin" /> : <MapPin size={16} />}
          {geo ? `Location attached (±${geo.accuracy.toFixed(0)}m)` : 'Attach location (optional)'}
        </button>
        {geoError && (
          <div className="text-xs text-[hsl(var(--warning-foreground))]">{geoError}</div>
        )}

        <label className="block text-sm">
          <span className="text-[hsl(var(--muted-foreground))]">Optional note</span>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            placeholder='e.g. "leak under master sink, both supply stops corroded"'
            className="mt-1 w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-2 text-sm"
          />
        </label>

        <div className="grid grid-cols-3 gap-2">
          <label className="block text-xs">
            <span className="text-[hsl(var(--muted-foreground))]">County</span>
            <select
              value={county}
              onChange={(e) => setCounty(e.target.value)}
              className="mt-1 w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-2"
            >
              {['Dallas', 'Tarrant', 'Collin', 'Denton', 'Rockwall', 'Ellis', 'Kaufman'].map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>
          <label className="block text-xs">
            <span className="text-[hsl(var(--muted-foreground))]">Urgency</span>
            <select
              value={urgency}
              onChange={(e) => setUrgency(e.target.value)}
              className="mt-1 w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-2"
            >
              <option value="standard">Standard</option>
              <option value="same_day">Same day</option>
              <option value="after_hours">After hours</option>
              <option value="emergency">Emergency</option>
            </select>
          </label>
          <label className="block text-xs">
            <span className="text-[hsl(var(--muted-foreground))]">Access</span>
            <select
              value={access}
              onChange={(e) => setAccess(e.target.value)}
              className="mt-1 w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-2"
            >
              <option value="first_floor">1st floor</option>
              <option value="second_floor">2nd floor</option>
              <option value="crawlspace">Crawlspace</option>
              <option value="attic">Attic</option>
              <option value="basement">Basement</option>
            </select>
          </label>
        </div>
      </section>

      {error && (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {results.length > 0 && (
        <section className="space-y-3">
          <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-3">
            <div className="flex items-baseline justify-between">
              <span className="text-sm text-[hsl(var(--muted-foreground))]">
                Combined total ({successQuotes.length}/{slots.length} photos)
              </span>
              <span className="text-2xl font-semibold">
                ${combinedTotal.expected.toFixed(0)}
              </span>
            </div>
            <div className="text-xs text-[hsl(var(--muted-foreground))]">
              Range: ${combinedTotal.low.toFixed(0)} – ${combinedTotal.high.toFixed(0)}
            </div>
          </div>

          {results.map((r, idx) => (
            <div
              key={r.slotId}
              className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-3 text-sm"
            >
              <div className="font-medium">
                Photo {idx + 1}{r.quote?.scene ? ` · ${r.quote.scene}` : ''}
              </div>
              {r.ok && r.quote ? (
                <>
                  {r.quote.summary && (
                    <p className="mt-1 text-[hsl(var(--muted-foreground))]">{r.quote.summary}</p>
                  )}
                  <ul className="mt-2 space-y-1">
                    {r.quote.lines.map((l, i) => (
                      <li key={i} className="flex justify-between text-xs">
                        <span>
                          {l.task_code} · qty {l.quantity}
                          {l.condition ? ` · ${l.condition}` : ''}
                        </span>
                        <span>${l.subtotal_expected.toFixed(0)}</span>
                      </li>
                    ))}
                  </ul>
                </>
              ) : (
                <p className="mt-1 text-red-600">{r.error || 'Vision unavailable'}</p>
              )}
            </div>
          ))}
        </section>
      )}

      {/* Sticky bottom action bar — A4 ergonomics: thumb-reachable primary action. */}
      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-[hsl(var(--border))] bg-[hsl(var(--background)/0.95)] p-3 backdrop-blur supports-[backdrop-filter]:bg-[hsl(var(--background)/0.8)]">
        <div className="mx-auto flex max-w-md gap-2">
          <button
            type="button"
            onClick={submitAll}
            disabled={slots.length === 0 || busy !== null}
            className="flex-1 rounded-xl bg-[hsl(var(--primary))] py-3 text-sm font-semibold text-[hsl(var(--primary-foreground))] disabled:opacity-50"
          >
            {busy === 'submitting'
              ? `Analyzing ${results.length}/${slots.length}…`
              : slots.length > 0
              ? `Get quote · ${slots.length} photo${slots.length > 1 ? 's' : ''}`
              : 'Add a photo to start'}
          </button>
        </div>
      </div>
    </main>
  )
}
