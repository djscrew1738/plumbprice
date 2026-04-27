'use client'

/**
 * Customer Status Portal (f2-customer-status-portal)
 *
 * Read-only page customers visit AFTER accepting a proposal to track
 * schedule + project progress. Same public_token they used to accept;
 * we ignore expiry post-accept on the API side.
 *
 * No auth, no internal pricing, no profit/margin/supplier names.
 */

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { BUILT_BY_LINE } from '@/lib/branding'

interface Milestone {
  kind: string
  at: string | null
  note: string | null
}

interface CustomerStatus {
  token: string
  project_status: string
  project_name: string
  customer_name: string | null
  city: string | null
  state: string | null
  accepted_at: string | null
  scheduled_for: string | null
  milestones: Milestone[]
}

const STATUS_LABELS: Record<string, string> = {
  lead: 'Lead Received',
  estimating: 'Estimating',
  proposal: 'Proposal Sent',
  scheduled: 'Scheduled',
  in_progress: 'In Progress',
  rough_in: 'Rough-In',
  inspection: 'Awaiting Inspection',
  complete: 'Complete',
  invoiced: 'Invoiced',
  paid: 'Paid',
  accepted: 'Accepted',
}

const KIND_LABELS: Record<string, string> = {
  schedule_set: 'Schedule confirmed',
  schedule_changed: 'Schedule updated',
  work_started: 'Work started',
  rough_in_complete: 'Rough-in complete',
  inspection_passed: 'Inspection passed',
  inspection_failed: 'Inspection failed',
  work_completed: 'Work completed',
  payment_received: 'Payment received',
  invoice_sent: 'Invoice sent',
  note_to_customer: 'Update from your team',
}

function formatDate(iso: string | null): string {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    })
  } catch {
    return iso
  }
}

export default function CustomerStatusPage() {
  const params = useParams<{ token: string }>()
  const token = params?.token
  const [data, setData] = useState<CustomerStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    const apiBase = process.env.NEXT_PUBLIC_API_URL || ''
    fetch(`${apiBase}/api/v1/public/proposals/${token}/status`)
      .then(async (res) => {
        if (res.status === 404) {
          throw new Error(
            'This status link is not active. If you just accepted a proposal, please refresh in a few minutes.',
          )
        }
        if (!res.ok) throw new Error(`Unable to load status (${res.status})`)
        return res.json()
      })
      .then((d) => setData(d))
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [token])

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <p className="text-slate-500">Loading status…</p>
      </main>
    )
  }
  if (error || !data) {
    return (
      <main className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div className="max-w-md bg-white rounded-2xl shadow p-6 text-center">
          <h1 className="text-lg font-semibold text-slate-900">Status unavailable</h1>
          <p className="mt-2 text-sm text-slate-600">{error || 'Unknown error'}</p>
        </div>
      </main>
    )
  }

  const statusLabel =
    STATUS_LABELS[data.project_status] || data.project_status.replace(/_/g, ' ')

  return (
    <main className="min-h-screen bg-slate-50 py-10 px-4">
      <div className="mx-auto max-w-2xl">
        <header className="mb-6">
          <p className="text-xs uppercase tracking-wide text-slate-500">Project Status</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-900">{data.project_name}</h1>
          {(data.city || data.state) && (
            <p className="mt-1 text-sm text-slate-500">
              {[data.city, data.state].filter(Boolean).join(', ')}
            </p>
          )}
        </header>

        <section className="rounded-2xl bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Current status
              </p>
              <p className="mt-1 text-lg font-semibold text-emerald-700">{statusLabel}</p>
            </div>
            {data.accepted_at && (
              <div className="text-right">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Accepted</p>
                <p className="mt-1 text-sm text-slate-700">{formatDate(data.accepted_at)}</p>
              </div>
            )}
          </div>

          {data.scheduled_for && (
            <div className="mt-4 rounded-xl bg-blue-50 px-4 py-3 text-sm text-blue-900">
              <p className="font-medium">Scheduled for {formatDate(data.scheduled_for)}</p>
            </div>
          )}
        </section>

        <section className="mt-6 rounded-2xl bg-white p-6 shadow-sm">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Milestones
          </h2>
          {data.milestones.length === 0 ? (
            <p className="mt-3 text-sm text-slate-500">
              No updates yet. We&apos;ll post here as we make progress.
            </p>
          ) : (
            <ol className="mt-4 space-y-3">
              {data.milestones.map((m, i) => (
                <li key={i} className="flex gap-3">
                  <div className="mt-1 h-2 w-2 flex-shrink-0 rounded-full bg-emerald-500" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-slate-900">
                      {KIND_LABELS[m.kind] || m.kind.replace(/_/g, ' ')}
                    </p>
                    {m.note && <p className="mt-0.5 text-sm text-slate-600">{m.note}</p>}
                    {m.at && <p className="mt-0.5 text-xs text-slate-400">{formatDate(m.at)}</p>}
                  </div>
                </li>
              ))}
            </ol>
          )}
        </section>

        <p className="mt-6 text-center text-xs text-slate-400">{BUILT_BY_LINE}</p>
      </div>
    </main>
  )
}
