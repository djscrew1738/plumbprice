'use client'

import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { BUILT_BY_LINE } from '@/lib/branding'

interface PublicLineItem {
  description: string
  quantity: number
  unit: string
  unit_cost: number
  total_cost: number
}

interface PublicEstimate {
  id: number
  title: string
  job_type: string
  county: string
  tax_rate: number
  labor_total: number
  materials_total: number
  tax_total: number
  subtotal: number
  grand_total: number
  line_items: PublicLineItem[]
}

interface PublicCompany {
  name: string
  phone?: string | null
  address?: string | null
  city?: string | null
  state?: string | null
  zip_code?: string | null
  license_number?: string | null
  logo_url?: string | null
}

interface PublicProposal {
  token: string
  status: 'sent' | 'opened' | 'accepted' | 'declined' | 'expired'
  recipient_name: string | null
  message: string | null
  expires_at: string | null
  opened_at: string | null
  accepted_at: string | null
  declined_at: string | null
  client_signature: string | null
  company: PublicCompany
  estimate: PublicEstimate
}

const API_BASE = '/api/v1'

function fmt(n: number): string {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

function fmtDate(iso: string | null): string {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleDateString('en-US', {
      year: 'numeric', month: 'long', day: 'numeric',
    })
  } catch { return iso }
}

export default function PublicProposalPage() {
  const params = useParams<{ token: string }>()
  const token = params?.token
  const [proposal, setProposal] = useState<PublicProposal | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const [acceptOpen, setAcceptOpen] = useState(false)
  const [declineOpen, setDeclineOpen] = useState(false)
  const [signature, setSignature] = useState('')
  const [declineReason, setDeclineReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const fetchProposal = useCallback(async () => {
    if (!token) return
    try {
      const res = await fetch(`${API_BASE}/public/proposals/${token}`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      })
      if (res.status === 404) {
        setLoadError('This proposal link is invalid or has expired.')
        setLoading(false)
        return
      }
      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`)
      }
      const data = (await res.json()) as PublicProposal
      setProposal(data)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to load proposal'
      setLoadError(msg)
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => { void fetchProposal() }, [fetchProposal])

  // Light polling while the proposal is awaiting action — picks up
  // status changes (e.g., another decision-maker accepted on a different device).
  useEffect(() => {
    if (!proposal) return
    if (proposal.status !== 'sent' && proposal.status !== 'opened') return
    const id = window.setInterval(() => { void fetchProposal() }, 30_000)
    return () => window.clearInterval(id)
  }, [proposal, fetchProposal])

  const handleAccept = async () => {
    if (!token || !signature.trim()) return
    setSubmitting(true)
    setActionError(null)
    try {
      const res = await fetch(`${API_BASE}/public/proposals/${token}/accept`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ signature: signature.trim() }),
      })
      if (!res.ok) {
        const txt = await res.text()
        throw new Error(txt || `Server returned ${res.status}`)
      }
      const data = (await res.json()) as PublicProposal
      setProposal(data)
      setAcceptOpen(false)
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Failed to accept')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDecline = async () => {
    if (!token) return
    setSubmitting(true)
    setActionError(null)
    try {
      const res = await fetch(`${API_BASE}/public/proposals/${token}/decline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: declineReason.trim() || undefined }),
      })
      if (!res.ok) {
        const txt = await res.text()
        throw new Error(txt || `Server returned ${res.status}`)
      }
      const data = (await res.json()) as PublicProposal
      setProposal(data)
      setDeclineOpen(false)
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Failed to decline')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 animate-pulse">
        <div className="h-8 w-2/3 rounded-lg bg-zinc-800" />
        <div className="mt-6 h-48 rounded-xl bg-zinc-800" />
      </div>
    )
  }

  if (loadError || !proposal) {
    return (
      <div className="mx-auto flex min-h-dvh max-w-lg flex-col items-center justify-center px-4 text-center">
        <h1 className="text-2xl font-semibold text-white">Proposal unavailable</h1>
        <p className="mt-3 text-sm text-zinc-400">
          {loadError ?? 'This proposal link is invalid or has expired.'}
        </p>
        <p className="mt-6 text-xs text-zinc-500">
          If you believe this is a mistake, contact the sender for a fresh link.
        </p>
      </div>
    )
  }

  const { estimate, status } = proposal
  const canAct = status === 'sent' || status === 'opened'
  const company = proposal.company

  return (
    <div className="min-h-dvh bg-[hsl(var(--background))] text-[color:var(--ink)] print:bg-white print:text-black">
      <title>{`Proposal – ${estimate.title}`}</title>
      <style jsx global>{`
        @media print {
          .no-print { display: none !important; }
          body { background: #fff !important; color: #000 !important; }
          .proposal-card { border: 1px solid #ccc !important; box-shadow: none !important; }
        }
      `}</style>

      <div className="mx-auto max-w-3xl px-4 py-8 sm:py-12">
        {/* Company header */}
        <div className="mb-8 flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            {company.logo_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={company.logo_url}
                alt={company.name}
                className="h-10 w-auto rounded object-contain"
              />
            )}
            <div>
              {company.name && (
                <p className="text-sm font-bold text-[color:var(--ink)]">{company.name}</p>
              )}
              {company.license_number && (
                <p className="text-xs text-zinc-400">License #{company.license_number}</p>
              )}
              {(company.address || company.city) && (
                <p className="text-xs text-zinc-400">
                  {[company.address, company.city, company.state, company.zip_code]
                    .filter(Boolean).join(', ')}
                </p>
              )}
              {company.phone && (
                <p className="text-xs text-zinc-400">
                  <a href={`tel:${company.phone.replace(/[^\d+]/g, '')}`} className="hover:text-[color:var(--accent-strong)]">
                    {company.phone}
                  </a>
                </p>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={() => window.print()}
            className="no-print shrink-0 rounded-lg border border-zinc-700 px-3 py-1.5 text-xs text-zinc-300 hover:border-zinc-500 hover:text-white"
          >
            Print
          </button>
        </div>

        <header className="mb-6">
          <p className="text-xs font-semibold uppercase tracking-wider text-[color:var(--accent-strong)]">
            Plumbing Estimate
          </p>
          <h1 className="mt-1 text-2xl font-bold sm:text-3xl">{estimate.title}</h1>
          <p className="mt-1 text-sm text-zinc-400">
            {proposal.recipient_name ? `Prepared for ${proposal.recipient_name}` : 'Prepared for you'}
            {estimate.county ? ` · ${estimate.county} County, TX` : ''}
          </p>
        </header>

        {status === 'accepted' && (
          <div className="mb-6 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-emerald-200">
            <p className="text-sm font-medium">
              Accepted on {fmtDate(proposal.accepted_at)}
              {proposal.client_signature ? ` by ${proposal.client_signature}` : ''}.
            </p>
            <p className="mt-1 text-xs text-emerald-300/80">
              We&rsquo;ll be in touch shortly to schedule the work.
            </p>
            <a
              href={`/p/${proposal.token}/status`}
              className="no-print mt-3 inline-flex items-center gap-1 rounded-lg border border-emerald-500/40 px-3 py-1.5 text-xs font-semibold text-emerald-100 hover:bg-emerald-500/20"
            >
              Track your project →
            </a>
          </div>
        )}
        {status === 'declined' && (
          <div className="mb-6 rounded-xl border border-zinc-700 bg-zinc-900/60 px-4 py-3 text-zinc-300">
            <p className="text-sm">Declined on {fmtDate(proposal.declined_at)}.</p>
          </div>
        )}
        {status === 'expired' && (
          <div className="mb-6 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-amber-200">
            <p className="text-sm">This proposal has expired. Please request a new one.</p>
          </div>
        )}

        {proposal.message && (
          <div className="proposal-card mb-6 rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 text-sm text-zinc-300 print:border-zinc-300 print:bg-white print:text-black">
            {proposal.message}
          </div>
        )}

        <section className="proposal-card overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/40 print:border-zinc-300 print:bg-white">
          {/* Card list on small screens */}
          <ul className="divide-y divide-zinc-800 sm:hidden print:hidden">
            {estimate.line_items.length === 0 ? (
              <li className="px-4 py-6 text-center text-sm text-zinc-500">No line items.</li>
            ) : estimate.line_items.map((li, idx) => (
              <li key={idx} className="px-4 py-3">
                <p className="text-sm text-[color:var(--ink)]">{li.description}</p>
                <div className="mt-1 flex items-baseline justify-between text-xs text-zinc-400">
                  <span>{li.quantity} {li.unit}</span>
                  <span className="tabular-nums text-sm font-medium text-zinc-200">{fmt(li.total_cost)}</span>
                </div>
              </li>
            ))}
          </ul>

          <table className="hidden w-full text-sm sm:table print:table">
            <thead className="bg-zinc-900/80 text-xs uppercase tracking-wider text-zinc-400 print:bg-zinc-100 print:text-zinc-700">
              <tr>
                <th className="px-4 py-3 text-left font-semibold">Description</th>
                <th className="px-4 py-3 text-right font-semibold">Qty</th>
                <th className="px-4 py-3 text-right font-semibold">Total</th>
              </tr>
            </thead>
            <tbody>
              {estimate.line_items.length === 0 ? (
                <tr><td colSpan={3} className="px-4 py-6 text-center text-zinc-500">No line items.</td></tr>
              ) : estimate.line_items.map((li, idx) => (
                <tr key={idx} className="border-t border-zinc-800 print:border-zinc-200">
                  <td className="px-4 py-3">{li.description}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{li.quantity} {li.unit}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{fmt(li.total_cost)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <dl className="divide-y divide-zinc-800 border-t border-zinc-800 bg-zinc-900/30 text-sm print:divide-zinc-200 print:border-zinc-200 print:bg-zinc-50">
            <div className="flex justify-between px-4 py-2">
              <dt className="text-zinc-400">Labor</dt>
              <dd className="tabular-nums">{fmt(estimate.labor_total)}</dd>
            </div>
            <div className="flex justify-between px-4 py-2">
              <dt className="text-zinc-400">Materials</dt>
              <dd className="tabular-nums">{fmt(estimate.materials_total)}</dd>
            </div>
            <div className="flex justify-between px-4 py-2">
              <dt className="text-zinc-400">Tax ({(estimate.tax_rate * 100).toFixed(2)}%)</dt>
              <dd className="tabular-nums">{fmt(estimate.tax_total)}</dd>
            </div>
            <div className="flex justify-between px-4 py-3 text-lg font-semibold">
              <dt>Total</dt>
              <dd className="tabular-nums">{fmt(estimate.grand_total)}</dd>
            </div>
          </dl>
        </section>

        {proposal.expires_at && canAct && (
          <p className="mt-4 text-xs text-zinc-500">
            This proposal is valid until {fmtDate(proposal.expires_at)}.
          </p>
        )}

        {canAct && (
          <div className="no-print mt-6 hidden flex-col gap-3 sm:flex sm:flex-row">
            <button
              type="button"
              onClick={() => { setAcceptOpen(true); setActionError(null) }}
              className="flex-1 rounded-xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white hover:bg-emerald-500"
            >
              Accept proposal
            </button>
            <button
              type="button"
              onClick={() => { setDeclineOpen(true); setActionError(null) }}
              className="flex-1 rounded-xl border border-zinc-700 px-4 py-3 text-sm font-semibold text-zinc-200 hover:border-zinc-500"
            >
              Decline
            </button>
          </div>
        )}

        <footer className="mt-10 border-t border-zinc-800 pt-6 text-center text-xs text-zinc-500 print:border-zinc-300">
          <p>Estimate #{estimate.id} · Generated by PlumbPrice AI</p>
          <p className="mt-1 text-[11px] text-zinc-600">{BUILT_BY_LINE}</p>
        </footer>

        {/* spacer so sticky mobile CTA never overlaps footer text */}
        {canAct && <div className="h-24 sm:hidden" aria-hidden />}
      </div>

      {/* Sticky mobile CTA bar — only visible while action is possible */}
      {canAct && (
        <div
          className="no-print fixed inset-x-0 bottom-0 z-40 border-t border-zinc-800 bg-zinc-950/95 px-4 py-3 backdrop-blur sm:hidden"
          style={{ paddingBottom: 'calc(env(safe-area-inset-bottom) + 0.75rem)' }}
        >
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => { setAcceptOpen(true); setActionError(null) }}
              className="flex-1 rounded-xl bg-emerald-600 px-4 py-3 text-base font-semibold text-white active:bg-emerald-700"
            >
              Accept
            </button>
            <button
              type="button"
              onClick={() => { setDeclineOpen(true); setActionError(null) }}
              className="rounded-xl border border-zinc-700 px-4 py-3 text-base font-semibold text-zinc-200 active:bg-zinc-900"
            >
              Decline
            </button>
          </div>
        </div>
      )}

      {acceptOpen && (
        <div className="no-print fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md rounded-2xl border border-zinc-800 bg-zinc-950 p-5">
            <h2 className="text-lg font-semibold text-white">Accept this proposal</h2>
            <p className="mt-1 text-sm text-zinc-400">
              Type your full name below to accept. This acts as your electronic signature.
            </p>
            <label htmlFor="pp-sig" className="mt-4 block text-xs font-medium text-zinc-300">
              Full name
            </label>
            <input
              id="pp-sig"
              type="text"
              value={signature}
              onChange={(e) => setSignature(e.target.value)}
              maxLength={200}
              placeholder="Jane Doe"
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-white placeholder-zinc-500 focus:border-emerald-500 focus:outline-none"
            />
            {actionError && (
              <p role="alert" className="mt-3 text-xs text-red-400">{actionError}</p>
            )}
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setAcceptOpen(false)}
                className="rounded-lg border border-zinc-700 px-3 py-2 text-sm text-zinc-300 hover:border-zinc-500"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void handleAccept()}
                disabled={submitting || !signature.trim()}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
              >
                {submitting ? 'Submitting…' : 'Accept'}
              </button>
            </div>
          </div>
        </div>
      )}

      {declineOpen && (
        <div className="no-print fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md rounded-2xl border border-zinc-800 bg-zinc-950 p-5">
            <h2 className="text-lg font-semibold text-white">Decline this proposal</h2>
            <p className="mt-1 text-sm text-zinc-400">
              Let us know why — this is optional, but helps us improve.
            </p>
            <label htmlFor="pp-reason" className="mt-4 block text-xs font-medium text-zinc-300">
              Reason (optional)
            </label>
            <textarea
              id="pp-reason"
              value={declineReason}
              onChange={(e) => setDeclineReason(e.target.value)}
              maxLength={2000}
              rows={3}
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-white placeholder-zinc-500 focus:border-zinc-500 focus:outline-none"
            />
            {actionError && (
              <p role="alert" className="mt-3 text-xs text-red-400">{actionError}</p>
            )}
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setDeclineOpen(false)}
                className="rounded-lg border border-zinc-700 px-3 py-2 text-sm text-zinc-300 hover:border-zinc-500"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void handleDecline()}
                disabled={submitting}
                className="rounded-lg bg-zinc-800 px-4 py-2 text-sm font-semibold text-white hover:bg-zinc-700 disabled:opacity-50"
              >
                {submitting ? 'Submitting…' : 'Decline'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
