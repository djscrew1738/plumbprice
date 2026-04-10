'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileOutput, RefreshCw, MapPin, Calendar, X,
  Copy, Check, Printer, FileText, ChevronRight,
  Zap, Building2, Clock, Download,
} from 'lucide-react'
import { format, isValid } from 'date-fns'
import { api } from '@/lib/api'
import { formatCurrency, formatCurrencyDecimal } from '@/lib/utils'
import { useToast } from '@/components/ui/Toast'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { Badge } from '@/components/ui/Badge'

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

const STATUS_VARIANT: Record<string, 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info'> = {
  draft:    'neutral',
  sent:     'info',
  accepted: 'success',
}

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
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `proposal-PP-${String(estimate.id).padStart(5, '0')}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handlePrint = () => {
    const win = window.open('', '_blank', 'width=800,height=900')
    if (!win) {
      // Fallback: download as txt if popup blocked
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
              <button
                onClick={handleDownload}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/[0.05] border border-white/[0.08] text-xs font-semibold text-zinc-400 hover:text-white hover:bg-white/[0.08] transition-all"
                title="Download as .txt"
                aria-label="Download proposal"
              >
                <Download size={13} />
                <span className="hidden sm:inline">Download</span>
              </button>
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
                <span className="text-blue-400 font-semibold">Phase 2</span> will generate branded PDF proposals with your logo, signature fields, and automatic email delivery.
              </p>
            </div>
          </div>
        </div>
      </motion.div>
    </>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function ProposalsPage() {
  const router = useRouter()
  const toast = useToast()

  const [estimates, setEstimates] = useState<Estimate[]>([])
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState<string | null>(null)
  const [generating, setGenerating] = useState<number | null>(null)
  const [activeProposal, setActiveProposal] = useState<EstimateDetail | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const res = await api.get('/estimates')
      setEstimates(res.data ?? [])
    } catch {
      setError('Could not load estimates')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const generateProposal = async (est: Estimate) => {
    setGenerating(est.id)
    try {
      // Fetch full estimate with line items
      const res = await api.get(`/estimates/${est.id}`)
      setActiveProposal(res.data)
    } catch {
      toast.error('Could not load estimate details', 'Please try again.')
    } finally {
      setGenerating(null)
    }
  }

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
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/20">
              <Clock size={11} className="text-amber-400" />
              <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">Phase 2</span>
            </div>
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

        {/* Phase 2 callout */}
        <div className="mb-4 flex items-start gap-3 p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
          <Building2 size={16} className="text-blue-400 shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-zinc-300 mb-0.5">PDF proposals coming in Phase 2</p>
            <p className="text-[11px] text-zinc-600 leading-relaxed">
              Generate formatted text proposals now. Phase 2 adds branded PDF output, logo, e-signature, and automatic email delivery to customers.
            </p>
          </div>
        </div>

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
                        <Badge variant={STATUS_VARIANT[est.status] ?? 'neutral'} size="sm">
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
                        onClick={() => generateProposal(est)}
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
                        <Badge variant={STATUS_VARIANT[est.status] ?? 'neutral'} size="sm">
                         {est.status}
                       </Badge>
                      </div>
                    </div>
                    <div className="font-extrabold text-white text-lg tabular-nums shrink-0">
                      {formatCurrency(est.grand_total)}
                    </div>
                    <button
                      onClick={() => generateProposal(est)}
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
