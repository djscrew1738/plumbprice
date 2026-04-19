'use client'

import { useState, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { History, Pencil } from 'lucide-react'
import { api, outcomesApi, proposalsApi, type OutcomeValue } from '@/lib/api'
import { useEstimate } from '@/lib/hooks'
import { useToast } from '@/components/ui/Toast'
import { ErrorState } from '@/components/ui/ErrorState'
import { EstimateHeader } from './EstimateHeader'
import { CostBreakdownCard } from './CostBreakdownCard'
import { LineItemsTable, type LineItem } from './LineItemsTable'
import { EstimateEditor } from './EstimateEditor'
import { OutcomeRecorderCard, type SentProposal } from './OutcomeRecorderCard'
import { ProposalSendModal } from './ProposalSendModal'
import { EstimateActionsBar } from './EstimateActionsBar'
import { VersionTimeline } from './VersionTimeline'
import dynamic from 'next/dynamic'

const VersionDiffModal = dynamic(() => import('./VersionDiffModal').then(m => ({ default: m.VersionDiffModal })), { ssr: false })

interface EstimateDetail {
  id: number
  title: string
  job_type: string
  status: string
  labor_total: number
  materials_total: number
  tax_total: number
  markup_total: number
  misc_total: number
  subtotal: number
  grand_total: number
  confidence_score: number
  confidence_label: string
  assumptions: string[]
  county: string
  tax_rate: number
  preferred_supplier?: string | null
  line_items: LineItem[]
  created_at: string
}

const JOB_TYPE_VARIANT: Record<string, 'accent' | 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
  service: 'accent',
  construction: 'warning',
  commercial: 'info',
}

export function EstimateDetailPage() {
  const params = useParams()
  const router = useRouter()
  const toast  = useToast()
  const queryClient = useQueryClient()
  const id = Number(params?.id)

  const { data: rawEstimate, isLoading: loading, error: queryError } = useEstimate(id)
  const estimate = rawEstimate as EstimateDetail | undefined

  const { data: sentProposals = [] } = useQuery({
    queryKey: ['proposals', 'sends', id],
    queryFn: async () => {
      const res = await proposalsApi.listSends(id)
      return res.data as SentProposal[]
    },
    enabled: !!id,
  })

  const error = queryError ? 'Could not load estimate' : null

  const [duplicating,      setDuplicating]      = useState(false)
  const [confirmDelete,    setConfirmDelete]    = useState(false)
  const [deleting,         setDeleting]         = useState(false)
  const [outcome,          setOutcome]          = useState<OutcomeValue | null>(null)
  const [outcomeSubmitting, setOutcomeSubmitting] = useState(false)
  const [proposalOpen,     setProposalOpen]     = useState(false)
  const [proposalEmail,    setProposalEmail]    = useState('')
  const [proposalName,     setProposalName]     = useState('')
  const [proposalMsg,      setProposalMsg]      = useState('')
  const [proposalSending,  setProposalSending]  = useState(false)
  const [proposalError,    setProposalError]    = useState<string | null>(null)
  const [proposalShareUrl, setProposalShareUrl] = useState<string | null>(null)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [diffOpen, setDiffOpen] = useState(false)
  const [diffV1, setDiffV1] = useState('')
  const [diffV2, setDiffV2] = useState('')
  const [editing, setEditing] = useState(false)
  const exportCSV = useCallback(() => {
    if (!estimate) return
    const rows = [
      ['Type', 'Description', 'Qty', 'Unit', 'Unit Cost', 'Total', 'Supplier', 'SKU'],
      ...estimate.line_items.map(l => [
        l.line_type, l.description, String(l.quantity), l.unit,
        String(l.unit_cost), String(l.total_cost), l.supplier ?? '', l.sku ?? '',
      ]),
    ]
    const csv = rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `estimate-${estimate.id}-line-items.csv`
    a.click()
    URL.revokeObjectURL(url)
  }, [estimate])

  const handleDuplicate = useCallback(async () => {
    if (!estimate) return
    setDuplicating(true)
    try {
      const res = await api.post<{ id: number }>(`/estimates/${estimate.id}/duplicate`, {})
      toast.success('Estimate duplicated')
      router.push(`/estimates/${res.data.id}`)
    } catch {
      toast.error('Could not duplicate', 'Please try again.')
    } finally {
      setDuplicating(false)
    }
  }, [estimate, router, toast])

  const handleDelete = useCallback(async () => {
    if (!estimate) return
    setDeleting(true)
    try {
      await api.delete(`/estimates/${estimate.id}`)
      toast.success('Estimate deleted')
      router.push('/estimates')
    } catch {
      toast.error('Could not delete', 'Please try again.')
      setDeleting(false)
      setConfirmDelete(false)
    }
  }, [estimate, router, toast])

  const handleRecordOutcome = useCallback(async (value: OutcomeValue) => {
    if (!estimate) return
    setOutcomeSubmitting(true)
    try {
      await outcomesApi.record(estimate.id, { outcome: value })
      setOutcome(value)
      toast.success(value === 'won' ? 'Marked as won' : value === 'lost' ? 'Marked as lost' : 'Outcome recorded')
    } catch {
      toast.error('Could not record outcome', 'Please try again.')
    } finally {
      setOutcomeSubmitting(false)
    }
  }, [estimate, toast])

  const handleSendProposal = useCallback(async () => {
    if (!estimate || !proposalEmail.trim()) return
    setProposalSending(true)
    setProposalError(null)
    try {
      const res = await proposalsApi.send(estimate.id, {
        recipient_email: proposalEmail.trim(),
        recipient_name: proposalName.trim() || undefined,
        message: proposalMsg.trim() || undefined,
      })
      toast.success('Proposal sent')
      const token = res.data.public_token ?? null
      let url = res.data.accept_url ?? null
      if (token && !url && typeof window !== 'undefined') {
        url = `${window.location.origin}/p/${token}`
      }
      setProposalShareUrl(url)
      // Don't reset email/name/msg yet — the modal now shows the share link and
      // the user dismisses it explicitly.
      setProposalError(null)
      void queryClient.invalidateQueries({ queryKey: ['proposals', 'sends', id] })
    } catch (err) {
      const msg = err instanceof Error && err.message ? err.message : 'Please try again.'
      setProposalError(msg)
      toast.error('Could not send proposal', msg)
    } finally {
      setProposalSending(false)
    }
  }, [estimate, proposalEmail, proposalName, proposalMsg, toast, queryClient, id])

  const handleSelectVersion = useCallback(async (versionId: string) => {
    if (!estimate) return
    try {
      const res = await api.get(`/estimates/${estimate.id}/versions/${versionId}`)
      queryClient.setQueryData(['estimates', id], res.data)
    } catch {
      toast.error('Could not load version', 'Please try again.')
    }
  }, [estimate, toast, queryClient, id])

  const handleCompareVersions = useCallback((v1: string, v2: string) => {
    setDiffV1(v1)
    setDiffV2(v2)
    setDiffOpen(true)
  }, [])

  // ── Loading ──────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-full bg-[hsl(var(--background))] px-4 py-6 max-w-4xl mx-auto space-y-4">
        <div className="skeleton h-8 w-48 rounded-xl" />
        <div className="card p-6 space-y-4">
          <div className="skeleton h-6 w-2/3 rounded-lg" />
          <div className="skeleton h-4 w-1/3 rounded-lg" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
            {[1,2,3,4].map(i => <div key={i} className="skeleton h-20 rounded-xl" />)}
          </div>
        </div>
        <div className="card p-6 space-y-3">
          {[1,2,3,4,5].map(i => <div key={i} className="skeleton h-10 rounded-lg" />)}
        </div>
      </div>
    )
  }

  // ── Error ────────────────────────────────────────────────────────────────────
  if (error || !estimate) {
    return (
      <div className="min-h-full bg-[hsl(var(--background))] flex flex-col items-center justify-center gap-6 p-8">
        <ErrorState
          message={error ?? 'Estimate not found'}
          onRetry={() => router.back()}
          code={error ? undefined : 404}
        />
      </div>
    )
  }

  return (
    <div className="min-h-full bg-[hsl(var(--background))]">

      {/* ── Sticky header ────────────────────────────────────────────────────── */}
      <EstimateHeader
        estimate={estimate}
        outcome={outcome}
        outcomeSubmitting={outcomeSubmitting}
        duplicating={duplicating}
        confirmDelete={confirmDelete}
        deleting={deleting}
        jobTypeVariant={JOB_TYPE_VARIANT}
        onBack={() => router.back()}
        onOpenEstimator={() => router.push(`/estimator?estimateId=${estimate.id}`)}
        onDuplicate={() => void handleDuplicate()}
        onExportCSV={exportCSV}
        onPrint={() => window.print()}
        onSendProposal={() => setProposalOpen(true)}
        onRecordOutcome={(v) => void handleRecordOutcome(v)}
        onDeleteClick={() => setConfirmDelete(true)}
        onDeleteConfirm={() => void handleDelete()}
        onDeleteCancel={() => setConfirmDelete(false)}
      />

      <div className="max-w-4xl mx-auto px-4 py-5 space-y-4">

        {/* ── Cost breakdown + metadata ──────────────────────────────────────── */}
        <CostBreakdownCard
          laborTotal={estimate.labor_total}
          materialsTotal={estimate.materials_total}
          markupTotal={estimate.markup_total}
          taxTotal={estimate.tax_total}
          county={estimate.county}
          taxRate={estimate.tax_rate}
          preferredSupplier={estimate.preferred_supplier}
          confidenceLabel={estimate.confidence_label}
          confidenceScore={estimate.confidence_score}
          createdAt={estimate.created_at}
        />

        {/* ── Line items ─────────────────────────────────────────────────────── */}
        {editing ? (
          <EstimateEditor
            estimateId={estimate.id}
            initialLineItems={estimate.line_items}
            taxRate={estimate.tax_rate}
            onCancel={() => setEditing(false)}
            onSaved={() => setEditing(false)}
          />
        ) : (
          <>
            {estimate.status === 'draft' && (
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => setEditing(true)}
                  className="btn btn-ghost text-xs flex items-center gap-1"
                >
                  <Pencil size={13} /> Edit line items
                </button>
              </div>
            )}
            <LineItemsTable
              lineItems={estimate.line_items}
              subtotal={estimate.subtotal}
              taxTotal={estimate.tax_total}
              taxRate={estimate.tax_rate}
              grandTotal={estimate.grand_total}
            />
          </>
        )}

        {/* ── Assumptions & Sent Proposals ───────────────────────────────────── */}
        <OutcomeRecorderCard
          assumptions={estimate.assumptions}
          sentProposals={sentProposals}
          estimateId={estimate.id}
          onGenerateProposal={() => setProposalOpen(true)}
        />

        {/* ── Version History ────────────────────────────────────────────────── */}
        <div className="card overflow-hidden">
          <button
            onClick={() => setHistoryOpen((o) => !o)}
            className="w-full flex items-center gap-2 px-4 py-3 text-sm font-semibold text-[color:var(--ink)] hover:bg-white/[0.03] transition-colors"
          >
            <History size={15} className="text-[color:var(--accent-strong)]" />
            <span>Version History</span>
            <svg
              className={`ml-auto h-4 w-4 text-[color:var(--muted-ink)] transition-transform ${historyOpen ? 'rotate-180' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {historyOpen && (
            <div className="border-t border-[color:var(--line)] px-4 py-3">
              <VersionTimeline
                estimateId={estimate.id}
                onSelectVersion={handleSelectVersion}
                onCompare={handleCompareVersions}
              />
            </div>
          )}
        </div>

        {/* ── Bottom actions bar ─────────────────────────────────────────────── */}
        <EstimateActionsBar
          estimateTitle={estimate.title}
          estimateId={estimate.id}
          duplicating={duplicating}
          confirmDelete={confirmDelete}
          deleting={deleting}
          onDuplicate={() => void handleDuplicate()}
          onExportCSV={exportCSV}
          onPrint={() => window.print()}
          onDeleteClick={() => setConfirmDelete(true)}
          onDeleteConfirm={() => void handleDelete()}
          onDeleteCancel={() => setConfirmDelete(false)}
        />
      </div>

      {/* ── Send Proposal modal ──────────────────────────────────────────── */}
      <ProposalSendModal
        open={proposalOpen}
        estimateId={estimate.id}
        proposalEmail={proposalEmail}
        proposalName={proposalName}
        proposalMsg={proposalMsg}
        proposalSending={proposalSending}
        proposalError={proposalError}
        shareUrl={proposalShareUrl}
        grandTotal={estimate.grand_total}
        lineItemCount={estimate.line_items?.length}
        onClose={() => {
          setProposalOpen(false)
          setProposalError(null)
          if (proposalShareUrl) {
            setProposalShareUrl(null)
            setProposalEmail('')
            setProposalName('')
            setProposalMsg('')
          }
        }}
        onEmailChange={setProposalEmail}
        onNameChange={setProposalName}
        onMsgChange={setProposalMsg}
        onSend={() => void handleSendProposal()}
      />

      {/* ── Version Diff modal ───────────────────────────────────────────── */}
      <VersionDiffModal
        open={diffOpen}
        onClose={() => setDiffOpen(false)}
        estimateId={estimate.id}
        v1={diffV1}
        v2={diffV2}
      />
    </div>
  )
}
