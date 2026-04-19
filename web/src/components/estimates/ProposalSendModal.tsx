'use client'

import { useState } from 'react'
import { RefreshCw, Copy, Check, FileText, ChevronDown, ChevronUp } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'

function formatCurrency(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

export interface ProposalSendModalProps {
  open: boolean
  estimateId: number
  proposalEmail: string
  proposalName: string
  proposalMsg: string
  proposalSending: boolean
  proposalError?: string | null
  /** Public URL shown after a successful send so the contractor can share it another way. */
  shareUrl?: string | null
  /** Optional estimate summary for the preview section */
  grandTotal?: number
  lineItemCount?: number
  onClose: () => void
  onEmailChange: (value: string) => void
  onNameChange: (value: string) => void
  onMsgChange: (value: string) => void
  onSend: () => void
}

export function ProposalSendModal({
  open,
  estimateId,
  proposalEmail,
  proposalName,
  proposalMsg,
  proposalSending,
  proposalError,
  shareUrl,
  grandTotal,
  lineItemCount,
  onClose,
  onEmailChange,
  onNameChange,
  onMsgChange,
  onSend,
}: ProposalSendModalProps) {
  const [copied, setCopied] = useState(false)
  const [previewExpanded, setPreviewExpanded] = useState(false)
  const handleCopy = async () => {
    if (!shareUrl) return
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch { /* ignore */ }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={shareUrl ? 'Proposal sent' : 'Send Proposal'}
      description={
        shareUrl
          ? 'Your customer will receive an email. You can also share the link directly.'
          : `Email estimate #${estimateId} as a proposal to your customer.`
      }
      size="sm"
    >
      {shareUrl ? (
        <div className="space-y-3">
          <div className="rounded-xl border border-[color:var(--line)] bg-white/[0.02] p-3">
            <div className="mb-1 text-xs font-medium text-[color:var(--muted-ink)]">Shareable link</div>
            <div className="flex items-center gap-2">
              <input
                readOnly
                value={shareUrl}
                onFocus={(e) => e.currentTarget.select()}
                className="input w-full text-xs"
              />
              <button
                type="button"
                onClick={() => void handleCopy()}
                className="inline-flex items-center gap-1.5 rounded-lg border border-[color:var(--line)] px-3 py-2 text-xs font-medium text-[color:var(--muted-ink)] hover:text-[color:var(--ink)]"
                aria-label="Copy link"
              >
                {copied ? <><Check size={12} /> Copied</> : <><Copy size={12} /> Copy</>}
              </button>
            </div>
          </div>
          <div className="flex justify-end">
            <button
              type="button"
              onClick={onClose}
              className="btn-primary rounded-xl px-4 py-2 text-sm"
            >
              Done
            </button>
          </div>
        </div>
      ) : (
      <form
        onSubmit={e => { e.preventDefault(); onSend() }}
        className="space-y-3"
      >
        {/* Estimate summary preview */}
        {(grandTotal != null || lineItemCount != null) && (
          <div className="rounded-xl border border-[color:var(--line)] overflow-hidden">
            <button
              type="button"
              onClick={() => setPreviewExpanded(v => !v)}
              className="flex w-full items-center justify-between px-3 py-2.5 text-left hover:bg-[color:var(--panel-strong)] transition-colors"
              aria-expanded={previewExpanded}
            >
              <span className="flex items-center gap-2 text-xs font-medium text-[color:var(--muted-ink)]">
                <FileText size={13} />
                Estimate #{estimateId} preview
              </span>
              {previewExpanded ? <ChevronUp size={14} className="text-[color:var(--muted-ink)]" /> : <ChevronDown size={14} className="text-[color:var(--muted-ink)]" />}
            </button>
            {previewExpanded && (
              <div className="border-t border-[color:var(--line)] bg-[color:var(--panel)] px-3 py-2.5 flex items-center gap-4 text-xs">
                {lineItemCount != null && (
                  <span className="text-[color:var(--muted-ink)]">
                    <span className="font-semibold text-[color:var(--ink)]">{lineItemCount}</span> line item{lineItemCount !== 1 ? 's' : ''}
                  </span>
                )}
                {grandTotal != null && (
                  <span className="text-[color:var(--muted-ink)]">
                    Total: <span className="font-semibold text-[color:var(--ink)]">{formatCurrency(grandTotal)}</span>
                  </span>
                )}
                <span className="ml-auto text-[color:var(--muted-ink)] italic">Sent as a PDF proposal</span>
              </div>
            )}
          </div>
        )}

        <div>
          <label htmlFor="proposal-email" className="mb-1 block text-xs font-medium text-[color:var(--muted-ink)]">
            Recipient email *
          </label>
          <input
            id="proposal-email"
            type="email"
            required
            aria-required="true"
            autoComplete="email"
            value={proposalEmail}
            onChange={e => onEmailChange(e.target.value)}
            placeholder="customer@example.com"
            className="input w-full"
          />
        </div>
        <div>
          <label htmlFor="proposal-name" className="mb-1 block text-xs font-medium text-[color:var(--muted-ink)]">
            Recipient name
          </label>
          <input
            id="proposal-name"
            type="text"
            autoComplete="name"
            value={proposalName}
            onChange={e => onNameChange(e.target.value)}
            placeholder="John Smith"
            className="input w-full"
          />
        </div>
        <div>
          <label htmlFor="proposal-message" className="mb-1 block text-xs font-medium text-[color:var(--muted-ink)]">
            Personal message
          </label>
          <textarea
            id="proposal-message"
            value={proposalMsg}
            onChange={e => onMsgChange(e.target.value)}
            placeholder="Thank you for considering us for this project…"
            rows={3}
            className="input w-full resize-none"
          />
        </div>
        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-[color:var(--line)] px-4 py-2 text-sm font-medium text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!proposalEmail.trim() || proposalSending}
            className="btn-primary rounded-xl px-4 py-2 text-sm disabled:opacity-40"
          >
            {proposalSending ? (
              <><RefreshCw size={14} className="animate-spin" aria-hidden="true" /><span>Sending…</span></>
            ) : 'Send'}
          </button>
        </div>
        {proposalError && (
          <div
            role="alert"
            aria-live="polite"
            className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-400"
          >
            {proposalError}
          </div>
        )}
      </form>
      )}
    </Modal>
  )
}
