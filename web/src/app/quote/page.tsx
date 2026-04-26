'use client'

/**
 * Phase 5 — Public quote widget.
 *
 * Stand-alone, unauthenticated page anyone can hit to get an instant
 * residential plumbing quote. Backed by /api/v1/public-agent/quote.
 */

import { useEffect, useRef, useState } from 'react'

type Estimate = {
  task_code?: string | null
  grand_total: number
  labor_total: number
  materials_total: number
  tax_total: number
  confidence_label?: string | null
}

type QuoteResponse = {
  status: string
  answer: string
  task_code?: string | null
  estimate?: Estimate | null
  lead_id?: number | null
  follow_up_required: boolean
}

type Turn = { role: 'user' | 'agent'; text: string; estimate?: Estimate | null }

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pricing.ctlplumbingllc.com'

export default function PublicQuotePage() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [zip, setZip] = useState('')
  const [message, setMessage] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const transcriptRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    transcriptRef.current?.scrollTo({ top: transcriptRef.current.scrollHeight, behavior: 'smooth' })
  }, [turns])

  async function send(e?: React.FormEvent) {
    e?.preventDefault()
    if (!message.trim() || busy) return
    setError(null)
    const userMsg = message.trim()
    setTurns(prev => [...prev, { role: 'user', text: userMsg }])
    setMessage('')
    setBusy(true)
    try {
      const res = await fetch(`${API_BASE}/api/v1/public-agent/quote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMsg,
          customer: (email || phone) ? { name, email: email || undefined, phone: phone || undefined, zip_code: zip || undefined } : undefined,
        }),
      })
      if (!res.ok) {
        const text = await res.text()
        throw new Error(`Quote failed (${res.status}): ${text.slice(0, 200)}`)
      }
      const data: QuoteResponse = await res.json()
      setTurns(prev => [...prev, { role: 'agent', text: data.answer, estimate: data.estimate ?? null }])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error')
    } finally {
      setBusy(false)
    }
  }

  const usd = (n: number) => `$${n.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white text-gray-900">
      <div className="mx-auto max-w-2xl px-4 py-8">
        <header className="mb-6 text-center">
          <h1 className="text-3xl font-bold text-blue-700">CTL Plumbing — Instant Quote</h1>
          <p className="mt-2 text-sm text-gray-600">
            Tell us what you need. Get a typical price for the DFW area in seconds. A licensed plumber will confirm the final price before any work starts.
          </p>
        </header>

        <section className="mb-4 grid grid-cols-2 gap-2 rounded-lg bg-white p-3 shadow-sm">
          <input className="rounded border border-gray-300 px-3 py-2 text-sm"
            placeholder="Your name (optional)" value={name} onChange={e => setName(e.target.value)} />
          <input className="rounded border border-gray-300 px-3 py-2 text-sm"
            placeholder="ZIP (optional)" value={zip} onChange={e => setZip(e.target.value)} />
          <input type="email" className="rounded border border-gray-300 px-3 py-2 text-sm"
            placeholder="Email (so we can follow up)" value={email} onChange={e => setEmail(e.target.value)} />
          <input type="tel" className="rounded border border-gray-300 px-3 py-2 text-sm"
            placeholder="Phone (optional)" value={phone} onChange={e => setPhone(e.target.value)} />
        </section>

        <section ref={transcriptRef}
          className="mb-3 h-[55vh] overflow-y-auto rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          {turns.length === 0 && (
            <p className="text-sm text-gray-500">
              Try: <em>&quot;How much to replace a leaking kitchen faucet?&quot;</em> or <em>&quot;50-gallon gas water heater swap&quot;</em>.
            </p>
          )}
          {turns.map((t, i) => (
            <div key={i} className={`mb-3 ${t.role === 'user' ? 'text-right' : 'text-left'}`}>
              <div className={`inline-block max-w-[90%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm ${
                  t.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-900'}`}>
                {t.text}
              </div>
              {t.estimate && (
                <div className="mt-2 inline-block rounded-lg border border-blue-200 bg-blue-50 p-3 text-left text-xs text-gray-800 shadow-sm">
                  <div className="font-semibold text-blue-700">{t.estimate.task_code}</div>
                  <div className="mt-1 text-lg font-bold text-blue-900">{usd(t.estimate.grand_total)}</div>
                  <div className="text-gray-600">
                    Labor {usd(t.estimate.labor_total)} · Materials {usd(t.estimate.materials_total)} · Tax {usd(t.estimate.tax_total)}
                  </div>
                  {t.estimate.confidence_label && (
                    <div className="mt-1 text-gray-500">Confidence: {t.estimate.confidence_label}</div>
                  )}
                </div>
              )}
            </div>
          ))}
          {busy && <p className="text-sm text-gray-500">Estimating…</p>}
        </section>

        {error && <p className="mb-2 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

        <form onSubmit={send} className="flex gap-2">
          <input className="flex-1 rounded border border-gray-300 px-3 py-3 text-sm"
            placeholder="Describe the job…" value={message}
            onChange={e => setMessage(e.target.value)} disabled={busy} />
          <button type="submit" disabled={busy || !message.trim()}
            className="rounded bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow disabled:opacity-50">
            {busy ? '…' : 'Quote'}
          </button>
        </form>

        <footer className="mt-6 text-center text-xs text-gray-500">
          Quotes are estimates only. CTL Plumbing reserves the right to confirm pricing on site before any work is performed.
        </footer>
      </div>
    </div>
  )
}
