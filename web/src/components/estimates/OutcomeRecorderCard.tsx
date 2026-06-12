'use client'

import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Send, Download, FileOutput, Copy, Check } from 'lucide-react'
import Link from 'next/link'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Tooltip } from '@/components/ui/Tooltip'
import { proposalsApi } from '@/lib/api'
import { downloadBlob } from '@/lib/utils'
import { useToast } from '@/components/ui/Toast'
import { PROPOSAL_STATUS_VARIANT, PROPOSAL_STATUS_LABEL } from '@/lib/badgeConfig'
import { COPY_FEEDBACK_MS } from '@/lib/constants'

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
      setTimeout(() => setCopiedId((v) => (v === id ? null : v)), COPY_FEEDBACK_MS)
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
              const statusLabel = PROPOSAL_STATUS_LABEL[status] ?? (status.charAt(0).toUpperCase() + status.slice(1))
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
                      <Badge variant={PROPOSAL_STATUS_VARIANT[status] ?? 'neutral'} size="sm" dot>
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
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => void handleCopyLink(p.public_token, p.id)}
                          aria-label="Copy public proposal link"
                          className="h-7 w-7"
                        >
                          {copiedId === p.id ? <Check size={12} /> : <Copy size={12} />}
                        </Button>
                      </Tooltip>
                    )}
                    <Tooltip content="Resend proposal">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => void handleResend(p.id)}
                        disabled={resendingId === p.id}
                        isLoading={resendingId === p.id}
                        aria-label="Resend proposal"
                        className="h-7 w-7"
                      >
                        <Send size={12} />
                      </Button>
                    </Tooltip>
                    <Tooltip content="Download PDF">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => void handleDownloadPdf(p.id)}
                        disabled={downloadingId === p.id}
                        isLoading={downloadingId === p.id}
                        aria-label="Download PDF"
                        className="h-7 w-7"
                      >
                        <Download size={12} />
                      </Button>
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
              <Button
                variant="primary"
                size="sm"
                onClick={onGenerateProposal}
              >
                <FileOutput size={13} />
                Generate Proposal
              </Button>
            ) : estimateId ? (
              <Link
                href="/proposals"
                className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-gradient-to-br from-[color:var(--accent)] to-[color:var(--accent-strong)] px-4 py-2 text-xs font-semibold text-white shadow-[0_4px_12px_hsl(var(--accent-hsl)/0.28)] hover:shadow-[0_6px_18px_hsl(var(--accent-hsl)/0.36)] transition-all active:scale-[0.98]"
              >
                <FileOutput size={13} />
                Generate Proposal
              </Link>
            ) : null}
          </div>
        )}
      </motion.div>
    </>
  )
}
