'use client'

/**
 * Phase 5 — Public quote widget (v3).
 *
 * Stand-alone, unauthenticated page anyone can hit to get an instant
 * residential plumbing quote. Backed by /api/v1/public-agent/quote.
 *
 * Features:
 *   - Multi-turn conversation with history sent to backend
 *   - Clarification question handling (clickable chips)
 *   - Rich estimate display: line items, assumptions, confidence score
 *   - Line-item breakdown with labor / materials split
 */

import { useEffect, useRef, useState } from 'react'
import { api } from '@/lib/api'

type LineItem = {
  description: string
  quantity: number
  unit: string
  unit_cost: number
  total_cost: number
  line_type: string
}

type Estimate = {
  task_code?: string | null
  grand_total: number
  subtotal: number
  labor_total: number
  materials_total: number
  tax_total: number
  markup_total: number
  misc_total: number
  confidence: number
  confidence_label?: string | null
  line_items: LineItem[]
  assumptions: string[]
  market_adjustments: Record<string, unknown>[]
}

type QuoteResponse = {
  status: string
  answer: string
  task_code?: string | null
  estimate?: Estimate | null
  lead_id?: number | null
  follow_up_required: boolean
  clarification_questions: string[]
}

type HistoryMessage = { role: 'user' | 'assistant'; content: string }

type Turn = {
  role: 'user' | 'agent'
  text: string
  estimate?: Estimate | null
  clarificationQuestions?: string[]
}

function usd(n: number) {
  return `$${n.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`
}

function confidenceColor(confidence: number) {
  if (confidence >= 0.85) return 'text-green-700'
  if (confidence >= 0.65) return 'text-yellow-700'
  return 'text-red-700'
}

export function PublicQuotePage() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [zip, setZip] = useState('')
  const [message, setMessage] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [history, setHistory] = useState<HistoryMessage[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const transcriptRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = transcriptRef.current
    if (el && 'scrollTo' in el) {
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
    }
  }, [turns])

  async function send(userOverride?: string) {
    const msg = (userOverride ?? message).trim()
    if (!msg || busy) return
    setError(null)
    setTurns(prev => [...prev, { role: 'user', text: msg }])
    setMessage('')
    setBusy(true)

    const updatedHistory: HistoryMessage[] = [
      ...history,
      { role: 'user', content: msg },
    ]

    try {
      const { data } = await api.post<QuoteResponse>('/public-agent/quote', {
        message: msg,
        customer:
          email || phone
            ? {
                name: name || undefined,
                email: email || undefined,
                phone: phone || undefined,
                zip_code: zip || undefined,
              }
            : undefined,
        history: updatedHistory,
      })

      const agentTurn: Turn = {
        role: 'agent',
        text: data.answer,
        estimate: data.estimate ?? null,
        clarificationQuestions: data.clarification_questions ?? [],
      }
      setTurns(prev => [...prev, agentTurn])
      setHistory([...updatedHistory, { role: 'assistant', content: data.answer }])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error')
    } finally {
      setBusy(false)
    }
  }

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
          <input
            className="rounded border border-gray-300 px-3 py-2 text-sm"
            placeholder="Your name (optional)"
            aria-label="Your name (optional)"
            value={name}
            onChange={e => setName(e.target.value)}
          />
          <input
            className="rounded border border-gray-300 px-3 py-2 text-sm"
            placeholder="ZIP (optional)"
            aria-label="ZIP code (optional)"
            value={zip}
            onChange={e => setZip(e.target.value)}
          />
          <input
            type="email"
            className="rounded border border-gray-300 px-3 py-2 text-sm"
            placeholder="Email (so we can follow up)"
            aria-label="Email (so we can follow up)"
            value={email}
            onChange={e => setEmail(e.target.value)}
          />
          <input
            type="tel"
            className="rounded border border-gray-300 px-3 py-2 text-sm"
            placeholder="Phone (optional)"
            aria-label="Phone (optional)"
            value={phone}
            onChange={e => setPhone(e.target.value)}
          />
        </section>

        <section
          ref={transcriptRef}
          className="mb-3 h-[55vh] overflow-y-auto rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
        >
          {turns.length === 0 && (
            <p className="text-sm text-gray-500">
              Try: <em>&quot;How much to replace a leaking kitchen faucet?&quot;</em> or{' '}
              <em>&quot;50-gallon gas water heater swap&quot;</em>.
            </p>
          )}
          {turns.map((t, i) => (
            <div key={i} className={`mb-3 ${t.role === 'user' ? 'text-right' : 'text-left'}`}>
              <div
                className={`inline-block max-w-[90%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm ${
                  t.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                {t.text}
              </div>

              {/* Clarification questions as clickable chips */}
              {t.clarificationQuestions && t.clarificationQuestions.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2 text-left">
                  {t.clarificationQuestions.map((q, qi) => (
                    <button
                      key={qi}
                      onClick={() => send(q)}
                      className="rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-800 hover:bg-blue-200"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              )}

              {/* Rich estimate card */}
              {t.estimate && (
                <div className="mt-2 inline-block rounded-lg border border-blue-200 bg-blue-50 p-3 text-left text-xs text-gray-800 shadow-sm">
                  <div className="font-semibold text-blue-700">
                    {t.estimate.task_code ?? 'Estimate'}
                  </div>

                  <div className="mt-1 flex items-baseline gap-2">
                    <span className="text-lg font-bold text-blue-900">
                      {usd(t.estimate.grand_total)}
                    </span>
                    <span className={`font-medium ${confidenceColor(t.estimate.confidence)}`}>
                      Confidence: {Math.round(t.estimate.confidence * 100)}%
                    </span>
                  </div>

                  <div className="mt-2 grid grid-cols-3 gap-x-3 gap-y-1 text-gray-600">
                    <div>Labor {usd(t.estimate.labor_total)}</div>
                    <div>Materials {usd(t.estimate.materials_total)}</div>
                    <div>Tax {usd(t.estimate.tax_total)}</div>
                    {t.estimate.markup_total > 0 && (
                      <div>Markup {usd(t.estimate.markup_total)}</div>
                    )}
                    {t.estimate.misc_total > 0 && (
                      <div>Misc {usd(t.estimate.misc_total)}</div>
                    )}
                  </div>

                  {/* Line-item table */}
                  {t.estimate.line_items.length > 0 && (
                    <table className="mt-3 w-full border-collapse text-xs">
                      <thead>
                        <tr className="border-b border-blue-200 text-left text-gray-500">
                          <th className="py-1 pr-2">Item</th>
                          <th className="py-1 pr-2">Qty</th>
                          <th className="py-1 pr-2 text-right">Unit</th>
                          <th className="py-1 text-right">Total</th>
                        </tr>
                      </thead>
                      <tbody>
                        {t.estimate.line_items.map((li, liIdx) => (
                          <tr key={liIdx} className="border-b border-blue-100 last:border-0">
                            <td className="py-1 pr-2">{li.description}</td>
                            <td className="py-1 pr-2">{li.quantity}</td>
                            <td className="py-1 pr-2 text-right">{li.unit}</td>
                            <td className="py-1 text-right">{usd(li.total_cost)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}

                  {/* Assumptions */}
                  {t.estimate.assumptions.length > 0 && (
                    <ul className="mt-2 list-inside list-disc text-gray-600">
                      {t.estimate.assumptions.map((a, ai) => (
                        <li key={ai}>{a}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          ))}
          {busy && <p className="text-sm text-gray-500">Estimating…</p>}
        </section>

        {error && <p className="mb-2 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

        <form
          onSubmit={e => {
            e.preventDefault()
            send()
          }}
          className="flex gap-2"
        >
          <input
            className="flex-1 rounded border border-gray-300 px-3 py-3 text-sm"
            placeholder="Describe the job…"
            aria-label="Describe the job"
            value={message}
            onChange={e => setMessage(e.target.value)}
            disabled={busy}
          />
          <button
            type="submit"
            disabled={busy || !message.trim()}
            className="rounded bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow disabled:opacity-50"
          >
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
