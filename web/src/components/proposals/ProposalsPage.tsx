'use client'

import { useState, useCallback, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileOutput, RefreshCw, MapPin, Calendar, X,
  Copy, Check, Printer, FileText, ChevronRight,
  Zap, Download, Send,
} from 'lucide-react'
import { format, isValid } from 'date-fns'
import { api, proposalsApi, type ProposalListItem } from '@/lib/api'
import { formatCurrency, formatCurrencyDecimal, downloadBlob } from '@/lib/utils'
import { useToast } from '@/components/ui/Toast'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { Badge } from '@/components/ui/Badge'
import { Tooltip } from '@/components/ui/Tooltip'
import { DataTable, type Column } from '@/components/ui/DataTable'
import { SearchInput } from '@/components/ui/SearchInput'
import { Select } from '@/components/ui/Select'

// ─── Company config (move to /api/v1/settings when multi-tenant) ──────────────
const COMPANY = {
  name: 'CTL PLUMBING LLC',
  tagline: 'Licensed Master Plumber — DFW Metroplex',
  license: 'MPL-44467',
  taclb: 'TACLB-058513',
  phone: '(469) 843-4066',
  email: 'estimating@ctlplumbingllc.com',
  repLabel: 'CTL Plumbing Rep',
} as const

// ─── Types ────────────────────────────────────────────────────────────────────

interface Estimate {
  id: number
  title: string
  job_type: string
  status: string
  grand_total: number
  labor_total?: number
  materials_total?: number
  tax_total?: number
  markup_total?: number
  misc_total?: number
  confidence_label: string
  county: string
  created_at: string
  assumptions?: string[]
}

interface LineItem {
  line_type: string
  description: string
  quantity: number
  unit: string
  unit_cost: number
  total_cost: number
  supplier?: string | null
}

interface EstimateDetail extends Estimate {
  line_items: LineItem[]
  tax_rate?: number
  sources?: string[]
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtDate(s: string) {
  const d = new Date(s)
  return isValid(d) ? format(d, 'MMMM d, yyyy') : '—'
}

function fmtDateShort(s: string) {
  const d = new Date(s)
  return isValid(d) ? format(d, 'MMM d, yy') : '—'
}

const JOB_TYPE_VARIANT: Record<string, 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info'> = {
  service: 'info',
  construction: 'accent',
  commercial: 'warning',
}

const PROPOSAL_STATUS_VARIANT: Record<string, 'neutral' | 'info' | 'warning' | 'success' | 'danger'> = {
  draft:    'neutral',
  sent:     'info',
  viewed:   'warning',
  accepted: 'success',
  declined: 'danger',
}

const ESTIMATE_STATUS_VARIANT: Record<string, 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info'> = {
  draft:    'neutral',
  sent:     'info',
  accepted: 'success',
}

const STATUS_FILTER_OPTIONS = [
  { value: '',         label: 'All statuses' },
  { value: 'draft',    label: 'Draft' },
  { value: 'sent',     label: 'Sent' },
  { value: 'viewed',   label: 'Viewed' },
  { value: 'accepted', label: 'Accepted' },
  { value: 'declined', label: 'Declined' },
]

// ─── Proposal text generator ──────────────────────────────────────────────────

function buildProposalText(est: EstimateDetail): string {
  const today = format(new Date(), 'MMMM d, yyyy')
  const validUntil = format(new Date(Date.now() + 30 * 86400000), 'MMMM d, yyyy')
  const jobLabel = est.job_type === 'construction'
    ? 'New Construction'
    : est.job_type === 'commercial'
    ? 'Commercial Service'
    : 'Residential Service'

  const laborLines = est.line_items?.filter(li => li.line_type === 'labor') ?? []
  const materialLines = est.line_items?.filter(li => li.line_type === 'material') ?? []

  const laborDesc = laborLines.map(li => `  - ${li.description} (${li.quantity} ${li.unit})`).join('\n') || '  - See estimate breakdown'
  const materialDesc = materialLines.map(li => `  - ${li.description} (${li.quantity} × ${formatCurrencyDecimal(li.unit_cost)})${li.supplier ? ` [${li.supplier}]` : ''}`).join('\n') || '  - See estimate breakdown'

  return `═══════════════════════════════════════════════════════
${COMPANY.name}
${COMPANY.tagline}
${COMPANY.taclb} | ${COMPANY.license}
Phone: ${COMPANY.phone}
Email: ${COMPANY.email}
═══════════════════════════════════════════════════════

SERVICE PROPOSAL
───────────────────────────────────────────────────────
Date:           ${today}
Proposal #:     PP-${String(est.id).padStart(5, '0')}
Valid Until:    ${validUntil}
Job Type:       ${jobLabel}
County:         ${est.county} County, TX
───────────────────────────────────────────────────────

CUSTOMER
───────────────────────────────────────────────────────
Name:           ________________________________
Address:        ________________________________
Phone:          ________________________________
Email:          ________________________________

SCOPE OF WORK
───────────────────────────────────────────────────────
${est.title}

Labor:
${laborDesc}

Materials & Equipment:
${materialDesc}

PRICING SUMMARY
───────────────────────────────────────────────────────
  Labor                        ${formatCurrency(est.labor_total ?? 0).padStart(10)}
  Materials                    ${formatCurrency(est.materials_total ?? 0).padStart(10)}
  Materials Markup             ${formatCurrency(est.markup_total ?? 0).padStart(10)}
  Misc / Disposal              ${formatCurrency(est.misc_total ?? 0).padStart(10)}
  Sales Tax (${est.county} Co.) ${formatCurrencyDecimal(est.tax_total ?? 0).padStart(10)}
  ─────────────────────────────────────────────────
  TOTAL                        ${formatCurrency(est.grand_total).padStart(10)}

PAYMENT TERMS
───────────────────────────────────────────────────────
  • 50% deposit required to schedule work
  • Remaining balance due upon completion
  • Accepted: Check, Zelle, Cash
  • Finance options available (ask for details)

TERMS & CONDITIONS
───────────────────────────────────────────────────────
1. This proposal is valid for 30 days from the date above.
2. Price is based on standard access. Additional charges may
   apply for unforeseen conditions (slab, tile cuts, etc.).
3. All work performed per Texas Plumbing Code (TPLA).
4. Permit fees included unless otherwise noted.
5. One-year labor warranty on all installations.
6. Manufacturer warranty applies to equipment/fixtures.
7. Customer responsible for drywall repair unless quoted.
8. ${COMPANY.name} is not responsible for pre-existing
   conditions discovered during work.

ACCEPTANCE
───────────────────────────────────────────────────────
By signing below, you authorize ${COMPANY.name} to
proceed with the work described above.

Customer Signature: ____________________  Date: ________

Printed Name:       ____________________

${COMPANY.repLabel}:   ____________________  Date: ________

═══════════════════════════════════════════════════════
          Thank you for choosing ${COMPANY.name}!
═══════════════════════════════════════════════════════`
}

// ─── Proposal Modal ───────────────────────────────────────────────────────────

function ProposalModal({
  estimate,
  onClose,
}: {
  estimate: EstimateDetail
  onClose: () => void
}) {
  const toast = useToast()
  const [copied, setCopied] = useState(false)
  const proposalText = buildProposalText(estimate)

  const handleCopy = () => {
    void navigator.clipboard.writeText(proposalText).then(() => {
      setCopied(true)
      toast.success('Proposal copied to clipboard')
      setTimeout(() => setCopied(false), 2500)
    })
  }

  const handleDownload = () => {
    const blob = new Blob([proposalText], { type: 'text/plain;charset=utf-8;' })
    downloadBlob(blob, `proposal-PP-${String(estimate.id).padStart(5, '0')}.txt`)
  }

  const handlePrint = () => {
    const win = window.open('', '_blank', 'width=800,height=900')
    if (!win) {
      handleDownload()
      return
    }
    win.document.write(`
      <html><head>
        <title>Proposal PP-${String(estimate.id).padStart(5, '0')}</title>
        <style>
          @page { margin: 1in; }
          body { font-family: 'Courier New', monospace; font-size: 12px;
                 line-height: 1.65; color: #111; background: #fff; }
          pre { white-space: pre-wrap; word-wrap: break-word; margin: 0; }
        </style>
      </head><body>
        <pre>${proposalText.replace(/</g,'&lt;').replace(/>/g,'&gt;')}</pre>
        <script>window.onload = function(){ window.print(); }</script>
      </body></html>`)
    win.document.close()
  }

  return (
    <>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/75 backdrop-blur-sm z-40"
        onClick={onClose}
      />

      {/* Sheet */}
      <motion.div
        initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }}
        transition={{ type: 'spring', damping: 30, stiffness: 320 }}
        className="fixed inset-x-0 bottom-0 z-50 lg:inset-x-auto lg:inset-y-0 lg:right-0 lg:w-[600px]"
        style={{ maxHeight: '92dvh' }}
      >
        <div
          className="bg-[#0a0a0a] border-t lg:border-t-0 lg:border-l border-white/[0.08] flex flex-col h-full shadow-2xl"
          style={{ maxHeight: '92dvh', paddingBottom: 'max(env(safe-area-inset-bottom), 16px)' }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.07] shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                <FileOutput size={16} className="text-blue-400" />
              </div>
              <div>
                <div className="text-sm font-bold text-white">Proposal Preview</div>
                <div className="text-[11px] text-zinc-600">PP-{String(estimate.id).padStart(5, '0')}</div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/[0.05] border border-white/[0.08] text-xs font-semibold text-zinc-400 hover:text-white hover:bg-white/[0.08] transition-all"
              >
                {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
                {copied ? 'Copied!' : 'Copy'}
              </button>
              <Tooltip content="Download as .txt">
                <button
                  onClick={handleDownload}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/[0.05] border border-white/[0.08] text-xs font-semibold text-zinc-400 hover:text-white hover:bg-white/[0.08] transition-all"
                  aria-label="Download proposal"
                >
                  <Download size={13} />
                  <span className="hidden sm:inline">Download</span>
                </button>
              </Tooltip>
              <button
                onClick={handlePrint}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-600 text-white text-xs font-semibold hover:bg-blue-500 transition-colors"
                aria-label="Print proposal"
              >
                <Printer size={13} />
                Print
              </button>
              <button
                onClick={onClose}
                className="p-2 rounded-xl hover:bg-white/[0.07] text-zinc-500 hover:text-zinc-300 transition-colors"
                aria-label="Close proposal preview"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Proposal document */}
          <div className="flex-1 overflow-y-auto p-5">
            <div className="bg-[#050505] border border-white/[0.06] rounded-2xl p-5 lg:p-6">
              <pre className="text-[11px] lg:text-xs text-zinc-300 font-mono leading-relaxed whitespace-pre-wrap break-words">
                {proposalText}
              </pre>
            </div>

            {/* Info callout */}
            <div className="mt-4 flex items-start gap-2.5 px-4 py-3 rounded-xl bg-blue-500/5 border border-blue-500/15">
              <Zap size={13} className="text-blue-400 shrink-0 mt-0.5" />
              <p className="text-[11px] text-zinc-500 leading-relaxed">
                Customers can <span className="text-blue-400 font-semibold">accept or decline</span> proposals online via the public link. Use the Send button above to deliver this via email.
              </p>
            </div>
          </div>
        </div>
      </motion.div>
    </>
  )
}

// ─── Proposals DataTable Section ──────────────────────────────────────────────

function ProposalsTableSection({
  onResend,
  onDownloadPdf,
}: {
  onResend: (id: number) => Promise<void>
  onDownloadPdf: (id: number) => Promise<void>
}) {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [sortKey, setSortKey] = useState('created_at')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const { data: proposals = [], isLoading } = useQuery({
    queryKey: ['proposals', 'list'],
    queryFn: async () => {
      const res = await proposalsApi.list()
      return (res.data ?? []) as ProposalListItem[]
    },
  })

  const filtered = useMemo(() => {
    let items = proposals
    if (statusFilter) {
      items = items.filter(p => p.status === statusFilter)
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      items = items.filter(p =>
        (p.customer_name ?? '').toLowerCase().includes(q) ||
        (p.scope_summary ?? '').toLowerCase().includes(q) ||
        (p.recipient_email ?? '').toLowerCase().includes(q)
      )
    }
    items = [...items].sort((a, b) => {
      const key = sortKey as keyof ProposalListItem
      const aVal = a[key]
      const bVal = b[key]
      if (aVal == null && bVal == null) return 0
      if (aVal == null) return 1
      if (bVal == null) return -1
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDir === 'asc' ? aVal - bVal : bVal - aVal
      }
      const cmp = String(aVal).localeCompare(String(bVal))
      return sortDir === 'asc' ? cmp : -cmp
    })
    return items
  }, [proposals, statusFilter, search, sortKey, sortDir])

  const handleSort = useCallback((key: string) => {
    setSortDir(prev => sortKey === key && prev === 'asc' ? 'desc' : 'asc')
    setSortKey(key)
  }, [sortKey])

  const columns: Column<ProposalListItem>[] = useMemo(() => [
    {
      key: 'customer_name',
      header: 'Customer',
      sortable: true,
      render: (row) => (
        <div className="min-w-0">
          <div className="font-medium text-[color:var(--ink)] truncate">
            {row.customer_name || 'Unnamed'}
          </div>
          <div className="text-[11px] text-[color:var(--muted-ink)]">
            Est. #{row.estimate_id}
          </div>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      width: '110px',
      render: (row) => (
        <Badge
          variant={PROPOSAL_STATUS_VARIANT[row.status] ?? 'neutral'}
          size="sm"
          dot
        >
          {row.status.charAt(0).toUpperCase() + row.status.slice(1)}
        </Badge>
      ),
    },
    {
      key: 'grand_total',
      header: 'Total',
      sortable: true,
      align: 'right' as const,
      width: '120px',
      render: (row) => (
        <span className="font-bold tabular-nums text-[color:var(--ink)]">
          {formatCurrency(row.grand_total)}
        </span>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      sortable: true,
      width: '120px',
      render: (row) => (
        <span className="text-[color:var(--muted-ink)] text-xs">
          {fmtDateShort(row.created_at)}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      width: '140px',
      align: 'right' as const,
      render: (row) => (
        <div className="flex items-center justify-end gap-1.5">
          {row.status === 'sent' && (
            <Tooltip content="Resend proposal">
              <button
                onClick={(e) => { e.stopPropagation(); void onResend(row.id) }}
                className="p-1.5 rounded-lg hover:bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
                aria-label="Resend proposal"
              >
                <Send size={13} />
              </button>
            </Tooltip>
          )}
          <Tooltip content="Download PDF">
            <button
              onClick={(e) => { e.stopPropagation(); void onDownloadPdf(row.id) }}
              className="p-1.5 rounded-lg hover:bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
              aria-label="Download PDF"
            >
              <Download size={13} />
            </button>
          </Tooltip>
        </div>
      ),
    },
  ], [onResend, onDownloadPdf])

  if (!isLoading && proposals.length === 0) return null

  return (
    <div className="space-y-3 mb-6">
      <h2 className="text-[11px] font-bold text-zinc-600 uppercase tracking-widest px-0.5">
        Proposals
      </h2>

      {/* Search & filter bar */}
      <div className="flex flex-col sm:flex-row gap-2">
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search customer name…"
          className="flex-1"
        />
        <Select
          options={STATUS_FILTER_OPTIONS}
          value={statusFilter}
          onChange={setStatusFilter}
          placeholder="All statuses"
          clearable
          size="sm"
          className="sm:w-44"
        />
      </div>

      <DataTable
        columns={columns}
        data={filtered}
        keyExtractor={(row) => row.id}
        sortKey={sortKey}
        sortDir={sortDir}
        onSort={handleSort}
        loading={isLoading}
        emptyMessage="No proposals match your filters"
      />
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function ProposalsPage() {
  const router = useRouter()
  const toast = useToast()
  const queryClient = useQueryClient()

  const [generating, setGenerating] = useState<number | null>(null)
  const [activeProposal, setActiveProposal] = useState<EstimateDetail | null>(null)

  const { data: estimates = [], isLoading: loading, error: queryError, refetch: load } = useQuery({
    queryKey: ['estimates'],
    queryFn: async () => {
      const res = await api.get('/estimates')
      return (res.data ?? []) as Estimate[]
    },
  })

  const error = queryError ? 'Could not load estimates' : null

  const generateProposal = async (est: Estimate) => {
    setGenerating(est.id)
    try {
      const res = await api.get(`/estimates/${est.id}`)
      setActiveProposal(res.data as EstimateDetail)
    } catch {
      toast.error('Could not load estimate details', 'Please try again.')
    } finally {
      setGenerating(null)
    }
  }

  const handleResend = useCallback(async (proposalId: number) => {
    try {
      await proposalsApi.resend(proposalId)
      toast.success('Proposal resent')
      void queryClient.invalidateQueries({ queryKey: ['proposals', 'list'] })
    } catch {
      toast.error('Could not resend proposal', 'Please try again.')
    }
  }, [toast, queryClient])

  const handleDownloadPdf = useCallback(async (proposalId: number) => {
    try {
      const res = await proposalsApi.downloadPdf(proposalId)
      downloadBlob(res.data as Blob, `proposal-${proposalId}.pdf`)
    } catch {
      toast.error('Could not download PDF', 'Please try again.')
    }
  }, [toast])

  return (
    <div className="min-h-full bg-[hsl(var(--background))]">

      {/* ── Header ── */}
      <div className="bg-[hsl(var(--background))]/80 backdrop-blur-xl border-b border-white/[0.06] px-4 py-3 sticky top-0 z-10">
        <div className="max-w-3xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
              <FileOutput size={16} className="text-blue-400" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-white">Proposals</h1>
              <p className="text-[11px] text-zinc-600">Generate customer-ready proposals from estimates</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => void load()}
              disabled={loading}
              className="p-2 rounded-xl hover:bg-white/[0.07] text-zinc-500 hover:text-zinc-300 transition-colors"
              aria-label="Refresh proposals"
            >
              <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-4">

        {/* ── Proposals DataTable ── */}
        <ProposalsTableSection
          onResend={handleResend}
          onDownloadPdf={handleDownloadPdf}
        />

        {/* ── Estimates Section ── */}

        {/* Loading */}
        {loading && (
          <div className="space-y-2.5">
            {[1,2,3].map(i => (
              <div key={i} className="card p-4 space-y-2.5">
                <div className="skeleton h-3.5 w-2/3 rounded-lg" />
                <div className="skeleton h-6 w-1/3 rounded-lg" />
                <div className="skeleton h-3 w-1/2 rounded-lg" />
              </div>
            ))}
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <ErrorState
            message={error}
            onRetry={() => void load()}
          />
        )}

        {/* Empty */}
        {!loading && !error && estimates.length === 0 && (
          <EmptyState
            icon={<FileText size={24} />}
            title="No estimates yet"
            description="Generate pricing estimates first, then come back here to create proposals."
            action={
              <button onClick={() => router.push('/estimator')} className="btn-primary">
                <Zap size={15} />
                Open Estimator
              </button>
            }
          />
        )}

        {/* Estimates list */}
        {!loading && !error && estimates.length > 0 && (
          <div className="space-y-2.5">
            <p className="text-[11px] font-bold text-zinc-600 uppercase tracking-widest px-0.5 mb-3">
              {estimates.length} estimate{estimates.length !== 1 ? 's' : ''} available
            </p>

            <AnimatePresence initial={false}>
              {estimates.map((est, i) => (
                <motion.div
                  key={est.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  whileHover={{ y: -4 }}
                  transition={{ duration: 0.18, delay: i * 0.04 }}
                  className="card p-4"
                >
                  {/* Mobile layout */}
                  <div className="flex items-start gap-3 lg:hidden">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1.5">
                        <Badge variant={JOB_TYPE_VARIANT[est.job_type] ?? 'neutral'} size="sm">
                           {est.job_type}
                         </Badge>
                        <Badge variant={ESTIMATE_STATUS_VARIANT[est.status] ?? 'neutral'} size="sm">
                           {est.status}
                         </Badge>
                      </div>
                      <h3 className="font-semibold text-white text-sm leading-snug truncate mb-1">
                        {est.title || `Estimate #${est.id}`}
                      </h3>
                      <div className="flex items-center gap-3 text-[11px] text-zinc-600">
                        <span className="flex items-center gap-1"><MapPin size={10} />{est.county}</span>
                        <span className="flex items-center gap-1"><Calendar size={10} />{fmtDateShort(est.created_at)}</span>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-lg font-extrabold text-white mb-2">{formatCurrency(est.grand_total)}</div>
                      <button
                        onClick={() => void generateProposal(est)}
                        disabled={generating === est.id}
                        className="btn-primary text-xs px-3 py-1.5 whitespace-nowrap"
                      >
                        {generating === est.id
                          ? <RefreshCw size={12} className="animate-spin" />
                          : <FileOutput size={12} />}
                        {generating === est.id ? 'Loading…' : 'Generate'}
                      </button>
                    </div>
                  </div>

                  {/* Desktop layout */}
                  <div className="hidden lg:flex items-center gap-4">
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge variant={JOB_TYPE_VARIANT[est.job_type] ?? 'neutral'} size="sm">
                           {est.job_type}
                         </Badge>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-zinc-200 text-sm truncate">
                        {est.title || `Estimate #${est.id}`}
                      </div>
                      <div className="flex items-center gap-3 text-[11px] text-zinc-600 mt-0.5">
                        <span className="flex items-center gap-1"><MapPin size={10} />{est.county} County</span>
                        <span className="flex items-center gap-1"><Calendar size={10} />{fmtDate(est.created_at)}</span>
                        <Badge variant={ESTIMATE_STATUS_VARIANT[est.status] ?? 'neutral'} size="sm">
                         {est.status}
                       </Badge>
                      </div>
                    </div>
                    <div className="font-extrabold text-white text-lg tabular-nums shrink-0">
                      {formatCurrency(est.grand_total)}
                    </div>
                    <button
                      onClick={() => void generateProposal(est)}
                      disabled={generating === est.id}
                      className="btn-primary shrink-0 text-xs px-4 py-2"
                    >
                      {generating === est.id
                        ? <RefreshCw size={13} className="animate-spin" />
                        : <FileOutput size={13} />}
                      {generating === est.id ? 'Loading…' : 'Generate Proposal'}
                      {generating !== est.id && <ChevronRight size={13} className="opacity-60" />}
                    </button>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* ── Proposal Modal ── */}
      <AnimatePresence>
        {activeProposal && (
          <ProposalModal
            estimate={activeProposal}
            onClose={() => setActiveProposal(null)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
