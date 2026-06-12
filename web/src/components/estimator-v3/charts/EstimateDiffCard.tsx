'use client'

import { cn, formatCurrencyDecimal } from '@/lib/utils'
import type { EstimateDiffV3 } from '../ChatMessageListV3'

interface EstimateDiffCardProps {
  diff: EstimateDiffV3
  className?: string
}

export function EstimateDiffCard({ diff, className }: EstimateDiffCardProps) {
  const hasChanges =
    (diff.added_line_items?.length || 0) > 0 ||
    (diff.removed_line_items?.length || 0) > 0 ||
    (diff.modified_line_items?.length || 0) > 0

  if (!hasChanges) return null

  return (
    <div className={cn('rounded-xl border border-[color:var(--line)] bg-[color:var(--panel-strong)] p-3', className)}>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-semibold text-[color:var(--ink)]">Changes</span>
        <span className={cn(
          'text-[10px] font-bold',
          (diff.total_delta || 0) >= 0 ? 'text-amber-600' : 'text-emerald-600'
        )}>
          {(diff.total_delta || 0) >= 0 ? '+' : ''}{formatCurrencyDecimal(diff.total_delta || 0)}
        </span>
      </div>

      <div className="space-y-1.5">
        {diff.added_line_items?.map((item: Record<string, unknown>, i: number) => (
          <div key={`added-${i}`} className="flex items-center justify-between rounded-lg bg-blue-50 px-2.5 py-1.5 dark:bg-blue-900/20">
            <span className="text-[11px] text-blue-700 dark:text-blue-300">+ {String(item.description || 'Item')}</span>
            <span className="text-[11px] font-medium text-blue-700 dark:text-blue-300">{formatCurrencyDecimal(Number(item.total_cost || 0))}</span>
          </div>
        ))}
        {diff.removed_line_items?.map((item: Record<string, unknown>, i: number) => (
          <div key={`removed-${i}`} className="flex items-center justify-between rounded-lg bg-red-50 px-2.5 py-1.5 dark:bg-red-900/20">
            <span className="text-[11px] text-red-700 dark:text-red-300">− {String(item.description || 'Item')}</span>
            <span className="text-[11px] font-medium text-red-700 dark:text-red-300">{formatCurrencyDecimal(Number(item.total_cost || 0))}</span>
          </div>
        ))}
        {diff.modified_line_items?.map((item: Record<string, unknown>, i: number) => (
          <div key={`modified-${i}`} className="flex items-center justify-between rounded-lg bg-violet-50 px-2.5 py-1.5 dark:bg-violet-900/20">
            <span className="text-[11px] text-violet-700 dark:text-violet-300">~ {String(item.description || 'Item')}</span>
            <span className="text-[11px] font-medium text-violet-700 dark:text-violet-300">
              {formatCurrencyDecimal(Number(item.previous_total_cost || 0))} → {formatCurrencyDecimal(Number(item.total_cost || 0))}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
