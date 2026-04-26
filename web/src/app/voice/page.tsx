'use client'

/**
 * Phase 4 — Voice quoting (PWA friendly).
 *
 *   Hold-to-talk → MediaRecorder → POST /api/v1/voice/quote
 *
 * The UI shows: transcript, the agent's answer, and a structured estimate
 * snapshot if the chat agent priced anything.
 */

import { useEffect, useRef, useState } from 'react'
import { api } from '@/lib/api'

type EstimateSummary = {
  task_code: string | null
  county: string | null
  grand_total: number
  labor_total: number
  materials_total: number
  tax_total: number
  confidence_label: string | null
}

type QuoteResponse = {
  status: string
  transcript: string
  answer: string
  task_code: string | null
  county: string | null
  estimate: EstimateSummary | null
  stt_duration_s?: number
}

export default function VoiceRoute() {
  const [recording, setRecording] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [quote, setQuote] = useState<QuoteResponse | null>(null)
  const [county, setCounty] = useState('Dallas')
  const [elapsed, setElapsed] = useState(0)

  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const tickRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop())
      if (tickRef.current) window.clearInterval(tickRef.current)
    }
  }, [])

  const start = async () => {
    setError(null)
    setQuote(null)
    setElapsed(0)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/mp4')
        ? 'audio/mp4'
        : ''
      const rec = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream)
      chunksRef.current = []
      rec.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data)
      }
      rec.onstop = handleStop
      recorderRef.current = rec
      rec.start()
      setRecording(true)
      tickRef.current = window.setInterval(() => setElapsed((s) => s + 1), 1000) as unknown as number
    } catch (e: any) {
      setError(e?.message ?? 'Microphone access denied')
    }
  }

  const stop = () => {
    if (tickRef.current) {
      window.clearInterval(tickRef.current)
      tickRef.current = null
    }
    recorderRef.current?.stop()
    streamRef.current?.getTracks().forEach((t) => t.stop())
    setRecording(false)
  }

  const handleStop = async () => {
    setBusy(true)
    try {
      const rec = recorderRef.current
      const mime = rec?.mimeType ?? 'audio/webm'
      const ext = mime.includes('mp4') ? 'm4a' : mime.includes('ogg') ? 'ogg' : 'webm'
      const blob = new Blob(chunksRef.current, { type: mime })
      const fd = new FormData()
      fd.append('file', blob, `voice.${ext}`)
      if (county) fd.append('county', county)
      const res = await api.post<QuoteResponse>('/voice/quote', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 90_000,
      })
      setQuote(res.data)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? 'Voice quote failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="mx-auto max-w-md p-4 space-y-4">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">Voice Quick-Quote</h1>
        <p className="text-sm text-gray-500">
          Tap, describe the job out loud, tap again to stop. We&apos;ll transcribe and price it.
        </p>
      </header>

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

      <div className="flex flex-col items-center gap-2">
        <button
          type="button"
          onClick={recording ? stop : start}
          disabled={busy}
          className={`h-32 w-32 rounded-full text-white text-lg font-semibold transition ${
            recording
              ? 'bg-red-600 animate-pulse'
              : busy
              ? 'bg-gray-400'
              : 'bg-blue-600 active:scale-95'
          }`}
        >
          {busy ? 'Working…' : recording ? 'Stop' : '🎤 Record'}
        </button>
        {recording && <div className="text-sm text-gray-600">{elapsed}s</div>}
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {quote && (
        <section className="space-y-3">
          {quote.transcript && (
            <div className="rounded-xl bg-gray-50 p-3 text-sm">
              <div className="font-medium text-gray-700">You said:</div>
              <div className="mt-1 text-gray-900 italic">&ldquo;{quote.transcript}&rdquo;</div>
            </div>
          )}
          {quote.answer && (
            <div className="rounded-xl border p-3 text-sm whitespace-pre-wrap">
              {quote.answer}
            </div>
          )}
          {quote.estimate && (
            <div className="rounded-xl border p-3">
              <div className="flex items-baseline justify-between">
                <span className="text-sm text-gray-600">{quote.estimate.task_code ?? 'Estimate'}</span>
                <span className="text-2xl font-semibold">
                  ${quote.estimate.grand_total.toFixed(0)}
                </span>
              </div>
              <div className="text-xs text-gray-500">
                Labor ${quote.estimate.labor_total.toFixed(0)} · Materials ${quote.estimate.materials_total.toFixed(0)} · Tax ${quote.estimate.tax_total.toFixed(0)}
                {quote.estimate.confidence_label ? ` · ${quote.estimate.confidence_label}` : ''}
              </div>
            </div>
          )}
        </section>
      )}
    </main>
  )
}
