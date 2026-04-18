'use client'

import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Send, Download, RefreshCw, FileOutput, Copy, Check } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Tooltip } from '@/components/ui/Tooltip'
import { proposalsApi } from '@/lib/api'
import { downloadBlob } from '@/lib/utils'
import { useToast } from '@/components/ui/Toast'

export interface SentProposal {
  id: number
  recipient_email: string
  recipient_name: string | null
  sent_at: string | null
  created_at: string
  status?: string
  public_token?: string | null
  token_expires_at?: string | null
  opened_at?: string | null
  accepted_at?: string | null
  declined_at?: string | null
  client_signature?: string | null
}

export interface OutcomeRecorderCardProps {
  assumptions: string[]
  sentProposals: SentProposal[]
  estimateId?: number
  onGenerateProposal?: () => void
}

const STATUS_VARIANT: Record<string, 'neutral' | 'info' | 'warning' | 'success' | 'danger'> = {
  draft:    'neutral',
  sent:     'info',
  viewed:   'warning',
  opened:   'warning',
  accepted: 'success',
  declined: 'danger',
  expired:  'neutral',
}

const STATUS_LABEL: Record<string, string> = {
  sent:     'Sent',
  opened:   'Opened',
  viewed:   'Opened',
  accepted: 'Accepted',
  declined: 'Declined',
  expired:  'Expired',
  draft:    'Draft',
}

export function OutcomeRecorderCard({
  assumptions,
  sentProposals,
  estimateId,
  onGenerateProposal,
}: OutcomeRecorderCardProps) {
  const toast = useToast()
  const [resendingId, setResendingId] = useState<number | null>(null)
  const [downloadingId, setDownloadingId] = useState<number | null>(null)
  const [copiedId, setCopiedId] = useState<number | null>(null)

  const handleCopyLink = useCallback(async (token: string | null | undefined, id: number) => {
    if (!token) return
    try {
      const origin = typeof window !== 'undefined' ? window.location.origin : ''
      await navigator.clipboard.writeText(`${origin}/p/${token}`)
      setCopiedId(id)
      setTimeout(() => setCopiedId((v) => (v === id ? null : v)), 2000)
      toast.success('Link copied')
    } catch {
      toast.error('Could not copy link')
    }
  }, [toast])

  const handleResend = useCallback(async (proposalId: number) => {
    setResendingId(proposalId)
    try {
      await proposalsApi.resend(proposalId)
      toast.success('Proposal resent')
    } catch {
      toast.error('Could not resend proposal', 'Please try again.')
    } finally {
      setResendingId(null)
    }
  }, [toast])

  const handleDownloadPdf = useCallback(async (proposalId: number) => {
    setDownloadingId(proposalId)
    try {
      const targetId = estimateId ?? proposalId
      const res = await proposalsApi.downloadPdf(targetId)
      downloadBlob(res.data as Blob, `proposal-${proposalId}.pdf`)
    } catch {
      toast.error('Could not download PDF', 'Please try again.')
    } finally {
      setDownloadingId(null)
    }
  }, [toast, estimateId])

  return (
    <>
      {/* Assumptions */}
      {assumptions.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, delay: 0.15 }}
          className="card p-4"
        >
          <h2 className="text-xs font-bold text-white uppercase tracking-wider mb-3">Assumptions</h2>
          <ul className="space-y-2">
            {assumptions.map((a, i) => (
              <li key={i} className="flex items-start gap-2.5 text-xs text-zinc-500">
                <span className="w-1.5 h-1.5 rounded-full bg-zinc-700 mt-1.5 shrink-0" />
                {a}
              </li>
            ))}
          </ul>
        </motion.div>
      )}

      {/* Proposal History */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2, delay: 0.2 }}
        className="card p-4"
      >
        <h2 className="text-xs font-bold text-white uppercase tracking-wider mb-3">Proposal History</h2>

        {sentProposals.length > 0 ? (
          <ul className="space-y-3">
            {sentProposals.map(p => {
              const status = p.status ?? 'sent'
              const statusLabel = STATUS_LABEL[status] ?? (status.charAt(0).toUpperCase() + status.slice(1))
              const dateStr = p.sent_at
                ? new Date(p.sent_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                : new Date(p.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })

              return (
                <li key={p.id} className="flex items-center justify-between gap-2 py-1.5 border-b border-white/[0.04] last:border-b-0">
                  <div className="min-w-0 flex-1">
                    <div className="text-xs text-[color:var(--foreground)] truncate">
                      {p.recipient_name ? `${p.recipient_name} <${p.recipient_email}>` : p.recipient_email}
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[11px] text-[color:var(--muted-ink)]">{dateStr}</span>
                      <Badge variant={STATUS_VARIANT[status] ?? 'neutral'} size="sm" dot>
                        {statusLabel}
                      </Badge>
                      {status === 'accepted' && p.client_signature && (
                        <span className="text-[11px] text-emerald-400/80 truncate">
                          · signed by {p.client_signature}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {p.public_token && (
                      <Tooltip content={copiedId === p.id ? 'Copied!' : 'Copy public link'}>
                        <button
                          onClick={() => void handleCopyLink(p.public_token, p.id)}
                          className="p-1.5 rounded-lg hover:bg-white/[0.06] text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
                          aria-label="Copy public proposal link"
                        >
                          {copiedId === p.id ? <Check size={12} /> : <Copy size={12} />}
                        </button>
                      </Tooltip>
                    )}
                    <Tooltip content="Resend proposal">
                      <button
                        onClick={() => void handleResend(p.id)}
                        disabled={resendingId === p.id}
                        className="p-1.5 rounded-lg hover:bg-white/[0.06] text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
                        aria-label="Resend proposal"
                      >
                        {resendingId === p.id
                          ? <RefreshCw size={12} className="animate-spin" />
                          : <Send size={12} />}
                      </button>
                    </Tooltip>
                    <Tooltip content="Download PDF">
                      <button
                        onClick={() => void handleDownloadPdf(p.id)}
                        disabled={downloadingId === p.id}
                        className="p-1.5 rounded-lg hover:bg-white/[0.06] text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
                        aria-label="Download PDF"
                      >
                        {downloadingId === p.id
                          ? <RefreshCw size={12} className="animate-spin" />
                          : <Download size={12} />}
                      </button>
                    </Tooltip>
                  </div>
                </li>
              )
            })}
          </ul>
        ) : (
          <div className="text-center py-4">
            <p className="text-xs text-[color:var(--muted-ink)] mb-3">No proposals sent yet</p>
            {onGenerateProposal ? (
              <button
                onClick={onGenerateProposal}
                className="btn-primary text-xs px-4 py-2 inline-flex items-center gap-1.5"
              >
                <FileOutput size={13} />
                Generate Proposal
              </button>
            ) : estimateId ? (
              <a
                href={`/proposals`}
                className="btn-primary text-xs px-4 py-2 inline-flex items-center gap-1.5"
              >
                <FileOutput size={13} />
                Generate Proposal
              </a>
            ) : null}
          </div>
        )}
      </motion.div>
    </>
  )
}
