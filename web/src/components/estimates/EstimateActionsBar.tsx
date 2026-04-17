'use client'

import { Copy, Download, Printer, Trash2, RefreshCw } from 'lucide-react'
import dynamic from 'next/dynamic'
import { Tooltip } from '@/components/ui/Tooltip'

const ConfirmDialog = dynamic(() => import('@/components/ui/ConfirmDialog').then(m => ({ default: m.ConfirmDialog })), { ssr: false })

export interface EstimateActionsBarProps {
  estimateTitle: string
  estimateId: number
  duplicating: boolean
  confirmDelete: boolean
  deleting: boolean
  onDuplicate: () => void
  onExportCSV: () => void
  onPrint: () => void
  onDeleteClick: () => void
  onDeleteConfirm: () => void
  onDeleteCancel: () => void
}

export function EstimateActionsBar({
  estimateTitle,
  estimateId,
  duplicating,
  confirmDelete,
  deleting,
  onDuplicate,
  onExportCSV,
  onPrint,
  onDeleteClick,
  onDeleteConfirm,
  onDeleteCancel,
}: EstimateActionsBarProps) {
  return (
    <div className="flex items-center gap-2 border-t border-white/[0.06] px-4 py-3 bg-[color:var(--panel)]">
      <Tooltip content="Duplicate estimate">
        <button
          onClick={onDuplicate}
          disabled={duplicating}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] hover:bg-white/[0.07] transition-colors disabled:opacity-40"
          aria-label="Duplicate estimate"
        >
          {duplicating ? <RefreshCw size={14} className="animate-spin" /> : <Copy size={14} />}
          Duplicate
        </button>
      </Tooltip>

      <Tooltip content="Export as CSV">
        <button
          onClick={onExportCSV}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] hover:bg-white/[0.07] transition-colors"
          aria-label="Export as CSV"
        >
          <Download size={14} />
          Export CSV
        </button>
      </Tooltip>

      <Tooltip content="Print or save as PDF">
        <button
          onClick={onPrint}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] hover:bg-white/[0.07] transition-colors"
          aria-label="Print or save as PDF"
        >
          <Printer size={14} />
          Print
        </button>
      </Tooltip>

      <div className="flex-1" />

      <Tooltip content="Delete estimate">
        <button
          onClick={onDeleteClick}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-[color:var(--muted-ink)] hover:text-[hsl(var(--danger))] hover:bg-[hsl(var(--danger)/0.1)] transition-colors"
          aria-label="Delete estimate"
        >
          <Trash2 size={14} />
          Delete
        </button>
      </Tooltip>

      <ConfirmDialog
        open={confirmDelete}
        onClose={onDeleteCancel}
        onConfirm={onDeleteConfirm}
        title="Delete estimate"
        description={`Are you sure you want to delete "${estimateTitle || `Estimate #${estimateId}`}"? This action cannot be undone.`}
        confirmLabel="Delete"
        cancelLabel="Cancel"
        variant="danger"
        isLoading={deleting}
      />
    </div>
  )
}
