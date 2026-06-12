'use client'

/**
 * Field Voice Quote page — /field/voice
 *
 * Mobile-optimized voice quoting using the same hold-to-talk pattern
 * as the desktop voice page, but with large touch targets and field-friendly UX.
 */

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Mic, MicOff, ArrowLeft, ChevronDown } from 'lucide-react'
import { api } from '@/lib/api'
import { DFW_COUNTIES, DEFAULT_COUNTY } from '@/lib/constants'
import { VOICE_TICK_MS, API_TIMEOUT_LONG_MS } from '@/lib/constants'
import { formatCurrency } from '@/lib/utils'
import { haptic } from '@/lib/haptics'
import { cn } from '@/lib/utils'

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
}

export default function FieldVoicePage() {
  const router = useRouter()
  const [recording, setRecording] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [quote, setQuote] = useState<QuoteResponse | null>(null)
  const [county, setCounty] = useState(DEFAULT_COUNTY)
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
    haptic('tap')
    setError(null)
    setQuote(null)
    setElapsed(0)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      recorder.start()
      recorderRef.current = recorder
      setRecording(true)
      haptic('selection')
      tickRef.current = window.setInterval(
        () => setElapsed((s) => s + VOICE_TICK_MS / 1000),
        VOICE_TICK_MS
      )
    } catch {
      setError('Microphone access denied. Check browser permissions.')
      haptic('error')
    }
  }

  const stop = async () => {
    if (!recorderRef.current || recorderRef.current.state === 'inactive') return
    haptic('warning')
    // Assign onstop BEFORE calling stop() to avoid missing the event
    recorderRef.current.onstop = async () => {
      const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
      const form = new FormData()
      form.append('audio', blob, 'voice.webm')
      form.append('county', county)
      try {
        const resp = await api.post<QuoteResponse>('/voice/quote', form, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: API_TIMEOUT_LONG_MS,
        })
        setQuote(resp.data)
        haptic('success')
      } catch {
        setError('Voice processing failed. Please try again.')
        haptic('error')
      } finally {
        setBusy(false)
      }
    }
    recorderRef.current.stop()
    streamRef.current?.getTracks().forEach((t) => t.stop())
    if (tickRef.current) {
      window.clearInterval(tickRef.current)
      tickRef.current = null
    }
    setRecording(false)
    setBusy(true)
  }

  return (
    <div className="flex flex-col min-h-screen bg-background">
      <header className="sticky top-0 z-10 bg-background border-b border-border-subtle px-4 py-3 flex items-center gap-3">
        <button
          onClick={() => router.back()}
          className="p-2 -ml-2 rounded-lg hover:bg-surface-1 min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="Back"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <h1 className="text-base font-semibold">Voice Quote</h1>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center p-6 gap-8">
        {/* County selector */}
        <div className="w-full max-w-xs">
          <label htmlFor="county-select" className="text-xs font-medium text-muted-foreground mb-1 block">County</label>
          <div className="relative">
            <select
              id="county-select"
              value={county}
              onChange={(e) => setCounty(e.target.value)}
              className="w-full appearance-none bg-card border border-border-subtle rounded-xl px-4 py-3 pr-10 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {DFW_COUNTIES.map((c) => (
                <option key={c} value={c}>
                  {c} County
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          </div>
        </div>

        {/* Mic button */}
        <div className="flex flex-col items-center gap-4">
          <button
            onPointerDown={start}
            onPointerUp={stop}
            onPointerCancel={stop}
            onPointerLeave={stop}
            disabled={busy}
            aria-label={recording ? 'Release to send' : 'Hold to record'}
            className={cn(
              'w-28 h-28 rounded-full flex items-center justify-center shadow-lg transition-all active:scale-95',
              recording
                ? 'bg-red-500 text-white ring-4 ring-red-300 animate-pulse'
                : busy
                  ? 'bg-surface-2 text-muted-foreground cursor-not-allowed'
                  : 'bg-brand text-white hover:bg-brand/90',
            )}
          >
            {recording ? (
              <MicOff className="h-10 w-10" />
            ) : (
              <Mic className="h-10 w-10" />
            )}
          </button>

          <p className="text-sm text-muted-foreground text-center">
            {recording
              ? `Recording… ${elapsed.toFixed(0)}s — release to send`
              : busy
                ? 'Processing…'
                : 'Hold to speak your quote'}
          </p>
        </div>

        {error && (
          <div className="w-full max-w-sm rounded-xl bg-red-50 border border-red-200 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {quote && (
          <div className="w-full max-w-sm space-y-3">
            {quote.transcript && (
              <div className="rounded-xl bg-surface-1 p-4">
                <p className="text-xs font-medium text-muted-foreground mb-1">You said</p>
                <p className="text-sm italic">&ldquo;{quote.transcript}&rdquo;</p>
              </div>
            )}
            {quote.answer && (
              <div className="rounded-xl bg-surface-1 p-4">
                <p className="text-xs font-medium text-muted-foreground mb-1">Response</p>
                <p className="text-sm">{quote.answer}</p>
              </div>
            )}
            {quote.estimate && (
              <div className="rounded-xl bg-card border border-border-subtle p-4 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-semibold">Estimate Total</span>
                  <span className="text-lg font-bold text-foreground">
                    {formatCurrency(quote.estimate.grand_total)}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                  <span>Labor: {formatCurrency(quote.estimate.labor_total)}</span>
                  <span>Materials: {formatCurrency(quote.estimate.materials_total)}</span>
                </div>
                {quote.estimate.confidence_label && (
                  <span className="inline-block text-xs px-2 py-0.5 rounded-full bg-surface-2 text-foreground font-medium">
                    {quote.estimate.confidence_label}
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
