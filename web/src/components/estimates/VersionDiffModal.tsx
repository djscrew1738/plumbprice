'use client'

import { useQuery } from '@tanstack/react-query'
import { GitCompare, Plus, Minus, Pencil } from 'lucide-react'
import { estimatesApi } from '@/lib/api'
import { Modal } from '@/components/ui/Modal'
import { Badge } from '@/components/ui/Badge'
import { cn, formatCurrencyDecimal } from '@/lib/utils'

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface DiffLineItem {
  description: string
  change_type: 'added' | 'removed' | 'changed' | 'unchanged'
  before?: { quantity: number; unit_cost: number; total_cost: number } | null
  after?: { quantity: number; unit_cost: number; total_cost: number } | null
}

interface VersionDiffData {
  v1_version_number?: number
  v2_version_number?: number
  summary?: {
    added: number
    removed: number
    changed: number
  }
  line_items?: DiffLineItem[]
}

export interface VersionDiffModalProps {
  open: boolean
  onClose: () => void
  estimateId: number
  v1: string
  v2: string
}

/* ------------------------------------------------------------------ */
/*  Styling helpers                                                    */
/* ------------------------------------------------------------------ */

const changeRowBg: Record<string, string> = {
  added: 'bg-[hsl(var(--success)/0.06)]',
  removed: 'bg-[hsl(var(--danger)/0.06)]',
  changed: 'bg-[hsl(var(--warning)/0.06)]',
  unchanged: '',
}

const changeBadgeVariant: Record<string, 'success' | 'danger' | 'warning' | 'neutral'> = {
  added: 'success',
  removed: 'danger',
  changed: 'warning',
  unchanged: 'neutral',
}

const changeIcon: Record<string, typeof Plus> = {
  added: Plus,
  removed: Minus,
  changed: Pencil,
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function VersionDiffModal({
  open,
  onClose,
  estimateId,
  v1,
  v2,
}: VersionDiffModalProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['estimates', estimateId, 'diff', v1, v2],
    queryFn: () => estimatesApi.diffVersions(estimateId, v1, v2),
    select: (res) => (res.data ?? res) as VersionDiffData,
    enabled: open && !!v1 && !!v2,
  })

  const diff = data
  const items = diff?.line_items ?? []
  const summary = diff?.summary ?? { added: 0, removed: 0, changed: 0 }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Version Comparison"
      size="lg"
    >
      {/* Header summary */}
      <div className="flex items-center gap-3 flex-wrap mb-4">
        <div className="flex items-center gap-1.5 text-sm font-medium text-[color:var(--ink)]">
          <GitCompare size={15} className="text-[color:var(--accent-strong)]" />
          <span>v{diff?.v1_version_number ?? '?'}</span>
          <span className="text-[color:var(--muted-ink)]">→</span>
          <span>v{diff?.v2_version_number ?? '?'}</span>
        </div>

        <div className="flex items-center gap-2 ml-auto">
          {summary.added > 0 && (
            <Badge variant="success" size="sm">+{summary.added} added</Badge>
          )}
          {summary.removed > 0 && (
            <Badge variant="danger" size="sm">−{summary.removed} removed</Badge>
          )}
          {summary.changed > 0 && (
            <Badge variant="warning" size="sm">~{summary.changed} changed</Badge>
          )}
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="space-y-3 py-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton h-10 rounded-lg" />
          ))}
        </div>
      )}

      {/* Error */}
      {isError && (
        <p className="text-sm text-[color:var(--muted-ink)] py-4 text-center">
          Could not load diff. Please try again.
        </p>
      )}

      {/* Diff table */}
      {!isLoading && !isError && items.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-[color:var(--line)]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[color:var(--line)] bg-[color:var(--panel-strong)]">
                <th className="text-left px-3 py-2 text-[11px] font-semibold text-[color:var(--muted-ink)] uppercase tracking-wider">
                  Item
                </th>
                <th className="text-center px-3 py-2 text-[11px] font-semibold text-[color:var(--muted-ink)] uppercase tracking-wider">
                  Change
                </th>
                <th className="text-right px-3 py-2 text-[11px] font-semibold text-[color:var(--muted-ink)] uppercase tracking-wider">
                  Qty (before)
                </th>
                <th className="text-right px-3 py-2 text-[11px] font-semibold text-[color:var(--muted-ink)] uppercase tracking-wider">
                  Qty (after)
                </th>
                <th className="text-right px-3 py-2 text-[11px] font-semibold text-[color:var(--muted-ink)] uppercase tracking-wider">
                  Unit Cost (before)
                </th>
                <th className="text-right px-3 py-2 text-[11px] font-semibold text-[color:var(--muted-ink)] uppercase tracking-wider">
                  Unit Cost (after)
                </th>
                <th className="text-right px-3 py-2 text-[11px] font-semibold text-[color:var(--muted-ink)] uppercase tracking-wider">
                  Total (before)
                </th>
                <th className="text-right px-3 py-2 text-[11px] font-semibold text-[color:var(--muted-ink)] uppercase tracking-wider">
                  Total (after)
                </th>
              </tr>
            </thead>
            <tbody>
              {items
                .filter((item) => item.change_type !== 'unchanged')
                .map((item, idx) => {
                  const Icon = changeIcon[item.change_type]
                  return (
                    <tr
                      key={idx}
                      className={cn(
                        'border-b border-[color:var(--line)] last:border-b-0',
                        changeRowBg[item.change_type],
                      )}
                    >
                      <td className="px-3 py-2 text-[color:var(--ink)] font-medium max-w-[200px] truncate">
                        {item.description}
                      </td>
                      <td className="px-3 py-2 text-center">
                        <Badge variant={changeBadgeVariant[item.change_type]} size="sm">
                          {Icon && <Icon size={10} />}
                          {item.change_type}
                        </Badge>
                      </td>
                      <DiffCell value={item.before?.quantity} type="number" changeType={item.change_type} side="before" />
                      <DiffCell value={item.after?.quantity} type="number" changeType={item.change_type} side="after" />
                      <DiffCell value={item.before?.unit_cost} type="currency" changeType={item.change_type} side="before" />
                      <DiffCell value={item.after?.unit_cost} type="currency" changeType={item.change_type} side="after" />
                      <DiffCell value={item.before?.total_cost} type="currency" changeType={item.change_type} side="before" />
                      <DiffCell value={item.after?.total_cost} type="currency" changeType={item.change_type} side="after" />
                    </tr>
                  )
                })}
            </tbody>
          </table>
        </div>
      )}

      {/* No changes */}
      {!isLoading && !isError && items.filter((i) => i.change_type !== 'unchanged').length === 0 && (
        <p className="text-sm text-[color:var(--muted-ink)] py-6 text-center">
          No differences found between these versions.
        </p>
      )}
    </Modal>
  )
}

/* ------------------------------------------------------------------ */
/*  DiffCell — shows before/after with subtle styling                  */
/* ------------------------------------------------------------------ */

function DiffCell({
  value,
  type,
  changeType,
  side,
}: {
  value: number | undefined | null
  type: 'number' | 'currency'
  changeType: string
  side: 'before' | 'after'
}) {
  if (value == null) {
    return (
      <td className="px-3 py-2 text-right text-[color:var(--muted-ink)]">—</td>
    )
  }

  const formatted = type === 'currency' ? formatCurrencyDecimal(value) : String(value)

  const isHighlight =
    (changeType === 'added' && side === 'after') ||
    (changeType === 'removed' && side === 'before')

  return (
    <td
      className={cn(
        'px-3 py-2 text-right tabular-nums',
        isHighlight ? 'font-semibold text-[color:var(--ink)]' : 'text-[color:var(--muted-ink)]',
      )}
    >
      {formatted}
    </td>
  )
}
