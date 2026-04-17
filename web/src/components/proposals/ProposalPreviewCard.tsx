'use client'

import { useState } from 'react'
import { Download, Send, RefreshCw } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Tooltip } from '@/components/ui/Tooltip'
import { formatCurrency } from '@/lib/utils'
import type { ProposalListItem } from '@/lib/api'

/* ── Status badge variant map ────────────────────── */

const STATUS_VARIANT: Record<string, 'neutral' | 'info' | 'warning' | 'success' | 'danger'> = {
  draft: 'neutral',
  sent: 'info',
  viewed: 'warning',
  accepted: 'success',
  declined: 'danger',
}

/* ── Props ─────────────────────────────────────────── */

export interface ProposalPreviewCardProps {
  proposal: ProposalListItem
  onSend?: (id: number) => void | Promise<void>
  onDownloadPdf?: (id: number) => void | Promise<void>
  className?: string
}

/* ── Component ────────────────────────────────────── */

export function ProposalPreviewCard({
  proposal,
  onSend,
  onDownloadPdf,
  className,
}: ProposalPreviewCardProps) {
  const [sending, setSending] = useState(false)
  const [downloading, setDownloading] = useState(false)

  const handleSend = async () => {
    if (!onSend) return
    setSending(true)
    try {
      await onSend(proposal.id)
    } finally {
      setSending(false)
    }
  }

  const handleDownload = async () => {
    if (!onDownloadPdf) return
    setDownloading(true)
    try {
      await onDownloadPdf(proposal.id)
    } finally {
      setDownloading(false)
    }
  }

  const statusLabel = proposal.status.charAt(0).toUpperCase() + proposal.status.slice(1)

  return (
    <div
      className={`card overflow-hidden border-l-4 border-l-[color:var(--accent)] ${className ?? ''}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-3 px-5 pt-4 pb-2">
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-bold text-[color:var(--ink)] truncate">
            {proposal.customer_name || 'Customer'}
          </h3>
          <p className="text-[11px] text-[color:var(--muted-ink)] mt-0.5">
            Estimate #{proposal.estimate_id}
          </p>
        </div>
        <Badge
          variant={STATUS_VARIANT[proposal.status] ?? 'neutral'}
          size="sm"
          dot
        >
          {statusLabel}
        </Badge>
      </div>

      {/* Body */}
      <div className="px-5 py-3 space-y-2">
        {proposal.scope_summary && (
          <p className="text-xs text-[color:var(--muted-ink)] leading-relaxed line-clamp-2">
            {proposal.scope_summary}
          </p>
        )}
        <div className="flex items-baseline gap-1">
          <span className="text-[10px] font-bold text-[color:var(--muted-ink)] uppercase tracking-widest">
            Total
          </span>
          <span className="text-lg font-extrabold text-[color:var(--ink)] tabular-nums">
            {formatCurrency(proposal.grand_total)}
          </span>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center gap-2 px-5 pb-4 pt-1">
        {onSend && (
          <Tooltip content={proposal.status === 'sent' ? 'Resend to customer' : 'Send to customer'}>
            <button
              onClick={() => void handleSend()}
              disabled={sending}
              className="btn-primary text-xs px-3.5 py-1.5 inline-flex items-center gap-1.5"
            >
              {sending
                ? <RefreshCw size={12} className="animate-spin" />
                : <Send size={12} />}
              {proposal.status === 'sent' ? 'Resend' : 'Send'}
            </button>
          </Tooltip>
        )}
        {onDownloadPdf && (
          <Tooltip content="Download PDF">
            <button
              onClick={() => void handleDownload()}
              disabled={downloading}
              className="inline-flex items-center gap-1.5 rounded-xl border border-[color:var(--line)] px-3.5 py-1.5 text-xs font-medium text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] hover:bg-[color:var(--panel-strong)] transition-colors"
            >
              {downloading
                ? <RefreshCw size={12} className="animate-spin" />
                : <Download size={12} />}
              PDF
            </button>
          </Tooltip>
        )}
      </div>
    </div>
  )
}
