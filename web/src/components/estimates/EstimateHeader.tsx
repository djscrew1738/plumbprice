'use client'

import {
  ArrowLeft, Zap, Copy, Download, Printer, Mail, Trash2, AlertTriangle,
} from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import dynamic from 'next/dynamic'
import { Tooltip } from '@/components/ui/Tooltip'

const ConfirmDialog = dynamic(() => import('@/components/ui/ConfirmDialog').then(m => ({ default: m.ConfirmDialog })), { ssr: false })
import { cn, formatCurrency } from '@/lib/utils'
import type { OutcomeValue } from '@/lib/api'

export interface EstimateHeaderProps {
  estimate: {
    id: number
    title: string
    job_type: string
    county: string
    grand_total: number
    status?: string
    is_expired?: boolean | null
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
    <div className="bg-[color:var(--panel)]/80 backdrop-blur-xl border-b border-[color:var(--line)] px-4 py-3 sticky top-0 z-10">
      <div className="max-w-4xl mx-auto flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={onBack}
          aria-label="Go back"
          className="shrink-0"
        >
          <ArrowLeft size={16} />
        </Button>
        <div className="flex-1 min-w-0">
          <h1 className="text-sm font-bold text-[color:var(--ink)] truncate">{estimate.title || `Estimate #${estimate.id}`}</h1>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            <Badge variant={jobTypeVariant[estimate.job_type] ?? 'accent'} size="sm">
              {estimate.job_type}
            </Badge>
            {estimate.status && (
              <Badge
                variant={estimate.status === 'accepted' ? 'success' : estimate.status === 'rejected' ? 'danger' : estimate.status === 'sent' ? 'info' : 'neutral'}
                size="sm"
              >
                {estimate.status}
              </Badge>
            )}
            <span className="text-[11px] text-[color:var(--muted-ink)]">{estimate.county} County</span>
            {estimate.is_expired && (
              <span className="inline-flex items-center gap-0.5 text-[color:var(--warning)] text-[10px] font-semibold">
                <AlertTriangle size={11} /> Expired
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Tooltip content="Open in Estimator">
            <Button
              variant="ghost"
              size="icon"
              onClick={onOpenEstimator}
              aria-label="Open in Estimator"
              className="shrink-0"
            >
              <Zap size={15} />
            </Button>
          </Tooltip>

          <Tooltip content="Duplicate estimate">
            <Button
              variant="ghost"
              size="icon"
              onClick={onDuplicate}
              disabled={duplicating}
              isLoading={duplicating}
              aria-label="Duplicate estimate"
              className="shrink-0"
            >
              <Copy size={15} />
            </Button>
          </Tooltip>

          <Tooltip content="Export CSV">
            <Button
              variant="ghost"
              size="icon"
              onClick={onExportCSV}
              aria-label="Export as CSV"
              className="shrink-0"
            >
              <Download size={16} />
            </Button>
          </Tooltip>

          <Tooltip content="Print / Save as PDF">
            <Button
              variant="ghost"
              size="icon"
              onClick={onPrint}
              aria-label="Print or save as PDF"
              className="shrink-0"
            >
              <Printer size={16} />
            </Button>
          </Tooltip>

          <Tooltip content="Send proposal email">
            <Button
              variant="ghost"
              size="icon"
              onClick={onSendProposal}
              aria-label="Send proposal"
              className="shrink-0"
            >
              <Mail size={15} />
            </Button>
          </Tooltip>

          <OutcomeButtons
            outcome={outcome}
            outcomeSubmitting={outcomeSubmitting}
            onRecordOutcome={onRecordOutcome}
          />

          <Tooltip content="Delete estimate">
            <Button
              variant="ghost"
              size="icon"
              onClick={onDeleteClick}
              aria-label="Delete estimate"
              className="shrink-0 hover:text-[color:var(--danger)] hover:bg-[color:var(--danger-soft)]"
            >
              <Trash2 size={15} />
            </Button>
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
  const OUTCOMES: { value: OutcomeValue; label: string; variant: 'success' | 'danger' | 'neutral' | 'warning' }[] = [
    { value: 'won', label: 'Won', variant: 'success' },
    { value: 'lost', label: 'Lost', variant: 'danger' },
    { value: 'no_bid', label: 'No Bid', variant: 'neutral' },
    { value: 'pending', label: 'Pending', variant: 'warning' },
  ]
  return (
    <div className="flex items-center gap-1">
      {OUTCOMES.map(({ value, label, variant }) => {
        const isActive = outcome === value
        return (
          <Button
            key={value}
            variant={isActive ? variant : 'ghost'}
            size="xs"
            onClick={() => onRecordOutcome(value)}
            disabled={outcomeSubmitting || isActive}
            isLoading={outcomeSubmitting && isActive}
            aria-label={`Mark estimate as ${label.toLowerCase()}`}
            className={cn(
              !isActive && variant === 'success' && 'text-[color:var(--success)] hover:text-[color:var(--success)] hover:bg-[color:var(--success-soft)]',
              !isActive && variant === 'danger' && 'text-[color:var(--danger)] hover:text-[color:var(--danger)] hover:bg-[color:var(--danger-soft)]',
              !isActive && variant === 'warning' && 'text-[color:var(--warning)] hover:text-[color:var(--warning)] hover:bg-[color:var(--warning-soft)]',
              !isActive && variant === 'neutral' && 'text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] hover:bg-[color:var(--panel-strong)]',
            )}
          >
            {label}
          </Button>
        )
      })}
    </div>
  )
}
