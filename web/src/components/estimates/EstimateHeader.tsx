'use client'

import {
  ArrowLeft, Zap, Copy, Download, Printer, Mail, Trash2, RefreshCw,
} from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Tooltip } from '@/components/ui/Tooltip'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { cn, formatCurrency } from '@/lib/utils'
import type { OutcomeValue } from '@/lib/api'

export interface EstimateHeaderProps {
  estimate: {
    id: number
    title: string
    job_type: string
    county: string
    grand_total: number
  }
  outcome: OutcomeValue | null
  outcomeSubmitting: boolean
  duplicating: boolean
  confirmDelete: boolean
  deleting: boolean
  jobTypeVariant: Record<string, 'accent' | 'success' | 'warning' | 'danger' | 'info' | 'neutral'>
  onBack: () => void
  onOpenEstimator: () => void
  onDuplicate: () => void
  onExportCSV: () => void
  onPrint: () => void
  onSendProposal: () => void
  onRecordOutcome: (value: OutcomeValue) => void
  onDeleteClick: () => void
  onDeleteConfirm: () => void
  onDeleteCancel: () => void
}

export function EstimateHeader({
  estimate,
  outcome,
  outcomeSubmitting,
  duplicating,
  confirmDelete,
  deleting,
  jobTypeVariant,
  onBack,
  onOpenEstimator,
  onDuplicate,
  onExportCSV,
  onPrint,
  onSendProposal,
  onRecordOutcome,
  onDeleteClick,
  onDeleteConfirm,
  onDeleteCancel,
}: EstimateHeaderProps) {
  return (
    <div className="bg-[hsl(var(--background))]/80 backdrop-blur-xl border-b border-white/[0.06] px-4 py-3 sticky top-0 z-10">
      <div className="max-w-4xl mx-auto flex items-center gap-3">
        <button
          onClick={onBack}
          aria-label="Go back"
          className="p-2 rounded-xl hover:bg-white/[0.07] text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
        >
          <ArrowLeft size={16} />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-sm font-bold text-[color:var(--ink)] truncate">{estimate.title || `Estimate #${estimate.id}`}</h1>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            <Badge variant={jobTypeVariant[estimate.job_type] ?? 'accent'} size="sm">
              {estimate.job_type}
            </Badge>
            <span className="text-[11px] text-[color:var(--muted-ink)]">{estimate.county} County</span>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Tooltip content="Open in Estimator">
            <button
              onClick={onOpenEstimator}
              className="p-2 rounded-xl hover:bg-white/[0.07] text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
              aria-label="Open in Estimator"
            >
              <Zap size={15} />
            </button>
          </Tooltip>

          <Tooltip content="Duplicate estimate">
            <button
              onClick={onDuplicate}
              disabled={duplicating}
              className="p-2 rounded-xl hover:bg-white/[0.07] text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors disabled:opacity-40"
              aria-label="Duplicate estimate"
            >
              {duplicating ? <RefreshCw size={15} className="animate-spin" /> : <Copy size={15} />}
            </button>
          </Tooltip>

          <Tooltip content="Export CSV">
            <button
              onClick={onExportCSV}
              className="p-2 rounded-xl hover:bg-white/[0.07] text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
              aria-label="Export as CSV"
            >
              <Download size={16} />
            </button>
          </Tooltip>

          <Tooltip content="Print / Save as PDF">
            <button
              onClick={onPrint}
              className="p-2 rounded-xl hover:bg-white/[0.07] text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
              aria-label="Print or save as PDF"
            >
              <Printer size={16} />
            </button>
          </Tooltip>

          <Tooltip content="Send proposal email">
            <button
              onClick={onSendProposal}
              className="p-2 rounded-xl hover:bg-white/[0.07] text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
              aria-label="Send proposal"
            >
              <Mail size={15} />
            </button>
          </Tooltip>

          <OutcomeButtons
            outcome={outcome}
            outcomeSubmitting={outcomeSubmitting}
            onRecordOutcome={onRecordOutcome}
          />

          <Tooltip content="Delete estimate">
            <button
              onClick={onDeleteClick}
              className="p-2 rounded-xl hover:bg-[hsl(var(--danger)/0.1)] text-[color:var(--muted-ink)] hover:text-[hsl(var(--danger))] transition-colors"
              aria-label="Delete estimate"
            >
              <Trash2 size={15} />
            </button>
          </Tooltip>

          <div className="text-right ml-1">
            <div className="text-lg font-extrabold text-[color:var(--ink)] tabular-nums">
              {formatCurrency(estimate.grand_total)}
            </div>
            <div className="text-[10px] text-[color:var(--muted-ink)]">grand total</div>
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={confirmDelete}
        onClose={onDeleteCancel}
        onConfirm={onDeleteConfirm}
        title="Delete estimate"
        description={`Are you sure you want to delete "${estimate.title || `Estimate #${estimate.id}`}"? This action cannot be undone.`}
        confirmLabel="Delete"
        cancelLabel="Cancel"
        variant="danger"
        isLoading={deleting}
      />
    </div>
  )
}

function OutcomeButtons({
  outcome,
  outcomeSubmitting,
  onRecordOutcome,
}: {
  outcome: OutcomeValue | null
  outcomeSubmitting: boolean
  onRecordOutcome: (value: OutcomeValue) => void
}) {
  if (outcome) {
    return (
      <span className={cn(
        'px-2 py-1 rounded-lg text-[11px] font-semibold border',
        outcome === 'won'
          ? 'bg-[hsl(var(--success)/0.15)] text-[hsl(var(--success))] border-[hsl(var(--success)/0.3)]'
          : 'bg-[hsl(var(--danger)/0.15)] text-[hsl(var(--danger))] border-[hsl(var(--danger)/0.3)]',
      )}>
        {outcome === 'won' ? 'Won' : 'Lost'}
      </span>
    )
  }

  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => onRecordOutcome('won')}
        disabled={outcomeSubmitting}
        title="Mark as won"
        aria-label="Mark estimate as won"
        className="px-3 py-1.5 rounded-lg text-xs font-semibold border border-[hsl(var(--success)/0.3)] bg-[hsl(var(--success)/0.08)] text-[hsl(var(--success))] hover:bg-[hsl(var(--success)/0.18)] transition-colors disabled:opacity-40"
      >
        Won
      </button>
      <button
        onClick={() => onRecordOutcome('lost')}
        disabled={outcomeSubmitting}
        title="Mark as lost"
        aria-label="Mark estimate as lost"
        className="px-3 py-1.5 rounded-lg text-xs font-semibold border border-[hsl(var(--danger)/0.3)] bg-[hsl(var(--danger)/0.08)] text-[hsl(var(--danger))] hover:bg-[hsl(var(--danger)/0.18)] transition-colors disabled:opacity-40"
      >
        Lost
      </button>
    </div>
  )
}
