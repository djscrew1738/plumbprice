'use client'

import { Copy, Download, Printer, Trash2 } from 'lucide-react'
import dynamic from 'next/dynamic'
import { Button } from '@/components/ui/Button'
import { ActionBar, ActionBarGroup, ActionBarDivider } from '@/components/ui/ActionBar'

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
    <ActionBar className="border-t border-[color:var(--line)] px-4 py-3 bg-[color:var(--panel)]">
      <ActionBarGroup>
        <Button
          variant="ghost"
          size="sm"
          onClick={onDuplicate}
          disabled={duplicating}
          isLoading={duplicating}
          aria-label="Duplicate estimate"
        >
          <Copy size={14} />
          Duplicate
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={onExportCSV}
          aria-label="Export as CSV"
        >
          <Download size={14} />
          Export CSV
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={onPrint}
          aria-label="Print or save as PDF"
        >
          <Printer size={14} />
          Print
        </Button>
      </ActionBarGroup>

      <ActionBarDivider />

      <ActionBarGroup align="right">
        <Button
          variant="danger"
          size="sm"
          onClick={onDeleteClick}
          aria-label="Delete estimate"
        >
          <Trash2 size={14} />
          Delete
        </Button>
      </ActionBarGroup>

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
    </ActionBar>
  )
}
